"""
Telegram-бот для тренировки тестов ISSA Inshore Skipper + SRC (русскоязычный).

Режимы:
  • Нативные Telegram-quiz (poll) — мгновенная подсветка верного ответа + пояснение
  • Тренировка по темам
  • Режим экзамена (100 вопросов, проходной балл 90%)
  • Работа над ошибками (повтор только тех вопросов, где ошибались)

Логика «без повторов»: бот помнит, какие вопросы пользователь уже видел,
и не показывает их снова, пока не пройден весь банк (тогда круг сбрасывается).

Стек: Python + aiogram 3.x, хранилище — JSON-файлы (без внешней БД).

Запуск:
  1) pip install -r requirements.txt
  2) Получите токен у @BotFather, положите в файл .env (BOT_TOKEN=...)
     или задайте переменную окружения BOT_TOKEN.
  3) python bot.py
"""

import asyncio
import json
import logging
import os
import random
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    MenuButtonWebApp,
    Message,
    PollAnswer,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

import calc
import content
import glossary
import marine
import nav_tasks
import tides

# ──────────────────────────── Конфигурация ────────────────────────────

BASE_DIR = Path(__file__).parent
QUESTIONS_FILE = BASE_DIR / "questions.json"
PROGRESS_DIR = BASE_DIR / "progress"
PROGRESS_DIR.mkdir(exist_ok=True)
IMAGES_DIR = BASE_DIR / "images"

# Дисклеймер: бот неофициальный, без экзаменационных ключей.
DISCLAIMER = (
    "ℹ️ <i>Бот и база вопросов — оригинальные, созданы для тренировки. "
    "Они <b>не содержат экзаменационных ключей</b> и <b>не являются официальным "
    "материалом ISSA</b> или какой-либо школы. Это вспомогательный учебный "
    "материал для самоподготовки.</i>"
)

EXAM_SIZE = 100           # вопросов в экзамене
EXAM_PASS_PERCENT = 90    # проходной балл, %
# Боевой адрес Mini App (раздаётся Caddy на VPS). Используется как дефолт для
# URL-ов ниже, чтобы лаунчер-меню работало без правки systemd/.env. Переопределяется
# переменными окружения, если нужен другой хост.
DEFAULT_WEBAPP_BASE = "https://issa-46-224-220-94.sslip.io"
# URL мини-приложения (Mini App) калькулятора TVMDC. По умолчанию — боевой адрес,
# в меню калькулятора есть кнопка «Открыть приложение».
WEBAPP_URL = os.environ.get("WEBAPP_URL", DEFAULT_WEBAPP_BASE + "/calc.html").strip()
# URL Mini App «Тесты» (quiz.html). По умолчанию — боевой адрес: на reply-
# клавиатуре есть кнопка запуска приложения тестов. Результат теста
# возвращается в бота через WebApp.sendData и пишется в прогресс.
WEBAPP_QUIZ_URL = os.environ.get("WEBAPP_QUIZ_URL", DEFAULT_WEBAPP_BASE + "/quiz.html").strip()
# URL стартового экрана Mini App (home.html на корне). По умолчанию — боевой
# адрес: меню работает как лаунчер (большая кнопка «Открыть приложение» +
# быстрый доступ), контентные пункты живут внутри приложения. Переопределяется
# переменной WEBAPP_HOME_URL.
WEBAPP_HOME_URL = os.environ.get("WEBAPP_HOME_URL", DEFAULT_WEBAPP_BASE + "/").strip()
TG_MSG_LIMIT = 4096       # ограничение Telegram на длину сообщения
POLL_OPTION_LIMIT = 100   # ограничение Telegram на длину варианта ответа
POLL_QUESTION_LIMIT = 300 # ограничение Telegram на длину текста вопроса/пояснения

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("issa-bot")


def load_token() -> str:
    """Берём токен из переменной окружения или из файла .env рядом с ботом."""
    token = os.environ.get("BOT_TOKEN")
    if token:
        return token.strip()
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("BOT_TOKEN") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(
        "Не задан BOT_TOKEN. Создайте файл .env со строкой BOT_TOKEN=... "
        "или задайте переменную окружения."
    )


# ──────────────────────────── Банк вопросов ────────────────────────────

with open(QUESTIONS_FILE, encoding="utf-8") as f:
    QUESTIONS: list[dict] = json.load(f)

QUESTIONS_BY_ID: dict[str, dict] = {q["id"]: q for q in QUESTIONS}
TOPICS: list[str] = sorted({q["topic"] for q in QUESTIONS})


def topic_questions(topic: str) -> list[dict]:
    return [q for q in QUESTIONS if q["topic"] == topic]


# ──────────────────────────── Прогресс пользователя ────────────────────────────
#
# Формат файла progress/<user_id>.json:
# {
#   "seen":   ["id1", "id2", ...],          # уже показанные (для логики без повторов)
#   "wrong":  ["id5", ...],                  # вопросы, где пользователь ошибался
#   "stats":  {"answered": N, "correct": N}  # общая статистика
# }

def _progress_path(user_id: int) -> Path:
    return PROGRESS_DIR / f"{user_id}.json"


import contextlib  # noqa: E402

# Атомарность read-modify-write прогресса обеспечивает САМ event-loop: aiogram
# работает в одном потоке, а каждая мутация (load → modify → save ниже) полностью
# синхронна — внутри неё нет ни одного await, поэтому loop не переключается на
# другую корутину до завершения save_progress. Значит гонок между апдейтами
# одного юзера нет и отдельный замок не нужен (раньше тут был threading.RLock,
# который в однопоточном asyncio всё равно был no-op).
#
# Известный компромисс: файловый I/O синхронный и на время записи блокирует loop.
# Для учебной нагрузки приемлемо; переход на БД/aiofiles — в техдолге (см. README).
# _locked() оставлен как заглушка-контекст на случай, если мутации станут async.
def _lock_for(user_id: int):  # noqa: ARG001 - сигнатура сохранена для совместимости
    return contextlib.nullcontext()


def load_progress(user_id: int) -> dict:
    path = _progress_path(user_id)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Битый/недописанный файл: не теряем молча — сохраняем копию для
            # ручного разбора, затем стартуем с чистого прогресса.
            with contextlib.suppress(OSError):
                path.replace(path.with_suffix(".corrupt.json"))
            data = {}
    else:
        data = {}
    data.setdefault("seen", [])
    data.setdefault("wrong", [])
    data.setdefault("stats", {"answered": 0, "correct": 0})
    data.setdefault("tasks", {"solved": 0, "attempts": 0, "streak": 0, "best": 0})
    return data


def save_progress(user_id: int, data: dict) -> None:
    # Атомарная запись: пишем во временный файл и переименовываем. Так файл
    # прогресса никогда не остаётся «наполовину записанным» при сбое/нагрузке.
    path = _progress_path(user_id)
    # Уникальный временный файл (pid + случайный хвост) на случай параллельных
    # процессов; в одном процессе loop однопоточный, так что коллизий нет.
    tmp = path.with_suffix(f".{os.getpid()}.{random.randrange(1 << 32):08x}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def pick_unseen(user_id: int, pool: list[dict], count: int = 1) -> list[dict]:
    """
    Выбирает вопросы, которых пользователь ещё не видел (без повторов).
    Когда непросмотренных в пуле не остаётся — круг сбрасывается.
    """
    with _lock_for(user_id):
        prog = load_progress(user_id)
        seen = set(prog["seen"])
        unseen = [q for q in pool if q["id"] not in seen]

        if not unseen:
            # Прошли весь пул — сбрасываем «увиденное» только для этого пула.
            pool_ids = {q["id"] for q in pool}
            prog["seen"] = [sid for sid in prog["seen"] if sid not in pool_ids]
            save_progress(user_id, prog)
            unseen = list(pool)

    random.shuffle(unseen)
    return unseen[:count]


def mark_seen(user_id: int, qid: str) -> None:
    # Принимаем только реальные id из банка: иначе подделанный payload из WebApp
    # мог бы бесконечно раздувать прогресс-файл (защита от флуда мусором).
    if qid not in QUESTIONS_BY_ID:
        return
    with _lock_for(user_id):
        prog = load_progress(user_id)
        if qid not in prog["seen"]:
            prog["seen"].append(qid)
        save_progress(user_id, prog)


def record_answer(user_id: int, qid: str, correct: bool) -> None:
    if qid not in QUESTIONS_BY_ID:  # игнорируем несуществующие id (см. mark_seen)
        return
    with _lock_for(user_id):
        prog = load_progress(user_id)
        _apply_answer(prog, qid, correct)
        save_progress(user_id, prog)


def _apply_answer(prog: dict, qid: str, correct: bool) -> None:
    """Применить один ответ к загруженному прогрессу (в памяти, без I/O).

    Та же логика, что в record_answer: ведёт статистику и список «работы над
    ошибками». Вынесено, чтобы пакетная запись (record_results_batch) не плодила
    чтение/запись файла на каждый вопрос.
    """
    prog["stats"]["answered"] += 1
    if correct:
        prog["stats"]["correct"] += 1
        if qid in prog["wrong"]:
            prog["wrong"].remove(qid)  # исправился — убираем из работы над ошибками
    else:
        if qid not in prog["wrong"]:
            prog["wrong"].append(qid)


def record_results_batch(
    user_id: int, ok_ids: list[str], wrong_ids: list[str]
) -> None:
    """Записать целый набор ответов теста за ОДНО чтение и ОДНУ запись файла.

    Поведение идентично последовательным record_answer()+mark_seen() по каждому
    вопросу, но без I/O-флуда: при экзамене на 100 вопросов раньше было ~400
    обращений к диску под локом, теперь — одно load + одно save.
    Несуществующие id отбрасываются (как в record_answer/mark_seen).
    """
    seen_set = {*ok_ids, *wrong_ids} & QUESTIONS_BY_ID.keys()
    with _lock_for(user_id):
        prog = load_progress(user_id)
        for qid in ok_ids:
            if qid in QUESTIONS_BY_ID:
                _apply_answer(prog, qid, True)
        for qid in wrong_ids:
            if qid in QUESTIONS_BY_ID:
                _apply_answer(prog, qid, False)
        # «увиденные» — добавляем недостающие (как mark_seen, но разом)
        already = set(prog["seen"])
        for qid in seen_set:
            if qid not in already:
                prog["seen"].append(qid)
                already.add(qid)
        save_progress(user_id, prog)


def remaining_in_pool(user_id: int, pool: list[dict]) -> int:
    seen = set(load_progress(user_id)["seen"])
    return sum(1 for q in pool if q["id"] not in seen)


def _record_streak(user_id: int, correct: bool, key: str) -> dict:
    """Общий учёт задач со streak: попытки, решено, серия и рекорд под ключом key."""
    with _lock_for(user_id):
        prog = load_progress(user_id)
        t = prog.setdefault(key, {"solved": 0, "attempts": 0, "streak": 0, "best": 0})
        t["attempts"] += 1
        if correct:
            t["solved"] += 1
            t["streak"] += 1
            t["best"] = max(t["best"], t["streak"])
        else:
            t["streak"] = 0
        save_progress(user_id, prog)
        return dict(t)


def record_task(user_id: int, correct: bool) -> dict:
    """Учёт задач T-V-M-D-C."""
    return _record_streak(user_id, correct, "tasks")


def record_ptask(user_id: int, correct: bool) -> dict:
    """Учёт практических задач (скорость/время/дистанция/ETA)."""
    return _record_streak(user_id, correct, "ptasks")


# ──────────────────────────── Состояние сессий ────────────────────────────
#
# Связываем poll_id Telegram с вопросом, чтобы знать, на что ответил пользователь.
# poll_id -> {"user_id", "qid", "mode", "exam"?}
ACTIVE_POLLS: dict[str, dict] = {}

# Состояние идущего экзамена: user_id -> {"queue": [qid,...], "idx", "correct", "results": [...]}
EXAMS: dict[int, dict] = {}

# Текущая задача T-V-M-D-C, на которую пользователь вводит ответ: user_id -> task_id
ACTIVE_TASK: dict[int, str] = {}

# Текущая практическая задача (скорость/время/ETA): user_id -> task_id
ACTIVE_PTASK: dict[int, str] = {}

# Пользователи в режиме поиска по словарю (ждём ввод запроса): set(user_id)
GLOSSARY_SEARCH: set[int] = set()

# Калькулятор TVMDC: user_id -> {"src","dst"} — ждём ввод значений строкой.
CALC_STATE: dict[int, dict] = {}


# ──────────────────────────── Клавиатуры ────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    # Если развёрнут Mini App — ведём кнопкой «Открыть приложение», а контентные
    # разделы (есть в приложении) в чат-меню не дублируем. В чате остаётся то,
    # что завязано на прогресс/quiz-поллы. Без URL — полное меню (как было).
    if WEBAPP_HOME_URL:
        # Лаунчер-режим: приложение — основной интерфейс, в чате только
        # большая кнопка запуска + быстрый доступ к самому ходовому (без
        # дублирования всего: конспект/шпаргалки/словарь/калькулятор — внутри Mini App).
        rows = [
            [InlineKeyboardButton(text="🚀 Открыть приложение",
                                  web_app=WebAppInfo(url=WEBAPP_HOME_URL))],
            [InlineKeyboardButton(text="Случайный вопрос", callback_data="mode:random")],
            [InlineKeyboardButton(text=f"Экзамен ({EXAM_SIZE} вопросов)", callback_data="mode:exam")],
            [InlineKeyboardButton(text="Работа над ошибками", callback_data="mode:mistakes")],
            [InlineKeyboardButton(text="Моя статистика", callback_data="mode:stats")],
            [InlineKeyboardButton(text="Сбросить прогресс", callback_data="mode:reset")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=rows)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Случайный вопрос", callback_data="mode:random")],
            [InlineKeyboardButton(text="📚 Тренировка по темам", callback_data="mode:topics")],
            [InlineKeyboardButton(text=f"📝 Экзамен ({EXAM_SIZE} вопросов)", callback_data="mode:exam")],
            [InlineKeyboardButton(text="🔁 Работа над ошибками", callback_data="mode:mistakes")],
            [InlineKeyboardButton(text="🧭 Решение задач (T-V-M-D-C)", callback_data="mode:tasks")],
            [InlineKeyboardButton(text="🧮 Морской калькулятор", callback_data="mode:calc")],
            [InlineKeyboardButton(text="📝 Практические задачи", callback_data="mode:ptasks")],
            [InlineKeyboardButton(text="📖 Конспект", callback_data="mode:konspekt")],
            [InlineKeyboardButton(text="📌 Шпаргалки", callback_data="mode:cheat")],
            [InlineKeyboardButton(text="📚 Словарь яхтсмена", callback_data="mode:glossary")],
            [InlineKeyboardButton(text="📊 Моя статистика", callback_data="mode:stats")],
            [InlineKeyboardButton(text="♻️ Сбросить прогресс", callback_data="mode:reset")],
        ]
    )


def quiz_app_reply_kb() -> ReplyKeyboardMarkup | None:
    """
    Постоянная reply-клавиатура с кнопкой запуска Mini App «Тесты».
    Только reply-кнопка WebApp умеет возвращать данные через sendData,
    поэтому приложение тестов запускаем именно отсюда. Если URL не задан —
    клавиатуры нет (None), приложение недоступно, чат-режимы работают как есть.
    """
    if not WEBAPP_QUIZ_URL:
        return None
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎓 Тесты (приложение)",
                                  web_app=WebAppInfo(url=WEBAPP_QUIZ_URL))]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Меню — /menu",
    )


def topics_kb() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, topic in enumerate(TOPICS, 1):
        n = len(topic_questions(topic))
        row.append(InlineKeyboardButton(text=f"{topic} ({n})", callback_data=f"topic:{topic}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="mode:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def next_question_kb(callback: str, label: str = "➡️ Следующий вопрос",
                     study_qid: str | None = None) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=label, callback_data=callback)]]
    if study_qid:
        rows.append([InlineKeyboardButton(text="📖 Подробнее", callback_data=f"study:{study_qid}")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="mode:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ──────────────────────────── Отправка вопроса как quiz ────────────────────────────

def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


async def send_quiz(
    bot: Bot,
    chat_id: int,
    user_id: int,
    question: dict,
    mode: str,
    is_exam: bool = False,
) -> None:
    """Отправляет вопрос как нативный Telegram quiz-poll."""
    options = [_truncate(opt, POLL_OPTION_LIMIT) for opt in question["options"]]
    explanation = _truncate(question.get("expl", ""), POLL_QUESTION_LIMIT)
    q_text = _truncate(f"[{question['topic']}] {question['q']}", POLL_QUESTION_LIMIT)

    msg = await bot.send_poll(
        chat_id=chat_id,
        question=q_text,
        options=options,
        type="quiz",
        correct_option_id=question["answer"],
        explanation=explanation or None,
        is_anonymous=False,
    )
    poll_id = msg.poll.id
    ACTIVE_POLLS[poll_id] = {
        "user_id": user_id,
        "qid": question["id"],
        "mode": mode,
        "exam": is_exam,
    }
    mark_seen(user_id, question["id"])


# ──────────────────────────── Хэндлеры команд ────────────────────────────

dp = Dispatcher()

# Бот рассчитан на ЛИЧНЫЕ чаты: прогресс, экзамен и quiz привязаны к одному
# пользователю. В группах модель ответов на poll работает иначе, поэтому
# в группах вежливо отправляем в личку и дальше не обрабатываем.

@dp.message(~F.chat.type.in_({"private"}))
async def group_redirect(message: Message) -> None:
    try:
        me = await message.bot.get_me()
        await message.reply(
            "👋 Я тренажёр для самоподготовки. Открой меня в личном чате: "
            f"@{me.username} → /start"
        )
    except Exception:  # noqa: BLE001
        pass


@dp.callback_query(~F.message.chat.type.in_({"private"}))
async def group_cb_redirect(cb: CallbackQuery) -> None:
    await cb.answer("Открой бота в личном чате 🙂", show_alert=True)


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    # Если развёрнут Mini App — делаем его ГЛАВНЫМ входом: крупная кнопка-приложение
    # первым сообщением. Весь тренажёр (тесты с разбором, конспект, калькуляторы,
    # повторение, прогресс) удобнее в приложении; чат-режимы — как быстрый доступ.
    if WEBAPP_HOME_URL:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🚀 Открыть тренажёр",
                                 web_app=WebAppInfo(url=WEBAPP_HOME_URL))
        ]])
        await message.answer(
            "⚓ <b>ISSA Trainer</b> — подготовка к экзамену Inshore Skipper + SRC\n\n"
            f"<b>{len(QUESTIONS)} вопросов</b> с разбором и источниками, конспект по "
            "учебнику, морские калькуляторы, интервальное повторение, пробный экзамен "
            "и отслеживание готовности.\n\n"
            "👉 <b>Всё это — в приложении.</b> Нажми «Открыть тренажёр»:",
            reply_markup=kb,
        )
        await message.answer(
            "Или быстрые режимы прямо в чате:",
            reply_markup=main_menu_kb(),
        )
        return

    # Fallback без Mini App — как было: всё в чате.
    await message.answer(
        "⚓ <b>Тренажёр ISSA Inshore Skipper + SRC</b>\n\n"
        f"В банке <b>{len(QUESTIONS)}</b> вопросов по темам: "
        "терминология, паруса, манёвры, якорение, навигация, "
        "IALA, COLREG (МППСС), огни/знаки, звуковые сигналы, метео, "
        "безопасность, VHF/SRC, планирование, практика.\n\n"
        "Вопросы <b>не повторяются</b>, пока не пройдёшь весь круг.\n\n"
        + DISCLAIMER +
        "\n\nВыбери режим:",
        reply_markup=main_menu_kb(),
    )
    rk = quiz_app_reply_kb()
    if rk:
        await message.answer(
            "🎓 Доступно приложение «Тесты» — кнопка снизу (тренировка и экзамен "
            "с таймером; результат сохраняется в твой прогресс).",
            reply_markup=rk,
        )


@dp.message(Command("tests"))
async def cmd_tests(message: Message) -> None:
    rk = quiz_app_reply_kb()
    if rk:
        await message.answer(
            "🎓 <b>Приложение «Тесты»</b>\n"
            "Нажми кнопку снизу — откроется тренажёр (тренировка/экзамен). "
            "Результат вернётся в бота и сохранится в прогресс.",
            reply_markup=rk,
        )
    else:
        await message.answer(
            "Приложение «Тесты» пока не подключено. Тренироваться можно прямо "
            "в чате: /menu → «🎯 Случайный вопрос» или «📝 Экзамен».",
            reply_markup=main_menu_kb(),
        )


@dp.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("Главное меню:", reply_markup=main_menu_kb())


@dp.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    await show_stats(message.bot, message.chat.id, message.from_user.id)


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Команды:</b>\n"
        "/start — главное меню\n"
        "/menu — меню режимов\n"
        "/stats — моя статистика\n"
        "/calc — морской калькулятор (TVMDC, скорость/время/ETA)\n"
        "/tests — приложение «Тесты» (если подключено)\n"
        "/about — о боте\n"
        "/privacy — конфиденциальность\n"
        "/help — эта справка\n\n"
        "В режиме quiz нажимай на вариант ответа — бот сразу покажет, "
        "верно ли, и даст пояснение."
    )


@dp.message(Command("about"))
async def cmd_about(message: Message) -> None:
    await message.answer(
        "⚓ <b>Тренажёр ISSA Inshore Skipper + SRC</b>\n\n" + DISCLAIMER
    )


@dp.message(Command("calc"))
async def cmd_calc(message: Message) -> None:
    CALC_STATE.pop(message.from_user.id, None)
    await message.answer(
        "🧮 <b>Калькулятор поправок компаса (TVMDC)</b>\n\n"
        "Цепочка: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
        "Выбери, что во что пересчитать:",
        reply_markup=calc_menu_kb(),
    )


@dp.message(Command("privacy"))
async def cmd_privacy(message: Message) -> None:
    await message.answer(
        "🔒 <b>Конфиденциальность</b>\n\n"
        "Бот хранит только <b>ваш Telegram ID</b> и <b>прогресс обучения</b> "
        "(какие вопросы видели, ошибки, статистика) — чтобы вести вашу "
        "тренировку отдельно.\n\n"
        "❌ Не собираются: имя, телефон, переписка, геолокация, платежи.\n"
        "Бот работает только в личном чате и не читает группы.\n\n"
        "Удалить свои данные — кнопка «♻️ Сбросить прогресс» в меню."
    )


async def show_stats(bot: Bot, chat_id: int, user_id: int) -> None:
    prog = load_progress(user_id)
    answered = prog["stats"]["answered"]
    correct = prog["stats"]["correct"]
    pct = round(correct / answered * 100) if answered else 0
    wrong_n = len(prog["wrong"])
    seen_n = len(set(prog["seen"]) & set(QUESTIONS_BY_ID))
    await bot.send_message(
        chat_id,
        "📊 <b>Твоя статистика</b>\n\n"
        f"Отвечено: <b>{answered}</b>\n"
        f"Правильно: <b>{correct}</b> ({pct}%)\n"
        f"Вопросов на повтор (ошибки): <b>{wrong_n}</b>\n"
        f"Пройдено из банка: <b>{seen_n}/{len(QUESTIONS)}</b>",
        reply_markup=main_menu_kb(),
    )


# ──────────────────────────── Обработка нажатий меню ────────────────────────────

@dp.callback_query(F.data == "mode:menu")
async def cb_menu(cb: CallbackQuery) -> None:
    # Сбрасываем «ожидающие ввод» режимы, чтобы текст не уходил не туда.
    CALC_STATE.pop(cb.from_user.id, None)
    GLOSSARY_SEARCH.discard(cb.from_user.id)
    ACTIVE_TASK.pop(cb.from_user.id, None)
    ACTIVE_PTASK.pop(cb.from_user.id, None)
    await cb.message.answer("Главное меню:", reply_markup=main_menu_kb())
    await cb.answer()


@dp.callback_query(F.data == "mode:random")
async def cb_random(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    chosen = pick_unseen(user_id, QUESTIONS, 1)
    if not chosen:
        await cb.message.answer("Вопросы закончились 🤷", reply_markup=main_menu_kb())
        await cb.answer()
        return
    await send_quiz(cb.bot, cb.message.chat.id, user_id, chosen[0], mode="random")
    left = remaining_in_pool(user_id, QUESTIONS)
    sq = chosen[0]["id"] if chosen[0].get("study") else None
    await cb.message.answer(
        f"Осталось новых вопросов в круге: <b>{left}</b>",
        reply_markup=next_question_kb("mode:random", study_qid=sq),
    )
    await cb.answer()


@dp.callback_query(F.data == "mode:topics")
async def cb_topics(cb: CallbackQuery) -> None:
    await cb.message.answer("Выбери тему:", reply_markup=topics_kb())
    await cb.answer()


@dp.callback_query(F.data.startswith("topic:"))
async def cb_topic_question(cb: CallbackQuery) -> None:
    topic = cb.data.split(":", 1)[1]
    user_id = cb.from_user.id
    pool = topic_questions(topic)
    chosen = pick_unseen(user_id, pool, 1)
    if not chosen:
        await cb.message.answer("В этой теме вопросов нет.", reply_markup=topics_kb())
        await cb.answer()
        return
    await send_quiz(cb.bot, cb.message.chat.id, user_id, chosen[0], mode=f"topic:{topic}")
    left = remaining_in_pool(user_id, pool)
    sq = chosen[0]["id"] if chosen[0].get("study") else None
    await cb.message.answer(
        f"Тема «{topic}». Осталось новых: <b>{left}</b>",
        reply_markup=next_question_kb(f"topic:{topic}", "➡️ Ещё по этой теме", study_qid=sq),
    )
    await cb.answer()


@dp.callback_query(F.data == "mode:mistakes")
async def cb_mistakes(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    prog = load_progress(user_id)
    wrong_ids = [qid for qid in prog["wrong"] if qid in QUESTIONS_BY_ID]
    if not wrong_ids:
        await cb.message.answer(
            "🎉 У тебя нет вопросов на повтор — ошибок не накоплено!",
            reply_markup=main_menu_kb(),
        )
        await cb.answer()
        return
    qid = random.choice(wrong_ids)
    question = QUESTIONS_BY_ID[qid]
    await send_quiz(cb.bot, cb.message.chat.id, user_id, question, mode="mistakes")
    sq = question["id"] if question.get("study") else None
    await cb.message.answer(
        f"Вопросов на повтор осталось: <b>{len(wrong_ids)}</b>",
        reply_markup=next_question_kb("mode:mistakes", "🔁 Следующая ошибка", study_qid=sq),
    )
    await cb.answer()


@dp.callback_query(F.data == "mode:stats")
async def cb_stats(cb: CallbackQuery) -> None:
    await show_stats(cb.bot, cb.message.chat.id, cb.from_user.id)
    await cb.answer()


@dp.callback_query(F.data.startswith("study:"))
async def cb_study(cb: CallbackQuery) -> None:
    """Показать расширенный учебный материал (study_material) к вопросу."""
    qid = cb.data.split(":", 1)[1]
    question = QUESTIONS_BY_ID.get(qid)
    study = (question or {}).get("study")
    if not study:
        await cb.answer("Подробностей нет")
        return
    text = _truncate(f"📖 <b>Подробнее</b>\n\n{study}", 4000)
    await cb.message.answer(text)
    await cb.answer()


@dp.callback_query(F.data == "mode:reset")
async def cb_reset(cb: CallbackQuery) -> None:
    save_progress(cb.from_user.id, {"seen": [], "wrong": [], "stats": {"answered": 0, "correct": 0}})
    await cb.message.answer("♻️ Прогресс сброшен.", reply_markup=main_menu_kb())
    await cb.answer()


# ──────────────────────────── Экзамен ────────────────────────────

@dp.callback_query(F.data == "mode:exam")
async def cb_exam_start(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    size = min(EXAM_SIZE, len(QUESTIONS))
    chosen = pick_unseen(user_id, QUESTIONS, size)
    EXAMS[user_id] = {
        "queue": [q["id"] for q in chosen],
        "idx": 0,
        "correct": 0,
        "results": [],  # список (qid, correct: bool)
    }
    await cb.message.answer(
        f"📝 <b>Экзамен начат</b>\n"
        f"Вопросов: {len(chosen)} · Проходной балл: {EXAM_PASS_PERCENT}%\n"
        "Отвечай на каждый вопрос — в конце будет результат и разбор ошибок.",
    )
    await send_next_exam_question(cb.bot, cb.message.chat.id, user_id)
    await cb.answer()


async def send_next_exam_question(bot: Bot, chat_id: int, user_id: int) -> None:
    exam = EXAMS.get(user_id)
    if not exam:
        return
    if exam["idx"] >= len(exam["queue"]):
        await finish_exam(bot, chat_id, user_id)
        return
    qid = exam["queue"][exam["idx"]]
    question = QUESTIONS_BY_ID[qid]
    # В экзамене показываем прогресс в подписи отдельным сообщением.
    await bot.send_message(chat_id, f"Вопрос {exam['idx'] + 1} из {len(exam['queue'])}")
    await send_quiz(bot, chat_id, user_id, question, mode="exam", is_exam=True)


async def finish_exam(bot: Bot, chat_id: int, user_id: int) -> None:
    exam = EXAMS.pop(user_id, None)
    if not exam:
        return
    total = len(exam["queue"])
    correct = exam["correct"]
    pct = round(correct / total * 100) if total else 0
    passed = pct >= EXAM_PASS_PERCENT
    verdict = "✅ <b>СДАНО</b>" if passed else "❌ <b>НЕ СДАНО</b>"

    header = (
        f"🏁 <b>Экзамен завершён</b>\n"
        f"Результат: <b>{correct}/{total}</b> ({pct}%)\n"
        f"{verdict} (нужно ≥ {EXAM_PASS_PERCENT}%)"
    )
    wrong = [qid for qid, ok in exam["results"] if not ok]
    if not wrong:
        await bot.send_message(chat_id, header + "\n\n🎉 Без ошибок!", reply_markup=main_menu_kb())
        return

    # Разбор ошибок может быть длинным (до 100 вопросов) — режем на части
    # по лимиту Telegram, чтобы сообщение не упало.
    blocks = [header, "\n<b>Разбор ошибок:</b>"]
    for qid in wrong:
        q = QUESTIONS_BY_ID[qid]
        correct_opt = q["options"][q["answer"]]
        blocks.append(f"• [{q['topic']}] {q['q']}\n  ✔️ {correct_opt}")
    blocks.append("\nЭти вопросы добавлены в «Работу над ошибками».")
    blocks.append("\n" + DISCLAIMER)

    chunk = ""
    parts: list[str] = []
    for b in blocks:
        if len(chunk) + len(b) + 1 > TG_MSG_LIMIT - 100:
            parts.append(chunk)
            chunk = b
        else:
            chunk = f"{chunk}\n{b}" if chunk else b
    if chunk:
        parts.append(chunk)

    for i, part in enumerate(parts):
        kb = main_menu_kb() if i == len(parts) - 1 else None
        await bot.send_message(chat_id, part, reply_markup=kb)


# ──────────────────────────── Обработка ответа на quiz ────────────────────────────

@dp.poll_answer()
async def on_poll_answer(poll_answer: PollAnswer) -> None:
    info = ACTIVE_POLLS.pop(poll_answer.poll_id, None)
    if not info:
        # Ответ на «потерянный» опрос: бот перезапускали, либо опрос старый.
        # Молча игнорируем (прогресс при перезапуске не теряется, теряется
        # только привязка незавершённых опросов), но фиксируем в логе.
        log.info("stale poll_answer: poll_id=%s user=%s",
                 poll_answer.poll_id, getattr(poll_answer.user, "id", "?"))
        return
    user_id = info["user_id"]
    question = QUESTIONS_BY_ID.get(info["qid"])
    if not question:
        return
    chosen = poll_answer.option_ids[0] if poll_answer.option_ids else -1
    is_correct = chosen == question["answer"]
    record_answer(user_id, question["id"], is_correct)

    if info.get("exam"):
        exam = EXAMS.get(user_id)
        if exam:
            exam["results"].append((question["id"], is_correct))
            if is_correct:
                exam["correct"] += 1
            exam["idx"] += 1
            # Небольшая пауза, чтобы пользователь увидел подсветку ответа.
            await asyncio.sleep(1.0)
            # chat_id == user_id для приватных чатов
            await send_next_exam_question(poll_answer.bot, user_id, user_id)


# ──────────────────────────── Иллюстрации ────────────────────────────

async def send_images(bot: Bot, chat_id: int, files: list[str]) -> None:
    """Отправить картинки страницы (если файлы есть в bot/images/)."""
    for fname in files:
        path = IMAGES_DIR / fname
        if path.exists():
            try:
                await bot.send_photo(chat_id, FSInputFile(path))
            except Exception as e:  # noqa: BLE001 — картинка не критична
                log.warning("Не удалось отправить %s: %s", fname, e)


# ──────────────────────────── Конспект ────────────────────────────

def konspekt_menu_kb() -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, key in enumerate(content.KONSPEKT_ORDER, 1):
        title = content.KONSPEKT_BTN.get(key, content.KONSPEKT[key][0])
        row.append(InlineKeyboardButton(text=title, callback_data=f"kon:{key}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="mode:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data == "mode:konspekt")
async def cb_konspekt(cb: CallbackQuery) -> None:
    await cb.message.answer(
        "📖 <b>Конспект по теории ISSA Inshore Skipper + SRC</b>\n\n"
        "Выбери тему. Жирным выделены термины и формулы, которые чаще всего "
        "спрашивают на тесте.",
        reply_markup=konspekt_menu_kb(),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("kon:"))
async def cb_konspekt_page(cb: CallbackQuery) -> None:
    key = cb.data.split(":", 1)[1]
    page = content.KONSPEKT.get(key)
    if not page:
        await cb.answer("Тема не найдена")
        return
    await cb.message.answer(page[1])
    await send_images(cb.bot, cb.message.chat.id, content.KONSPEKT_IMAGES.get(key, []))
    await cb.message.answer("⬆️ Тема выше. Выбери следующую:", reply_markup=konspekt_menu_kb())
    await cb.answer()


# ──────────────────────────── Шпаргалки ────────────────────────────

def cheat_menu_kb() -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, key in enumerate(content.CHEATSHEET_ORDER, 1):
        title = content.CHEATSHEET_BTN.get(key, content.CHEATSHEETS[key][0])
        row.append(InlineKeyboardButton(text=title, callback_data=f"chs:{key}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="mode:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data == "mode:cheat")
async def cb_cheat(cb: CallbackQuery) -> None:
    await cb.message.answer(
        "📌 <b>Шпаргалки</b>\n\nКраткие выжимки по ключевым темам — удобно "
        "повторить перед тестом или экзаменом.",
        reply_markup=cheat_menu_kb(),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("chs:"))
async def cb_cheat_page(cb: CallbackQuery) -> None:
    key = cb.data.split(":", 1)[1]
    # Узлы — отдельное подменю с пошаговыми фото.
    if key == "knots":
        page = content.CHEATSHEETS["knots"]
        await cb.message.answer(page[1])
        await cb.message.answer(
            "Выбери узел — покажу пошагово с фото:", reply_markup=knots_menu_kb()
        )
        await cb.answer()
        return
    page = content.CHEATSHEETS.get(key)
    if not page:
        await cb.answer("Шпаргалка не найдена")
        return
    await cb.message.answer(page[1])
    await send_images(cb.bot, cb.message.chat.id, content.CHEATSHEET_IMAGES.get(key, []))
    await cb.message.answer("⬆️ Шпаргалка выше. Ещё:", reply_markup=cheat_menu_kb())
    await cb.answer()


# ── Узлы: подменю с фото по шагам ──

def knots_menu_kb() -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, key in enumerate(content.KNOTS_ORDER, 1):
        title = content.KNOTS[key][0]
        row.append(InlineKeyboardButton(text=title, callback_data=f"knot:{key}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="⬅️ К шпаргалкам", callback_data="mode:cheat")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data.startswith("knot:"))
async def cb_knot(cb: CallbackQuery) -> None:
    key = cb.data.split(":", 1)[1]
    knot = content.KNOTS.get(key)
    if not knot:
        await cb.answer("Узел не найден")
        return
    title, descr, steps = knot
    await cb.message.answer(f"{title}\n\n{descr}")
    await send_images(cb.bot, cb.message.chat.id, steps)
    await cb.message.answer("Готово! Выбери другой узел:", reply_markup=knots_menu_kb())
    await cb.answer()


# ──────────────────────────── Словарь яхтсмена ────────────────────────────

GLOSSARY_PAGE = 8  # терминов на страницу


def glossary_menu_kb() -> InlineKeyboardMarkup:
    rows, row = [], []
    i = 0
    for cat in glossary.CATEGORY_ORDER:
        icon = glossary.CATEGORY_ICONS.get(cat, "📚")
        n = len(glossary.YACHTING_GLOSSARY.get(cat, []))
        if n == 0:
            continue
        label = glossary.CATEGORY_BTN.get(cat, cat)
        key = glossary.CATEGORY_KEY[cat]
        row.append(InlineKeyboardButton(text=f"{icon} {label}", callback_data=f"gl:cat:{key}"))
        i += 1
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🔎 Поиск термина", callback_data="gl:search")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="mode:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def glossary_terms_kb(cat: str, page: int) -> InlineKeyboardMarkup:
    key = glossary.CATEGORY_KEY[cat]
    items = glossary.YACHTING_GLOSSARY.get(cat, [])
    start = page * GLOSSARY_PAGE
    chunk = items[start:start + GLOSSARY_PAGE]
    rows = [[InlineKeyboardButton(text=it["term"], callback_data=f"gl:t:{key}:{start + i}")]
            for i, it in enumerate(chunk)]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"gl:cat:{key}:{page - 1}"))
    if start + GLOSSARY_PAGE < len(items):
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"gl:cat:{key}:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ К категориям", callback_data="mode:glossary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data == "mode:glossary")
async def cb_glossary(cb: CallbackQuery) -> None:
    GLOSSARY_SEARCH.discard(cb.from_user.id)
    await cb.message.answer(
        f"📚 <b>Словарь яхтсмена</b> ({glossary.total_count()} терминов)\n\n"
        "Морские и яхтенные термины простыми словами. Выбери категорию "
        "или нажми «🔎 Поиск термина».\n\n"
        "<i>Вспомогательный материал для подготовки, не официальный учебник.</i>",
        reply_markup=glossary_menu_kb(),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("gl:cat:"))
async def cb_glossary_cat(cb: CallbackQuery) -> None:
    rest = cb.data[len("gl:cat:"):]  # <key>[:page]
    if ":" in rest:
        key, page = rest.split(":", 1)
        page = int(page) if page.isdigit() else 0
    else:
        key, page = rest, 0
    cat = glossary.KEY_CATEGORY.get(key)
    if not cat:
        await cb.answer("Категория не найдена")
        return
    icon = glossary.CATEGORY_ICONS.get(cat, "📚")
    await cb.message.answer(f"{icon} <b>{cat}</b>\nВыбери термин:",
                            reply_markup=glossary_terms_kb(cat, page))
    await cb.answer()


@dp.callback_query(F.data.startswith("gl:t:"))
async def cb_glossary_term(cb: CallbackQuery) -> None:
    rest = cb.data[len("gl:t:"):]  # <key>:<idx>
    key, idx = rest.rsplit(":", 1)
    cat = glossary.KEY_CATEGORY.get(key)
    items = glossary.YACHTING_GLOSSARY.get(cat, []) if cat else []
    try:
        it = items[int(idx)]
    except (ValueError, IndexError):
        await cb.answer("Термин не найден")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К списку", callback_data=f"gl:cat:{key}")],
        [InlineKeyboardButton(text="📚 Категории", callback_data="mode:glossary")],
    ])
    await cb.message.answer(glossary.render(cat, it), reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data == "gl:search")
async def cb_glossary_search(cb: CallbackQuery) -> None:
    GLOSSARY_SEARCH.add(cb.from_user.id)
    await cb.message.answer(
        "🔎 Напиши слово для поиска по словарю (например <code>киль</code>, "
        "<code>mayday</code>, <code>галс</code>).")
    await cb.answer()


# ──────────────────────────── Решение задач T-V-M-D-C ────────────────────────────

# ──────────────────────────── Практические задачи (S-D-T / ETA) ────────────────────────────

def ptask_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Новая задача", callback_data="ptask:new")],
        [InlineKeyboardButton(text="💡 Показать решение", callback_data="ptask:solve")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="ptask:stats")],
        [InlineKeyboardButton(text="🧮 Калькулятор", callback_data="mode:calc")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="mode:menu")],
    ])


async def _send_ptask(bot: Bot, chat_id: int, user_id: int, task: marine.MarineTask) -> None:
    ACTIVE_PTASK[user_id] = task.id
    await bot.send_message(
        chat_id,
        f"📝 <b>Практическая задача</b>\n\n{task.text}\n\n"
        f"✍️ Напиши ответ числом (в {task.unit}). Допуск ±{marine._num(task.tol)}.",
        reply_markup=ptask_kb(),
    )


@dp.callback_query(F.data == "mode:ptasks")
async def cb_ptasks(cb: CallbackQuery) -> None:
    await cb.message.answer(
        "📝 <b>Практические задачи</b>\n\n"
        "Скорость · дистанция · время · ETA. Реши задачу — бот проверит ответ "
        "и покажет решение. Ведётся серия (streak).",
        reply_markup=ptask_kb(),
    )
    await _send_ptask(cb.bot, cb.message.chat.id, cb.from_user.id, random.choice(marine.TASKS))
    await cb.answer()


@dp.callback_query(F.data == "ptask:new")
async def cb_ptask_new(cb: CallbackQuery) -> None:
    await _send_ptask(cb.bot, cb.message.chat.id, cb.from_user.id, random.choice(marine.TASKS))
    await cb.answer()


@dp.callback_query(F.data == "ptask:solve")
async def cb_ptask_solve(cb: CallbackQuery) -> None:
    tid = ACTIVE_PTASK.get(cb.from_user.id)
    task = marine.TASKS_BY_ID.get(tid) if tid else None
    if not task:
        await cb.answer("Сначала возьми задачу")
        return
    await cb.message.answer(
        f"💡 <b>Решение</b>\n\n{task.text}\n\n<pre>{task.solution}</pre>\n"
        f"✅ Ответ: <b>{marine._num(task.answer)} {task.unit}</b>",
        reply_markup=ptask_kb(),
    )
    await cb.answer()


@dp.callback_query(F.data == "ptask:stats")
async def cb_ptask_stats(cb: CallbackQuery) -> None:
    p = load_progress(cb.from_user.id).get("ptasks", {"solved": 0, "attempts": 0, "streak": 0, "best": 0})
    att, solved = p["attempts"], p["solved"]
    acc = round(solved / att * 100) if att else 0
    await cb.message.answer(
        "📊 <b>Статистика практических задач</b>\n\n"
        f"Решено верно: <b>{solved}</b> из {att} ({acc}%)\n"
        f"🔥 Текущая серия: <b>{p['streak']}</b>\n"
        f"🏆 Лучшая серия: <b>{p['best']}</b>\n\n"
        f"Всего задач в банке: {len(marine.TASKS)}.",
        reply_markup=ptask_kb(),
    )
    await cb.answer()


def task_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎲 Новая задача", callback_data="task:new"),
             InlineKeyboardButton(text="⭐ Со звёздочкой", callback_data="task:star")],
            [InlineKeyboardButton(text="💡 Показать решение", callback_data="task:solve")],
            [InlineKeyboardButton(text="📊 Статистика задач", callback_data="task:stats")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="mode:menu")],
        ]
    )


async def _send_task(bot: Bot, chat_id: int, user_id: int, task: nav_tasks.NavTask) -> None:
    ACTIVE_TASK[user_id] = task.id
    star = " ⭐<i>(с подвохом — возможен переход через 360°)</i>" if task.starred else ""
    await bot.send_message(
        chat_id,
        f"🧭 <b>Задача T-V-M-D-C</b>{star}\n\n{task.text}\n\n"
        "✍️ Напиши ответ числом (градусы), например <code>046</code>.",
        reply_markup=task_kb(),
    )


@dp.callback_query(F.data == "mode:tasks")
async def cb_tasks(cb: CallbackQuery) -> None:
    await cb.message.answer(
        "🧭 <b>Решение задач: поправки компаса (T-V-M-D-C)</b>\n\n"
        "Цепочка: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
        "Вниз (T→C): <b>East −, West +</b>. Вверх (C→T): наоборот.\n\n"
        "Задачи можно повторять — цель научиться решать. "
        "Есть задачи <b>со звёздочкой</b> (с подвохом, &gt;360°).",
        reply_markup=task_kb(),
    )
    task = random.choice(nav_tasks.TASKS)
    await _send_task(cb.bot, cb.message.chat.id, cb.from_user.id, task)
    await cb.answer()


@dp.callback_query(F.data == "task:new")
async def cb_task_new(cb: CallbackQuery) -> None:
    await _send_task(cb.bot, cb.message.chat.id, cb.from_user.id, random.choice(nav_tasks.TASKS))
    await cb.answer()


@dp.callback_query(F.data == "task:star")
async def cb_task_star(cb: CallbackQuery) -> None:
    await _send_task(cb.bot, cb.message.chat.id, cb.from_user.id, random.choice(nav_tasks.starred_tasks()))
    await cb.answer()


@dp.callback_query(F.data == "task:solve")
async def cb_task_solve(cb: CallbackQuery) -> None:
    task_id = ACTIVE_TASK.get(cb.from_user.id)
    task = nav_tasks.TASKS_BY_ID.get(task_id) if task_id else None
    if not task:
        await cb.answer("Сначала возьми задачу")
        return
    await cb.message.answer(
        f"💡 <b>Решение</b>\n\n{task.text}\n\n<pre>{task.solution}</pre>\n"
        f"✅ Ответ: <b>{task.answer:.0f}°</b>",
        reply_markup=task_kb(),
    )
    await cb.answer()


@dp.callback_query(F.data == "task:stats")
async def cb_task_stats(cb: CallbackQuery) -> None:
    t = load_progress(cb.from_user.id)["tasks"]
    att, solved = t["attempts"], t["solved"]
    acc = round(solved / att * 100) if att else 0
    await cb.message.answer(
        "📊 <b>Статистика по задачам T-V-M-D-C</b>\n\n"
        f"Решено верно: <b>{solved}</b> из {att} ({acc}%)\n"
        f"🔥 Текущая серия: <b>{t['streak']}</b>\n"
        f"🏆 Лучшая серия: <b>{t['best']}</b>\n\n"
        f"Всего задач в банке: {len(nav_tasks.TASKS)} (⭐ с подвохом: {len(nav_tasks.starred_tasks())}).",
        reply_markup=task_kb(),
    )
    await cb.answer()


# ──────────────────────────── Калькулятор TVMDC ────────────────────────────
# Универсальный пересчёт курсов «любое → любое» (calc.solve). Пользователь
# выбирает направление кнопкой, затем вводит значения одной строкой.

# Направления: (src, dst, подпись на кнопке). Покрываем все практичные пары.
CALC_DIRS = [
    ("T", "C", "True → Compass"),
    ("C", "T", "Compass → True"),
    ("T", "M", "True → Magnetic"),
    ("M", "T", "Magnetic → True"),
    ("M", "C", "Magnetic → Compass"),
    ("C", "M", "Compass → Magnetic"),
]


def calc_menu_kb() -> InlineKeyboardMarkup:
    rows = []
    # Если развёрнут Mini App — первой кнопкой даём удобный визуальный калькулятор.
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton(
            text="📱 Открыть приложение-калькулятор",
            web_app=WebAppInfo(url=WEBAPP_URL))])
    rows += [[InlineKeyboardButton(text=label, callback_data=f"calc:dir:{s}{d}")]
             for s, d, label in CALC_DIRS]
    rows.append([InlineKeyboardButton(text="⬅️ Разделы", callback_data="mode:calc")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def calc_result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другое направление", callback_data="calc:cat:compass")],
        [InlineKeyboardButton(text="🧭 Потренироваться (задачи)", callback_data="mode:tasks")],
        [InlineKeyboardButton(text="⬅️ Разделы", callback_data="mode:calc")],
    ])


def _calc_prompt(src: str, dst: str) -> str:
    """Подсказка по вводу: какие поправки нужны для выбранного направления."""
    # T↔M использует Variation, M↔C — Deviation; для T↔C нужны обе.
    pair = {src, dst}
    if pair == {"T", "M"}:
        fields, example = "<b>курс</b> и <b>Variation</b>", "100 6E"
        hint = "Формат: <code>курс  variation(E/W)</code>"
    elif pair == {"M", "C"}:
        fields, example = "<b>курс</b> и <b>Deviation</b>", "120 4W"
        hint = "Формат: <code>курс  deviation(E/W)</code>"
    else:  # T↔C
        fields, example = "<b>курс</b>, <b>Variation</b> и <b>Deviation</b>", "045 3W 2E"
        hint = "Формат: <code>курс  variation(E/W)  deviation(E/W)</code>"
    return (
        f"Введи {fields} одной строкой.\n"
        f"{hint}\n"
        f"Пример: <code>{example}</code>\n\n"
        "Направление поправки указывай буквой: <b>E</b> (восток) или <b>W</b> (запад). "
        "Можно и русские: <b>В</b>/<b>З</b>."
    )


def calc_categories_kb() -> InlineKeyboardMarkup:
    rows = []
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton(
            text="📱 Открыть приложение-калькулятор",
            web_app=WebAppInfo(url=WEBAPP_URL))])
    rows += [
        [InlineKeyboardButton(text="🧭 Поправки компаса (TVMDC)", callback_data="calc:cat:compass")],
        [InlineKeyboardButton(text="⏱ Скорость · время · ETA", callback_data="calc:cat:marine")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="mode:menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data == "mode:calc")
async def cb_calc(cb: CallbackQuery) -> None:
    CALC_STATE.pop(cb.from_user.id, None)
    await cb.message.answer(
        "🧮 <b>Морской калькулятор</b>\n\nВыбери раздел:",
        reply_markup=calc_categories_kb(),
    )
    await cb.answer()


@dp.callback_query(F.data == "calc:cat:compass")
async def cb_calc_compass(cb: CallbackQuery) -> None:
    CALC_STATE.pop(cb.from_user.id, None)
    await cb.message.answer(
        "🧭 <b>Поправки компаса (TVMDC)</b>\n\n"
        "Цепочка: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
        "Выбери, что во что пересчитать:",
        reply_markup=calc_menu_kb(),
    )
    await cb.answer()


# ── Раздел «Скорость · время · ETA» ──
# kind: t=время, d=дистанция, v=скорость, e=ETA.
MARINE_KINDS = {
    "t": ("⏱ Время в пути", "Скорость (узлы) и дистанцию (NM).", "5.5 13.2"),
    "d": ("📏 Дистанция", "Скорость (узлы) и время (часы).", "6 2.5"),
    "v": ("🚤 Средняя скорость", "Дистанцию (NM) и время (часы).", "15 3"),
    "e": ("🎯 ETA / время прибытия", "Дистанцию (NM), скорость (узлы), запас % "
          "и время старта ЧЧ:ММ.", "18 5 20 09:00"),
    "tide": ("🌊 Прилив (правило 12)", "Малую воду LW, полную HW (м) и часы после "
             "малой воды (0–6).", "2 8 3.5"),
}


def marine_menu_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=MARINE_KINDS[k][0], callback_data=f"calc:m:{k}")]
            for k in ("t", "d", "v", "e", "tide")]
    rows.append([InlineKeyboardButton(text="⬅️ Разделы", callback_data="mode:calc")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def marine_result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Ещё расчёт", callback_data="calc:cat:marine")],
        [InlineKeyboardButton(text="📝 Практические задачи", callback_data="mode:ptasks")],
        [InlineKeyboardButton(text="⬅️ Разделы", callback_data="mode:calc")],
    ])


@dp.callback_query(F.data == "calc:cat:marine")
async def cb_calc_marine(cb: CallbackQuery) -> None:
    CALC_STATE.pop(cb.from_user.id, None)
    await cb.message.answer(
        "⏱ <b>Скорость · время · ETA</b>\n\nЧто посчитать?",
        reply_markup=marine_menu_kb(),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("calc:m:"))
async def cb_calc_marine_kind(cb: CallbackQuery) -> None:
    kind = cb.data[len("calc:m:"):]
    if kind not in MARINE_KINDS:
        await cb.answer("Неизвестный расчёт")
        return
    CALC_STATE[cb.from_user.id] = {"marine": kind}
    title, need, example = MARINE_KINDS[kind]
    await cb.message.answer(
        f"{title}\n\nВведи {need}\nОдной строкой через пробел.\n"
        f"Пример: <code>{example}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="calc:cat:marine")],
        ]),
    )
    await cb.answer()


def _marine_numbers(text: str) -> list[float]:
    import re
    return [float(x.replace(",", ".")) for x in re.findall(r"[-+]?\d+(?:[.,]\d+)?", text)]


def compute_marine(kind: str, text: str) -> str:
    """
    Посчитать выбранный морской расчёт по строке ввода. Бросает ValueError
    с понятным текстом, если данных не хватает или они некорректны.
    """
    nums = _marine_numbers(text)
    if kind == "t":
        if len(nums) < 2:
            raise ValueError("Нужны скорость и дистанция, например «5.5 13.2».")
        v, d = nums[0], nums[1]
        h = marine.time_from(d, v)
        return (f"⏱ <b>Время в пути: {round(h,2)} ч</b> ({marine.hours_to_hm(h)})\n\n"
                f"<pre>t = D / V = {marine._num(d)} / {marine._num(v)} = {round(h,2)} ч</pre>")
    if kind == "d":
        if len(nums) < 2:
            raise ValueError("Нужны скорость и время, например «6 2.5».")
        v, t = nums[0], nums[1]
        d = marine.distance_from(v, t)
        return (f"📏 <b>Дистанция: {round(d,1)} NM</b>\n\n"
                f"<pre>D = V × t = {marine._num(v)} × {marine._num(t)} = {round(d,1)} NM</pre>")
    if kind == "v":
        if len(nums) < 2:
            raise ValueError("Нужны дистанция и время, например «15 3».")
        d, t = nums[0], nums[1]
        v = marine.speed_from(d, t)
        return (f"🚤 <b>Средняя скорость: {round(v,1)} узла</b>\n\n"
                f"<pre>V = D / t = {marine._num(d)} / {marine._num(t)} = {round(v,1)} узла</pre>")
    if kind == "e":
        # дистанция, скорость, [запас%], [старт ЧЧ:ММ]
        import re
        if len(nums) < 2:
            raise ValueError("Нужны минимум дистанция и скорость, например «18 5 20 09:00».")
        d, v = nums[0], nums[1]
        reserve = nums[2] if len(nums) >= 3 else 0.0
        mt = re.search(r"\b(\d{1,2}[:.]\d{2})\b", text)
        start = mt.group(1).replace(".", ":") if mt else None
        r = marine.plan_eta(d, v, reserve, start)
        lines = [f"t = D / V = {marine._num(d)} / {marine._num(v)} = {round(r.travel_h,2)} ч"]
        if reserve:
            lines.append(f"с запасом {marine._num(reserve)}% → {round(r.travel_h_reserve,2)} ч")
        body = "\n".join(lines)
        head = f"🎯 <b>В пути: {round(r.travel_h_reserve,2)} ч</b> ({marine.hours_to_hm(r.travel_h_reserve)})"
        if r.eta:
            head += f"\n🕒 <b>ETA: {r.eta}</b>"
        return f"{head}\n\n<pre>{body}</pre>"
    if kind == "tide":
        # LW, HW, часы после малой воды (по правилу двенадцатых)
        if len(nums) < 3:
            raise ValueError("Нужны LW, HW и часы после малой воды, например «2 8 3.5».")
        lw, hw, hours = nums[0], nums[1], nums[2]
        water = tides.height_after_lw(hw, lw, hours)
        rng = hw - lw
        rows = [f"Диапазон = {tides._num(hw)} − {tides._num(lw)} = {tides._num(rng)} м; "
                f"1/12 = {tides._num(rng/12)} м"]
        acc = lw
        for i, part in enumerate(tides.TWELFTHS, start=1):
            acc += rng * part / 12
            rows.append(f"{i}ч  +{part}/12 → {tides._num(acc)} м")
        return (f"🌊 <b>Высота воды через {tides._num(hours)} ч: "
                f"{tides._num(water)} м</b>\n\n<pre>" + "\n".join(rows) + "</pre>")
    raise ValueError("Неизвестный расчёт")


@dp.callback_query(F.data.startswith("calc:dir:"))
async def cb_calc_dir(cb: CallbackQuery) -> None:
    code = cb.data[len("calc:dir:"):]  # напр. "TC"
    src, dst = code[0], code[1]
    if src not in calc.POINTS or dst not in calc.POINTS or src == dst:
        await cb.answer("Неизвестное направление")
        return
    CALC_STATE[cb.from_user.id] = {"src": src, "dst": dst}
    label = next((l for s, d, l in CALC_DIRS if s == src and d == dst), f"{src}→{dst}")
    await cb.message.answer(
        f"🧮 <b>{label}</b>\n\n{_calc_prompt(src, dst)}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="mode:calc")],
        ]),
    )
    await cb.answer()


# Парсер строки ввода: «045 3W 2E» / «100 6e» / «120,5 4 з».
_NUM = r"[-+]?\d+(?:[.,]\d+)?"


def _parse_calc_input(text: str, need_var: bool, need_dev: bool) -> dict | None:
    """
    Разобрать строку «045 3W 2E» в поля для calc.solve.

    Первое число — курс. Следующие — нужные поправки (Variation и/или
    Deviation) в порядке: сначала Variation, потом Deviation. У каждой
    поправки должна быть буква направления (E/W или В/З).
    Возвращает dict или None, если данных не хватает / формат непонятен.
    """
    import re
    pairs = []  # [(число, 'E'|'W'|'')]
    for m in re.finditer(rf"({_NUM})\s*([EWВЗ]?)", text.strip().upper()):
        d = {"E": "E", "W": "W", "В": "E", "З": "W"}.get(m.group(2), "")
        pairs.append((float(m.group(1).replace(",", ".")), d))
    if not pairs:
        return None

    course = pairs[0][0]
    rest = pairs[1:]
    n_need = (1 if need_var else 0) + (1 if need_dev else 0)
    # Нужно ровно столько поправок, и у каждой — направление.
    if len(rest) < n_need or any(not d for _, d in rest[:n_need]):
        return None

    res = {"course": course, "var": 0, "var_dir": "E", "dev": 0, "dev_dir": "E"}
    i = 0
    if need_var:
        res["var"], res["var_dir"] = abs(rest[i][0]), rest[i][1]; i += 1
    if need_dev:
        res["dev"], res["dev_dir"] = abs(rest[i][0]), rest[i][1]
    return res


def _format_calc_result(res: dict) -> str:
    steps = "\n".join(s["text"] for s in res["steps"])
    return (
        f"✅ <b>{res['from']} → {res['to']} = {res['answer']:03d}°</b>\n\n"
        f"<pre>{steps}</pre>\n"
        f"<i>{calc.rule_hint(res['direction'])}</i>"
    )


# ──────────────────────────── Результат из Mini App «Тесты» ────────────────────────────
# Mini App (quiz.html) отправляет компактный итог через WebApp.sendData —
# приходит как Message.web_app_data. Пишем результаты в прогресс (та же
# логика, что и в чат-режимах) и показываем сводку.

MAX_WEBAPP_RESULTS = 200  # защита от слишком большого payload


def parse_webapp_quiz(payload) -> dict | None:
    """
    Разобрать и провалидировать payload из Mini App «Тесты».
    Возвращает {mode, is_exam, ok_ids:[...], wrong_ids:[...], secs} либо
    None, если формат непригоден. Чистая функция (без записи прогресса) —
    удобно тестировать. Неизвестные id отбрасываются.
    """
    if not isinstance(payload, dict) or payload.get("t") != "quiz":
        return None
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        return None
    results = results[:MAX_WEBAPP_RESULTS]

    ok_ids, wrong_ids = [], []
    for item in results:
        if not (isinstance(item, list) and len(item) == 2):
            continue
        qid, ok = item[0], bool(item[1])
        if qid not in QUESTIONS_BY_ID:
            continue
        (ok_ids if ok else wrong_ids).append(qid)
    if not (ok_ids or wrong_ids):
        return None

    try:
        secs = int(payload.get("secs", 0) or 0)
    except (TypeError, ValueError):
        secs = 0
    mode = str(payload.get("mode", "random"))
    return {
        "mode": mode,
        "is_exam": mode == "exam",
        "ok_ids": ok_ids,
        "wrong_ids": wrong_ids,
        "secs": max(0, secs),
    }


@dp.message(F.web_app_data)
async def on_webapp_data(message: Message) -> None:
    user_id = message.from_user.id
    try:
        payload = json.loads(message.web_app_data.data)
    except (json.JSONDecodeError, TypeError):
        log.info("webapp_data: bad json from user=%s", user_id)
        await message.answer("Не удалось прочитать результат из приложения 🤷")
        return

    parsed = parse_webapp_quiz(payload)
    if not parsed:
        await message.answer("Неизвестный или пустой результат из приложения.")
        return

    is_exam = parsed["is_exam"]
    mode = parsed["mode"]
    # Записываем все ответы теста в прогресс (статистика, работа над ошибками,
    # «увиденные») одним пакетом — одно чтение и одна запись файла, а не ~400
    # обращений к диску под локом, как при поштучном record_answer()/mark_seen().
    record_results_batch(user_id, parsed["ok_ids"], parsed["wrong_ids"])

    counted = len(parsed["ok_ids"]) + len(parsed["wrong_ids"])
    correct = len(parsed["ok_ids"])
    pct = round(correct / counted * 100)
    secs = parsed["secs"]
    tline = f" · ⏱ {secs // 60}м {secs % 60}с" if is_exam and secs else ""

    if is_exam:
        passed = pct >= EXAM_PASS_PERCENT
        verdict = "✅ <b>СДАНО</b>" if passed else "❌ <b>НЕ СДАНО</b>"
        head = (f"🏁 <b>Экзамен (приложение) завершён</b>\n"
                f"Результат: <b>{correct}/{counted}</b> ({pct}%){tline}\n"
                f"{verdict} (нужно ≥ {EXAM_PASS_PERCENT}%)")
    else:
        label = mode.split(":", 1)[1] if mode.startswith("topic:") else "случайные"
        head = (f"🎯 <b>Тренировка (приложение): {label}</b>\n"
                f"Результат: <b>{correct}/{counted}</b> ({pct}%)")

    wrong = [QUESTIONS_BY_ID[qid] for qid in parsed["wrong_ids"]]
    if not wrong:
        await message.answer(head + "\n\n🎉 Без ошибок! Результат сохранён.",
                            reply_markup=main_menu_kb())
        return

    blocks = [head, "\n<b>Разбор ошибок:</b>"]
    for q in wrong:
        blocks.append(f"• [{q['topic']}] {q['q']}\n  ✔️ {q['options'][q['answer']]}")
    blocks.append("\nЭти вопросы добавлены в «Работу над ошибками».")

    chunk, parts = "", []
    for b in blocks:
        if len(chunk) + len(b) + 1 > TG_MSG_LIMIT - 100:
            parts.append(chunk)
            chunk = b
        else:
            chunk = f"{chunk}\n{b}" if chunk else b
    if chunk:
        parts.append(chunk)
    for i, part in enumerate(parts):
        kb = main_menu_kb() if i == len(parts) - 1 else None
        await message.answer(part, reply_markup=kb)


# ──────────────────────────── Текстовый ответ на задачу ────────────────────────────
# Срабатывает на любой НЕ-командный текст; если у пользователя активна задача —
# трактуем как ответ. Иначе мягко подсказываем меню.

@dp.message(F.text & ~F.text.startswith("/"))
async def on_text_answer(message: Message) -> None:
    user_id = message.from_user.id

    # 0) Калькулятор: ждём строку со значениями
    state = CALC_STATE.get(user_id)
    if state and "marine" in state:
        kind = state["marine"]
        try:
            out = compute_marine(kind, message.text)
        except ValueError as e:
            await message.answer(
                f"🤔 {e}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="calc:cat:marine")],
                ]),
            )
            return
        CALC_STATE.pop(user_id, None)
        await message.answer(out, reply_markup=marine_result_kb())
        return
    if state:
        src, dst = state["src"], state["dst"]
        pair = {src, dst}
        need_var = pair == {"T", "M"} or pair == {"T", "C"}
        need_dev = pair == {"M", "C"} or pair == {"T", "C"}
        parsed = _parse_calc_input(message.text, need_var, need_dev)
        if not parsed:
            await message.answer(
                "Не понял ввод 🤔 " + _calc_prompt(src, dst),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="mode:calc")],
                ]),
            )
            return
        try:
            res = calc.solve(src, dst, parsed["course"],
                             parsed["var"], parsed["var_dir"],
                             parsed["dev"], parsed["dev_dir"])
        except ValueError as e:
            await message.answer(f"⚠️ {e}", reply_markup=calc_result_kb())
            CALC_STATE.pop(user_id, None)
            return
        CALC_STATE.pop(user_id, None)
        await message.answer(_format_calc_result(res), reply_markup=calc_result_kb())
        return

    # 1) Режим поиска по словарю
    if user_id in GLOSSARY_SEARCH:
        GLOSSARY_SEARCH.discard(user_id)
        hits = glossary.search(message.text)
        if not hits:
            await message.answer(
                "Ничего не нашёл 🤷 Попробуй другое слово или открой категории.",
                reply_markup=glossary_menu_kb())
            return
        # первый результат — карточкой, остальные — кнопками
        cat0, it0 = hits[0]
        rows = []
        for cat, it in hits[1:10]:
            i = glossary.YACHTING_GLOSSARY[cat].index(it)
            key = glossary.CATEGORY_KEY[cat]
            rows.append([InlineKeyboardButton(text=f"{it['term']} ({cat})",
                                              callback_data=f"gl:t:{key}:{i}")])
        rows.append([InlineKeyboardButton(text="📚 Категории", callback_data="mode:glossary")])
        head = f"🔎 Найдено: {len(hits)}\n\n" if len(hits) > 1 else ""
        await message.answer(head + glossary.render(cat0, it0),
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        return

    # 2) Ответ на практическую задачу (скорость/время/ETA)
    ptid = ACTIVE_PTASK.get(user_id)
    if ptid:
        ptask = marine.TASKS_BY_ID.get(ptid)
        if not ptask:
            ACTIVE_PTASK.pop(user_id, None)
            await message.answer("Задача не найдена. /menu", reply_markup=main_menu_kb())
            return
        if ptask.check(message.text):
            ACTIVE_PTASK.pop(user_id, None)
            p = record_ptask(user_id, True)
            streak_line = f"🔥 Серия: <b>{p['streak']}</b>"
            if p["streak"] == p["best"] and p["streak"] >= 3:
                streak_line += " (рекорд!)"
            await message.answer(
                f"✅ <b>Верно!</b> Ответ {marine._num(ptask.answer)} {ptask.unit}.\n"
                f"{streak_line}\n\n<pre>{ptask.solution}</pre>",
                reply_markup=ptask_kb(),
            )
        else:
            p = record_ptask(user_id, False)
            await message.answer(
                "❌ Не то. Проверь формулу (t=D/V, D=V·t, V=D/t) и единицы.\n"
                "Попробуй ещё раз или нажми «💡 Показать решение».\n"
                f"<i>Серия сброшена. Лучшая: {p['best']}.</i>",
                reply_markup=ptask_kb(),
            )
        return

    # 3) Ответ на задачу T-V-M-D-C
    task_id = ACTIVE_TASK.get(user_id)
    if not task_id:
        await message.answer("Не понял. Откройте меню: /menu", reply_markup=main_menu_kb())
        return
    task = nav_tasks.TASKS_BY_ID.get(task_id)
    if not task:
        ACTIVE_TASK.pop(user_id, None)
        await message.answer("Задача не найдена. /menu", reply_markup=main_menu_kb())
        return
    if task.check(message.text):
        ACTIVE_TASK.pop(user_id, None)
        t = record_task(user_id, True)
        streak_line = f"🔥 Серия: <b>{t['streak']}</b>"
        if t["streak"] == t["best"] and t["streak"] >= 3:
            streak_line += " (рекорд!)"
        await message.answer(
            f"✅ <b>Верно!</b> Ответ {task.answer:.0f}°.\n{streak_line}\n\n"
            f"<pre>{task.solution}</pre>",
            reply_markup=task_kb(),
        )
    else:
        t = record_task(user_id, False)
        await message.answer(
            "❌ Неверно. Проверь правило знаков (вниз: <b>East −, West +</b>) "
            "и переход через 360°.\nПопробуй ещё раз или нажми «💡 Показать решение».\n"
            f"<i>Серия сброшена. Лучшая серия: {t['best']}.</i>",
            reply_markup=task_kb(),
        )


# ──────────────────────────── Глобальный обработчик ошибок ────────────────────────────
# Любая ошибка в одном апдейте логируется, но НЕ роняет polling.

@dp.error()
async def on_error(event) -> bool:
    log.exception("Ошибка при обработке апдейта: %s", getattr(event, "exception", event))
    return True  # ошибка обработана — бот продолжает работать


# ──────────────────────────── Запуск ────────────────────────────

async def main() -> None:
    token = load_token()
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    me = await bot.get_me()
    log.info("Бот запущен: @%s | вопросов в банке: %d | тем: %d", me.username, len(QUESTIONS), len(TOPICS))
    # Кнопка-меню слева от поля ввода → открывает Mini App (главный вход в продукт).
    # Так пользователь сразу видит, что «вкусное» — в приложении, а не в чат-диалоге.
    if WEBAPP_HOME_URL:
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="Открыть тренажёр",
                                             web_app=WebAppInfo(url=WEBAPP_HOME_URL))
            )
            log.info("Menu button → Mini App: %s", WEBAPP_HOME_URL)
        except Exception as e:
            log.warning("Не удалось установить menu button: %s", e)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as e:
        log.info("Остановка: %s", e)
