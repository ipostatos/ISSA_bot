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
import time
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LabeledPrice,
    MenuButtonWebApp,
    Message,
    PollAnswer,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

import calc
import content
import glossary
import marine
import nav_tasks
import tides

from bot_i18n import LANG_LABELS, SUPPORTED, norm_lang, t

# ──────────────────────────── Конфигурация ────────────────────────────

BASE_DIR = Path(__file__).parent
QUESTIONS_FILE = BASE_DIR / "questions.json"
PROGRESS_DIR = BASE_DIR / "progress"
PROGRESS_DIR.mkdir(exist_ok=True)
# Сессии живущих в памяти опросов/экзаменов — чтобы они пережили рестарт бота
# (systemd-перезапуск, деплой). Без этого активный чат-экзамен «сиротеет».
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)
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
# Базовый адрес Mini App (раздаётся Caddy на VPS) — из окружения, не хардкодим
# хост в исходниках. Задаётся в .env как WEBAPP_BASE (см. .env.example). Если не
# задан — кнопки «Открыть приложение» в чате просто не показываются (бот работает
# как обычный диалог); это безопасный дефолт без привязки к конкретному серверу.
DEFAULT_WEBAPP_BASE = os.environ.get("WEBAPP_BASE", "").strip().rstrip("/")
def _webapp_url(env_name: str, path: str) -> str:
    """URL страницы Mini App: явный env override, иначе из WEBAPP_BASE + path.
    Если базовый адрес не задан — пустая строка (кнопки приложения не покажутся)."""
    explicit = os.environ.get(env_name, "").strip()
    if explicit:
        return explicit
    return (DEFAULT_WEBAPP_BASE + path) if DEFAULT_WEBAPP_BASE else ""


# URL мини-приложения (Mini App) калькулятора TVMDC — кнопка «Открыть приложение».
WEBAPP_URL = _webapp_url("WEBAPP_URL", "/calc.html")
# URL Mini App «Тесты» (quiz.html) — кнопка запуска тестов на reply-клавиатуре.
WEBAPP_QUIZ_URL = _webapp_url("WEBAPP_QUIZ_URL", "/quiz.html")
# URL стартового экрана (home.html) — лаунчер-меню (кнопка «Открыть приложение»).
WEBAPP_HOME_URL = _webapp_url("WEBAPP_HOME_URL", "/")
# URL экрана польских лицензий (exam_pl.html) — экзамены Żeglarz/Sternik (PL/RU).
WEBAPP_LICENSES_URL = _webapp_url("WEBAPP_LICENSES_URL", "/exam_pl.html")
TG_MSG_LIMIT = 4096         # ограничение Telegram на длину сообщения
POLL_OPTION_LIMIT = 100     # ограничение Telegram на длину варианта ответа
POLL_QUESTION_LIMIT = 300   # лимит Telegram на текст вопроса опроса (300)
POLL_EXPL_LIMIT = 200       # лимит Telegram на explanation опроса (200!) — иначе send_poll 400

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
# Известный компромисс (оценён): файловый I/O синхронный и на время записи
# блокирует event loop. Замер на типичном прогрессе (~8 КБ): load ~0.3 мс,
# save (write+os.replace) ~2.5 мс. Результат теста пишется ОДНИМ батчем
# (record_results_batch) → ~2.8 мс на весь экзамен — для long-polling на малой/
# средней аудитории незаметно. Переход на async-storage (aiofiles/aiosqlite)
# отложен осознанно: он требует вернуть реальные per-user блокировки (сейчас
# nullcontext, т.к. loop однопоточный) и несёт риск в hot-path при копеечном
# выигрыше. _lock_for() оставлен точкой расширения на этот случай.
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


# ── Язык интерфейса пользователя ──
# Хранится в progress/<user_id>.json в поле "lang" (одно из bot_i18n.SUPPORTED).
# Контент вопросов/конспекта/словаря остаётся русским; переводится только «хром».

def user_lang(user_id: int) -> str:
    """Выбранный язык интерфейса пользователя; по умолчанию 'ru'."""
    lang = load_progress(user_id).get("lang")
    return lang if lang in SUPPORTED else "ru"


def set_user_lang(user_id: int, lang: str) -> None:
    """Сохранить язык интерфейса в прогресс пользователя."""
    with _lock_for(user_id):
        data = load_progress(user_id)
        data["lang"] = lang
        save_progress(user_id, data)


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

# ── персистентность сессий (переживают рестарт бота) ──
# Храним EXAMS и ACTIVE_POLLS в JSON, чтобы активный чат-экзамен не «сиротел»
# при перезапуске (systemd/деплой). Запись атомарная (tmp + os.replace), как у
# save_progress. Атомарность read-modify-write гарантирует однопоточный
# event-loop: между мутацией dict и записью нет await. Каждая запись мелкая
# (экзамен ≤100 qid; активные опросы транзиентны) — для long-polling незаметно.
_EXAMS_FILE = SESSIONS_DIR / "exams.json"
_POLLS_FILE = SESSIONS_DIR / "active_polls.json"
# Записи старше этого возраста при загрузке отбрасываем как заведомо мёртвые
# (ответ на опрос через сутки — это уже не «продолжение», а мусор).
_SESSION_TTL_SEC = 24 * 3600


def _atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(f".{os.getpid()}.{random.randrange(1 << 32):08x}.tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:  # диск/права — не роняем бот из-за сохранения сессии
        log.warning("Не удалось сохранить сессии в %s: %s", path.name, e)
        with contextlib.suppress(OSError):
            tmp.unlink()


def _save_exams() -> None:
    # user_id-ключи int → JSON-строки; при загрузке приводим обратно к int.
    _atomic_write_json(_EXAMS_FILE, {str(uid): ex for uid, ex in EXAMS.items()})


def _save_polls() -> None:
    _atomic_write_json(_POLLS_FILE, ACTIVE_POLLS)


def _load_sessions() -> None:
    """Восстановить EXAMS и ACTIVE_POLLS при старте, отбросив протухшее.

    Также сбрасываем «сирот»: опрос без своего экзамена (для exam-опросов) и
    экзамен без единого связанного опроса не имеют смысла после рестарта.
    """
    now = int(time.time())
    exams: dict[int, dict] = {}
    polls: dict[str, dict] = {}
    with contextlib.suppress(OSError, json.JSONDecodeError):
        if _EXAMS_FILE.exists():
            raw = json.loads(_EXAMS_FILE.read_text(encoding="utf-8"))
            for uid, ex in raw.items():
                if now - int(ex.get("ts", now)) <= _SESSION_TTL_SEC:
                    exams[int(uid)] = ex
    with contextlib.suppress(OSError, json.JSONDecodeError):
        if _POLLS_FILE.exists():
            raw = json.loads(_POLLS_FILE.read_text(encoding="utf-8"))
            for pid, info in raw.items():
                if now - int(info.get("ts", now)) <= _SESSION_TTL_SEC:
                    polls[pid] = info
    EXAMS.clear(); EXAMS.update(exams)
    ACTIVE_POLLS.clear(); ACTIVE_POLLS.update(polls)
    if exams or polls:
        log.info("Восстановлено сессий: экзаменов=%d, активных опросов=%d",
                 len(exams), len(polls))
        _save_exams(); _save_polls()   # перезаписываем уже без протухших


# Текущая задача T-V-M-D-C, на которую пользователь вводит ответ: user_id -> task_id
ACTIVE_TASK: dict[int, str] = {}

# Текущая практическая задача (скорость/время/ETA): user_id -> task_id
ACTIVE_PTASK: dict[int, str] = {}

# Пользователи в режиме поиска по словарю (ждём ввод запроса): set(user_id)
GLOSSARY_SEARCH: set[int] = set()

# Калькулятор TVMDC: user_id -> {"src","dst"} — ждём ввод значений строкой.
CALC_STATE: dict[int, dict] = {}


# ──────────────────────────── Клавиатуры ────────────────────────────

def main_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    # Лаунчер-режим (Mini App подключён): приложение — ЕДИНСТВЕННЫЙ интерфейс.
    # Никаких чат-режимов/чат-тестов в меню — только запуск приложения. Весь
    # функционал (тесты с разбором, конспект, калькуляторы, повторение, прогресс,
    # статистика) живёт внутри Mini App.
    if WEBAPP_HOME_URL:
        rows = [
            [InlineKeyboardButton(text=t("mm_open_trainer", lang),
                                  web_app=WebAppInfo(url=WEBAPP_HOME_URL))],
        ]
        if WEBAPP_LICENSES_URL:
            rows.append([InlineKeyboardButton(text=t("mm_pl_licenses", lang),
                                              web_app=WebAppInfo(url=WEBAPP_LICENSES_URL))])
        return InlineKeyboardMarkup(inline_keyboard=rows)
    # Fallback без Mini App (URL не задан) — полное чат-меню, как было.
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("mm_random", lang), callback_data="mode:random")],
            [InlineKeyboardButton(text=t("mm_topics", lang), callback_data="mode:topics")],
            [InlineKeyboardButton(text=t("mm_exam", lang, n=EXAM_SIZE), callback_data="mode:exam")],
            [InlineKeyboardButton(text=t("mm_mistakes", lang), callback_data="mode:mistakes")],
            [InlineKeyboardButton(text=t("mm_tasks", lang), callback_data="mode:tasks")],
            [InlineKeyboardButton(text=t("mm_calc", lang), callback_data="mode:calc")],
            [InlineKeyboardButton(text=t("mm_ptasks", lang), callback_data="mode:ptasks")],
            [InlineKeyboardButton(text=t("mm_konspekt", lang), callback_data="mode:konspekt")],
            [InlineKeyboardButton(text=t("mm_cheat", lang), callback_data="mode:cheat")],
            [InlineKeyboardButton(text=t("mm_glossary", lang), callback_data="mode:glossary")],
            [InlineKeyboardButton(text=t("mm_stats", lang), callback_data="mode:stats")],
            [InlineKeyboardButton(text=t("mm_reset", lang), callback_data="mode:reset")],
        ]
    )


def language_kb() -> InlineKeyboardMarkup:
    """Пикер языка интерфейса: RU / PL / UA / EN → callback_data «lang:<code>»."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LANG_LABELS[code], callback_data=f"lang:{code}")]
        for code in SUPPORTED
    ])


def quiz_app_reply_kb(lang: str = "ru") -> ReplyKeyboardMarkup | None:
    """
    Постоянная reply-клавиатура с кнопкой запуска Mini App «Тесты».
    Только reply-кнопка WebApp умеет возвращать данные через sendData,
    поэтому приложение тестов запускаем именно отсюда. Если URL не задан —
    клавиатуры нет (None), приложение недоступно, чат-режимы работают как есть.
    """
    if not WEBAPP_QUIZ_URL:
        return None
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("quiz_reply_btn", lang),
                                  web_app=WebAppInfo(url=WEBAPP_QUIZ_URL))]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=t("quiz_placeholder", lang),
    )


def topics_kb(lang: str = "ru") -> InlineKeyboardMarkup:
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
    rows.append([InlineKeyboardButton(text=t("back_menu", lang), callback_data="mode:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def next_question_kb(callback: str, label: str | None = None,
                     study_qid: str | None = None, lang: str = "ru") -> InlineKeyboardMarkup:
    if label is None:
        label = t("next_question", lang)
    rows = [[InlineKeyboardButton(text=label, callback_data=callback)]]
    if study_qid:
        rows.append([InlineKeyboardButton(text=t("more_details", lang), callback_data=f"study:{study_qid}")])
    rows.append([InlineKeyboardButton(text=t("back_menu", lang), callback_data="mode:menu")])
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
    explanation = _truncate(question.get("expl", ""), POLL_EXPL_LIMIT)   # 200, не 300
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
        "ts": int(time.time()),   # для TTL-очистки при загрузке
    }
    _save_polls()
    mark_seen(user_id, question["id"])


# ──────────────────────────── Хэндлеры команд ────────────────────────────

dp = Dispatcher()

# Бот рассчитан на ЛИЧНЫЕ чаты: прогресс, экзамен и quiz привязаны к одному
# пользователю. В группах модель ответов на poll работает иначе, поэтому
# в группах вежливо отправляем в личку и дальше не обрабатываем.

@dp.message(~F.chat.type.in_({"private"}))
async def group_redirect(message: Message) -> None:
    try:
        lang = norm_lang(message.from_user.language_code)
        me = await message.bot.get_me()
        await message.reply(t("group_redirect", lang, username=me.username))
    except Exception:  # noqa: BLE001
        pass


@dp.callback_query(~F.message.chat.type.in_({"private"}))
async def group_cb_redirect(cb: CallbackQuery) -> None:
    lang = norm_lang(cb.from_user.language_code)
    await cb.answer(t("group_cb_redirect", lang), show_alert=True)


# ─────────────────────────── Благодарность автору (Telegram Stars) ───────────────────────────
# Донат в Telegram Stars (валюта XTR). Провайдер не нужен, provider_token пустой.
# Поток: Mini App «Поддержать» → deep-link /start donate → выбор суммы → invoice →
# pre_checkout approve → successful_payment → спасибо. Оплата опциональна.
DONATE_TIERS = [
    ("donate_coffee", 50),
    ("donate_thanks_tier", 100),
    ("donate_generous", 300),
]


def donate_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"{t(label_key, lang)} · {amount} ⭐",
                                  callback_data=f"donate:{amount}")]
            for label_key, amount in DONATE_TIERS]
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def show_donate_options(message: Message) -> None:
    lang = user_lang(message.from_user.id)
    await message.answer(
        t("donate_intro", lang),
        reply_markup=donate_kb(lang),
    )


@dp.callback_query(F.data.startswith("donate:"))
async def cb_donate(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    try:
        amount = int(cb.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await cb.answer(t("donate_bad_amount", lang))
        return
    if amount < 1 or amount > 100000:
        await cb.answer(t("donate_bad_amount", lang))
        return
    await cb.answer()
    # Счёт в Stars: currency="XTR", provider_token="" (для Stars не требуется).
    await cb.message.answer_invoice(
        title=t("donate_invoice_title", lang),
        description=t("donate_invoice_desc", lang),
        payload=f"donate_{amount}",
        currency="XTR",
        prices=[LabeledPrice(label=t("donate_price", lang, amount=amount), amount=amount)],
        provider_token="",
    )


@dp.pre_checkout_query()
async def on_pre_checkout(pcq: PreCheckoutQuery) -> None:
    # Для Stars всегда подтверждаем (никаких внешних платёжных проверок).
    await pcq.answer(ok=True)


@dp.message(F.successful_payment)
async def on_successful_payment(message: Message) -> None:
    sp = message.successful_payment
    stars = sp.total_amount if sp else 0
    lang = user_lang(message.from_user.id)
    await message.answer(t("donate_payment_thanks", lang, stars=stars))


@dp.message(Command("donate"))
async def cmd_donate(message: Message) -> None:
    await show_donate_options(message)


@dp.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject | None = None) -> None:
    # Deep-link «/start donate» из кнопки «Поддержать» в Mini App → выбор суммы ⭐.
    if command and (command.args or "").strip() == "donate":
        await show_donate_options(message)
        return

    # Язык: если ещё не выбран — определяем по языку клиента Telegram и запоминаем.
    uid = message.from_user.id
    stored = load_progress(uid).get("lang")
    if stored in SUPPORTED:
        lang = stored
    else:
        lang = norm_lang(message.from_user.language_code)
        set_user_lang(uid, lang)

    # Если развёрнут Mini App — делаем его ГЛАВНЫМ входом: крупная кнопка-приложение
    # первым сообщением. Весь тренажёр (тесты с разбором, конспект, калькуляторы,
    # повторение, прогресс) удобнее в приложении; чат-режимы — как быстрый доступ.
    if WEBAPP_HOME_URL:
        await message.answer(
            t("start_webapp", lang, n=len(QUESTIONS)),
            reply_markup=main_menu_kb(lang),
        )
        return

    # Fallback без Mini App — как было: всё в чате.
    await message.answer(
        t("start_fallback", lang, n=len(QUESTIONS), disclaimer=t("disclaimer", lang)),
        reply_markup=main_menu_kb(lang),
    )
    rk = quiz_app_reply_kb(lang)
    if rk:
        await message.answer(t("start_quiz_note", lang), reply_markup=rk)


@dp.message(Command("tests"))
async def cmd_tests(message: Message) -> None:
    lang = user_lang(message.from_user.id)
    rk = quiz_app_reply_kb(lang)
    if rk:
        await message.answer(t("tests_available", lang), reply_markup=rk)
    else:
        await message.answer(t("tests_unavailable", lang), reply_markup=main_menu_kb(lang))


@dp.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    lang = user_lang(message.from_user.id)
    text = t("menu_webapp", lang) if WEBAPP_HOME_URL else t("menu_plain", lang)
    await message.answer(text, reply_markup=main_menu_kb(lang))


@dp.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    await show_stats(message.bot, message.chat.id, message.from_user.id)


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    lang = user_lang(message.from_user.id)
    await message.answer(t("help", lang))


@dp.message(Command("language"))
async def cmd_language(message: Message) -> None:
    lang = user_lang(message.from_user.id)
    await message.answer(t("language_pick", lang), reply_markup=language_kb())


@dp.callback_query(F.data.startswith("lang:"))
async def cb_lang(cb: CallbackQuery) -> None:
    code = cb.data.split(":", 1)[1]
    if code not in SUPPORTED:
        await cb.answer(t("donate_bad_amount", user_lang(cb.from_user.id)))
        return
    set_user_lang(cb.from_user.id, code)
    await cb.answer()
    # Подтверждение и меню — уже на НОВОМ языке.
    await cb.message.answer(t("language_changed", code), reply_markup=main_menu_kb(code))


@dp.message(Command("about"))
async def cmd_about(message: Message) -> None:
    lang = user_lang(message.from_user.id)
    await message.answer(t("about_title", lang, disclaimer=t("disclaimer", lang)))


@dp.message(Command("calc"))
async def cmd_calc(message: Message) -> None:
    lang = user_lang(message.from_user.id)
    CALC_STATE.pop(message.from_user.id, None)
    await message.answer(t("calc_compass_intro", lang), reply_markup=calc_menu_kb(lang))


@dp.message(Command("privacy"))
async def cmd_privacy(message: Message) -> None:
    lang = user_lang(message.from_user.id)
    await message.answer(t("privacy", lang))


async def show_stats(bot: Bot, chat_id: int, user_id: int) -> None:
    lang = user_lang(user_id)
    prog = load_progress(user_id)
    answered = prog["stats"]["answered"]
    correct = prog["stats"]["correct"]
    pct = round(correct / answered * 100) if answered else 0
    wrong_n = len(prog["wrong"])
    seen_n = len(set(prog["seen"]) & set(QUESTIONS_BY_ID))
    await bot.send_message(
        chat_id,
        t("stats", lang, answered=answered, correct=correct, pct=pct,
          wrong_n=wrong_n, seen_n=seen_n, total=len(QUESTIONS)),
        reply_markup=main_menu_kb(lang),
    )


# ──────────────────────────── Обработка нажатий меню ────────────────────────────

@dp.callback_query(F.data == "mode:menu")
async def cb_menu(cb: CallbackQuery) -> None:
    # Сбрасываем «ожидающие ввод» режимы, чтобы текст не уходил не туда.
    CALC_STATE.pop(cb.from_user.id, None)
    GLOSSARY_SEARCH.discard(cb.from_user.id)
    ACTIVE_TASK.pop(cb.from_user.id, None)
    ACTIVE_PTASK.pop(cb.from_user.id, None)
    lang = user_lang(cb.from_user.id)
    text = t("menu_webapp", lang) if WEBAPP_HOME_URL else t("menu_plain", lang)
    await cb.message.answer(text, reply_markup=main_menu_kb(lang))
    await cb.answer()


@dp.callback_query(F.data == "mode:random")
async def cb_random(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    lang = user_lang(user_id)
    chosen = pick_unseen(user_id, QUESTIONS, 1)
    if not chosen:
        await cb.message.answer(t("no_questions_left", lang), reply_markup=main_menu_kb(lang))
        await cb.answer()
        return
    await send_quiz(cb.bot, cb.message.chat.id, user_id, chosen[0], mode="random")
    left = remaining_in_pool(user_id, QUESTIONS)
    sq = chosen[0]["id"] if chosen[0].get("study") else None
    await cb.message.answer(
        t("remaining_in_circle", lang, left=left),
        reply_markup=next_question_kb("mode:random", study_qid=sq, lang=lang),
    )
    await cb.answer()


@dp.callback_query(F.data == "mode:topics")
async def cb_topics(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    await cb.message.answer(t("choose_topic", lang), reply_markup=topics_kb(lang))
    await cb.answer()


@dp.callback_query(F.data.startswith("topic:"))
async def cb_topic_question(cb: CallbackQuery) -> None:
    topic = cb.data.split(":", 1)[1]
    user_id = cb.from_user.id
    lang = user_lang(user_id)
    pool = topic_questions(topic)
    chosen = pick_unseen(user_id, pool, 1)
    if not chosen:
        await cb.message.answer(t("topic_empty", lang), reply_markup=topics_kb(lang))
        await cb.answer()
        return
    await send_quiz(cb.bot, cb.message.chat.id, user_id, chosen[0], mode=f"topic:{topic}")
    left = remaining_in_pool(user_id, pool)
    sq = chosen[0]["id"] if chosen[0].get("study") else None
    await cb.message.answer(
        t("topic_remaining", lang, topic=topic, left=left),
        reply_markup=next_question_kb(f"topic:{topic}", t("next_topic", lang), study_qid=sq, lang=lang),
    )
    await cb.answer()


@dp.callback_query(F.data == "mode:mistakes")
async def cb_mistakes(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    lang = user_lang(user_id)
    prog = load_progress(user_id)
    wrong_ids = [qid for qid in prog["wrong"] if qid in QUESTIONS_BY_ID]
    if not wrong_ids:
        await cb.message.answer(t("mistakes_none", lang), reply_markup=main_menu_kb(lang))
        await cb.answer()
        return
    qid = random.choice(wrong_ids)
    question = QUESTIONS_BY_ID[qid]
    await send_quiz(cb.bot, cb.message.chat.id, user_id, question, mode="mistakes")
    sq = question["id"] if question.get("study") else None
    await cb.message.answer(
        t("mistakes_remaining", lang, n=len(wrong_ids)),
        reply_markup=next_question_kb("mode:mistakes", t("next_mistake", lang), study_qid=sq, lang=lang),
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
    lang = user_lang(cb.from_user.id)
    question = QUESTIONS_BY_ID.get(qid)
    study = (question or {}).get("study")
    if not study:
        await cb.answer(t("no_details", lang))
        return
    text = _truncate(t("study_more", lang, study=study), 4000)
    await cb.message.answer(text)
    await cb.answer()


@dp.callback_query(F.data == "mode:reset")
async def cb_reset(cb: CallbackQuery) -> None:
    # Сброс необратим — требуем подтверждение вторым тапом, чтобы случайное
    # нажатие в меню не стёрло весь прогресс.
    lang = user_lang(cb.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("reset_confirm_btn", lang), callback_data="mode:reset_confirm")],
        [InlineKeyboardButton(text=t("cancel", lang), callback_data="mode:menu")],
    ])
    await cb.message.answer(t("reset_prompt", lang), reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data == "mode:reset_confirm")
async def cb_reset_confirm(cb: CallbackQuery) -> None:
    # Сохраняем выбранный язык при сбросе прогресса — это настройка, не «прогресс».
    lang = user_lang(cb.from_user.id)
    save_progress(cb.from_user.id,
                  {"seen": [], "wrong": [], "stats": {"answered": 0, "correct": 0}, "lang": lang})
    await cb.message.answer(t("reset_done", lang), reply_markup=main_menu_kb(lang))
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
        "ts": int(time.time()),   # для TTL-очистки при загрузке
    }
    _save_exams()
    lang = user_lang(user_id)
    await cb.message.answer(
        t("exam_started", lang, n=len(chosen), **{"pass": EXAM_PASS_PERCENT}),
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
    lang = user_lang(user_id)
    await bot.send_message(chat_id, t("exam_question_counter", lang,
                                      i=exam["idx"] + 1, n=len(exam["queue"])))
    await send_quiz(bot, chat_id, user_id, question, mode="exam", is_exam=True)


async def finish_exam(bot: Bot, chat_id: int, user_id: int) -> None:
    exam = EXAMS.pop(user_id, None)
    if not exam:
        return
    _save_exams()   # экзамен завершён — убираем из персистентного стора
    lang = user_lang(user_id)
    total = len(exam["queue"])
    correct = exam["correct"]
    pct = round(correct / total * 100) if total else 0
    passed = pct >= EXAM_PASS_PERCENT
    verdict = t("exam_passed", lang) if passed else t("exam_failed", lang)

    header = t("exam_finished_header", lang, correct=correct, total=total,
               pct=pct, verdict=verdict, **{"pass": EXAM_PASS_PERCENT})
    wrong = [qid for qid, ok in exam["results"] if not ok]
    if not wrong:
        await bot.send_message(chat_id, header + "\n\n" + t("exam_no_errors", lang),
                               reply_markup=main_menu_kb(lang))
        return

    # Разбор ошибок может быть длинным (до 100 вопросов) — режем на части
    # по лимиту Telegram, чтобы сообщение не упало.
    blocks = [header, t("error_review_header", lang)]
    for qid in wrong:
        q = QUESTIONS_BY_ID[qid]
        correct_opt = q["options"][q["answer"]]
        blocks.append(f"• [{q['topic']}] {q['q']}\n  ✔️ {correct_opt}")
    blocks.append(t("added_to_mistakes", lang))
    blocks.append("\n" + t("disclaimer", lang))

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
        kb = main_menu_kb(lang) if i == len(parts) - 1 else None
        await bot.send_message(chat_id, part, reply_markup=kb)


# ──────────────────────────── Обработка ответа на quiz ────────────────────────────

@dp.poll_answer()
async def on_poll_answer(poll_answer: PollAnswer) -> None:
    info = ACTIVE_POLLS.pop(poll_answer.poll_id, None)
    if not info:
        # Ответ на «потерянный» опрос: опрос старше TTL, либо уже отвеченный.
        # Активные опросы переживают рестарт (см. _load_sessions), так что это
        # уже действительно мусор — молча игнорируем, но фиксируем в логе.
        log.info("stale poll_answer: poll_id=%s user=%s",
                 poll_answer.poll_id, getattr(poll_answer.user, "id", "?"))
        return
    _save_polls()   # опрос отвечен — снимаем привязку из персистентного стора
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
            exam["ts"] = int(time.time())   # экзамен активен — обновляем TTL
            _save_exams()   # сохраняем прогресс до следующего вопроса (переживёт рестарт)
            # Небольшая пауза, чтобы пользователь увидел подсветку ответа.
            await asyncio.sleep(1.0)
            # chat_id == user_id для приватных чатов
            await send_next_exam_question(poll_answer.bot, user_id, user_id)
        else:
            # экзамен живёт в памяти и теряется при перезапуске бота — честно
            # сообщаем, а не игнорируем молча ответ на «осиротевший» вопрос.
            with contextlib.suppress(Exception):
                await poll_answer.bot.send_message(
                    user_id, t("exam_inactive", user_lang(user_id)),
                )


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

def konspekt_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, key in enumerate(content.KONSPEKT_ORDER, 1):
        title = content.KONSPEKT_BTN.get(key, content.KONSPEKT[key][0])
        row.append(InlineKeyboardButton(text=title, callback_data=f"kon:{key}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t("back_menu", lang), callback_data="mode:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data == "mode:konspekt")
async def cb_konspekt(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    await cb.message.answer(t("konspekt_intro", lang), reply_markup=konspekt_menu_kb(lang))
    await cb.answer()


@dp.callback_query(F.data.startswith("kon:"))
async def cb_konspekt_page(cb: CallbackQuery) -> None:
    key = cb.data.split(":", 1)[1]
    lang = user_lang(cb.from_user.id)
    page = content.KONSPEKT.get(key)
    if not page:
        await cb.answer(t("topic_not_found", lang))
        return
    await cb.message.answer(page[1])
    await send_images(cb.bot, cb.message.chat.id, content.KONSPEKT_IMAGES.get(key, []))
    await cb.message.answer(t("konspekt_next", lang), reply_markup=konspekt_menu_kb(lang))
    await cb.answer()


# ──────────────────────────── Шпаргалки ────────────────────────────

def cheat_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, key in enumerate(content.CHEATSHEET_ORDER, 1):
        title = content.CHEATSHEET_BTN.get(key, content.CHEATSHEETS[key][0])
        row.append(InlineKeyboardButton(text=title, callback_data=f"chs:{key}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t("back_menu", lang), callback_data="mode:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data == "mode:cheat")
async def cb_cheat(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    await cb.message.answer(t("cheat_intro", lang), reply_markup=cheat_menu_kb(lang))
    await cb.answer()


@dp.callback_query(F.data.startswith("chs:"))
async def cb_cheat_page(cb: CallbackQuery) -> None:
    key = cb.data.split(":", 1)[1]
    lang = user_lang(cb.from_user.id)
    # Узлы — отдельное подменю с пошаговыми фото.
    if key == "knots":
        page = content.CHEATSHEETS["knots"]
        await cb.message.answer(page[1])
        await cb.message.answer(t("choose_knot", lang), reply_markup=knots_menu_kb(lang))
        await cb.answer()
        return
    page = content.CHEATSHEETS.get(key)
    if not page:
        await cb.answer(t("cheat_not_found", lang))
        return
    await cb.message.answer(page[1])
    await send_images(cb.bot, cb.message.chat.id, content.CHEATSHEET_IMAGES.get(key, []))
    await cb.message.answer(t("cheat_next", lang), reply_markup=cheat_menu_kb(lang))
    await cb.answer()


# ── Узлы: подменю с фото по шагам ──

def knots_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, key in enumerate(content.KNOTS_ORDER, 1):
        title = content.KNOTS[key][0]
        row.append(InlineKeyboardButton(text=title, callback_data=f"knot:{key}"))
        if i % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=t("back_cheat", lang), callback_data="mode:cheat")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data.startswith("knot:"))
async def cb_knot(cb: CallbackQuery) -> None:
    key = cb.data.split(":", 1)[1]
    lang = user_lang(cb.from_user.id)
    knot = content.KNOTS.get(key)
    if not knot:
        await cb.answer(t("knot_not_found", lang))
        return
    title, descr, steps = knot
    await cb.message.answer(f"{title}\n\n{descr}")
    await send_images(cb.bot, cb.message.chat.id, steps)
    await cb.message.answer(t("knot_done", lang), reply_markup=knots_menu_kb(lang))
    await cb.answer()


# ──────────────────────────── Словарь яхтсмена ────────────────────────────

GLOSSARY_PAGE = 8  # терминов на страницу


def glossary_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
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
    rows.append([InlineKeyboardButton(text=t("glossary_search_btn", lang), callback_data="gl:search")])
    rows.append([InlineKeyboardButton(text=t("back_menu", lang), callback_data="mode:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def glossary_terms_kb(cat: str, page: int, lang: str = "ru") -> InlineKeyboardMarkup:
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
    rows.append([InlineKeyboardButton(text=t("back_categories", lang), callback_data="mode:glossary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data == "mode:glossary")
async def cb_glossary(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    GLOSSARY_SEARCH.discard(cb.from_user.id)
    await cb.message.answer(
        t("glossary_intro", lang, n=glossary.total_count()),
        reply_markup=glossary_menu_kb(lang),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("gl:cat:"))
async def cb_glossary_cat(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    rest = cb.data[len("gl:cat:"):]  # <key>[:page]
    if ":" in rest:
        key, page = rest.split(":", 1)
        page = int(page) if page.isdigit() else 0
    else:
        key, page = rest, 0
    cat = glossary.KEY_CATEGORY.get(key)
    if not cat:
        await cb.answer(t("category_not_found", lang))
        return
    icon = glossary.CATEGORY_ICONS.get(cat, "📚")
    await cb.message.answer(f"{icon} <b>{cat}</b>\n{t('choose_term', lang)}",
                            reply_markup=glossary_terms_kb(cat, page, lang))
    await cb.answer()


@dp.callback_query(F.data.startswith("gl:t:"))
async def cb_glossary_term(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    rest = cb.data[len("gl:t:"):]  # <key>:<idx>
    key, idx = rest.rsplit(":", 1)
    cat = glossary.KEY_CATEGORY.get(key)
    items = glossary.YACHTING_GLOSSARY.get(cat, []) if cat else []
    try:
        it = items[int(idx)]
    except (ValueError, IndexError):
        await cb.answer(t("term_not_found", lang))
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("back_list", lang), callback_data=f"gl:cat:{key}")],
        [InlineKeyboardButton(text=t("categories_btn", lang), callback_data="mode:glossary")],
    ])
    await cb.message.answer(glossary.render(cat, it), reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data == "gl:search")
async def cb_glossary_search(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    GLOSSARY_SEARCH.add(cb.from_user.id)
    await cb.message.answer(t("glossary_search_prompt", lang))
    await cb.answer()


# ──────────────────────────── Решение задач T-V-M-D-C ────────────────────────────

# ──────────────────────────── Практические задачи (S-D-T / ETA) ────────────────────────────

def ptask_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("ptask_new", lang), callback_data="ptask:new")],
        [InlineKeyboardButton(text=t("ptask_solve_btn", lang), callback_data="ptask:solve")],
        [InlineKeyboardButton(text=t("ptask_stats_btn", lang), callback_data="ptask:stats")],
        [InlineKeyboardButton(text=t("calc_btn", lang), callback_data="mode:calc")],
        [InlineKeyboardButton(text=t("back_menu", lang), callback_data="mode:menu")],
    ])


async def _send_ptask(bot: Bot, chat_id: int, user_id: int, task: marine.MarineTask) -> None:
    ACTIVE_PTASK[user_id] = task.id
    lang = user_lang(user_id)
    await bot.send_message(
        chat_id,
        t("ptask_prompt", lang, text=task.text, unit=task.unit, tol=marine._num(task.tol)),
        reply_markup=ptask_kb(lang),
    )


@dp.callback_query(F.data == "mode:ptasks")
async def cb_ptasks(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    await cb.message.answer(t("ptasks_intro", lang), reply_markup=ptask_kb(lang))
    await _send_ptask(cb.bot, cb.message.chat.id, cb.from_user.id, random.choice(marine.TASKS))
    await cb.answer()


@dp.callback_query(F.data == "ptask:new")
async def cb_ptask_new(cb: CallbackQuery) -> None:
    await _send_ptask(cb.bot, cb.message.chat.id, cb.from_user.id, random.choice(marine.TASKS))
    await cb.answer()


@dp.callback_query(F.data == "ptask:solve")
async def cb_ptask_solve(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    tid = ACTIVE_PTASK.get(cb.from_user.id)
    task = marine.TASKS_BY_ID.get(tid) if tid else None
    if not task:
        await cb.answer(t("take_task_first", lang))
        return
    await cb.message.answer(
        t("ptask_solution", lang, text=task.text, solution=task.solution,
          answer=marine._num(task.answer), unit=task.unit),
        reply_markup=ptask_kb(lang),
    )
    await cb.answer()


@dp.callback_query(F.data == "ptask:stats")
async def cb_ptask_stats(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    p = load_progress(cb.from_user.id).get("ptasks", {"solved": 0, "attempts": 0, "streak": 0, "best": 0})
    att, solved = p["attempts"], p["solved"]
    acc = round(solved / att * 100) if att else 0
    await cb.message.answer(
        t("ptask_stats", lang, solved=solved, att=att, acc=acc,
          streak=p["streak"], best=p["best"], total=len(marine.TASKS)),
        reply_markup=ptask_kb(lang),
    )
    await cb.answer()


def task_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("task_new", lang), callback_data="task:new"),
             InlineKeyboardButton(text=t("task_star", lang), callback_data="task:star")],
            [InlineKeyboardButton(text=t("task_solve_btn", lang), callback_data="task:solve")],
            [InlineKeyboardButton(text=t("task_stats_btn", lang), callback_data="task:stats")],
            [InlineKeyboardButton(text=t("back_menu", lang), callback_data="mode:menu")],
        ]
    )


async def _send_task(bot: Bot, chat_id: int, user_id: int, task: nav_tasks.NavTask) -> None:
    ACTIVE_TASK[user_id] = task.id
    lang = user_lang(user_id)
    star = t("task_star_note", lang) if task.starred else ""
    await bot.send_message(
        chat_id,
        t("task_prompt", lang, star=star, text=task.text),
        reply_markup=task_kb(lang),
    )


@dp.callback_query(F.data == "mode:tasks")
async def cb_tasks(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    await cb.message.answer(t("tasks_intro", lang), reply_markup=task_kb(lang))
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
    lang = user_lang(cb.from_user.id)
    task_id = ACTIVE_TASK.get(cb.from_user.id)
    task = nav_tasks.TASKS_BY_ID.get(task_id) if task_id else None
    if not task:
        # активная задача живёт в памяти и сбрасывается при перезапуске бота
        await cb.answer(t("task_inactive", lang), show_alert=True)
        return
    await cb.message.answer(
        t("task_solution", lang, text=task.text, solution=task.solution,
          answer=f"{task.answer:.0f}"),
        reply_markup=task_kb(lang),
    )
    await cb.answer()


@dp.callback_query(F.data == "task:stats")
async def cb_task_stats(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    tk = load_progress(cb.from_user.id)["tasks"]
    att, solved = tk["attempts"], tk["solved"]
    acc = round(solved / att * 100) if att else 0
    await cb.message.answer(
        t("task_stats", lang, solved=solved, att=att, acc=acc,
          streak=tk["streak"], best=tk["best"], total=len(nav_tasks.TASKS),
          starred=len(nav_tasks.starred_tasks())),
        reply_markup=task_kb(lang),
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


def calc_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    # Если развёрнут Mini App — первой кнопкой даём удобный визуальный калькулятор.
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton(
            text=t("open_calc_app", lang),
            web_app=WebAppInfo(url=WEBAPP_URL))])
    rows += [[InlineKeyboardButton(text=label, callback_data=f"calc:dir:{s}{d}")]
             for s, d, label in CALC_DIRS]
    rows.append([InlineKeyboardButton(text=t("back_sections", lang), callback_data="mode:calc")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def calc_result_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("calc_result_other", lang), callback_data="calc:cat:compass")],
        [InlineKeyboardButton(text=t("calc_result_train", lang), callback_data="mode:tasks")],
        [InlineKeyboardButton(text=t("back_sections", lang), callback_data="mode:calc")],
    ])


def _calc_prompt(src: str, dst: str, lang: str = "ru") -> str:
    """Подсказка по вводу: какие поправки нужны для выбранного направления."""
    # T↔M использует Variation, M↔C — Deviation; для T↔C нужны обе.
    pair = {src, dst}
    if pair == {"T", "M"}:
        fields, example, hint = t("calc_fields_var", lang), "100 6E", t("calc_hint_var", lang)
    elif pair == {"M", "C"}:
        fields, example, hint = t("calc_fields_dev", lang), "120 4W", t("calc_hint_dev", lang)
    else:  # T↔C
        fields, example, hint = t("calc_fields_both", lang), "045 3W 2E", t("calc_hint_both", lang)
    return t("calc_prompt_body", lang, fields=fields, hint=hint, example=example)


def calc_categories_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton(
            text=t("open_calc_app", lang),
            web_app=WebAppInfo(url=WEBAPP_URL))])
    rows += [
        [InlineKeyboardButton(text=t("cat_compass", lang), callback_data="calc:cat:compass")],
        [InlineKeyboardButton(text=t("cat_time_eta", lang), callback_data="calc:cat:marine")],
        [InlineKeyboardButton(text=t("back_menu", lang), callback_data="mode:menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.callback_query(F.data == "mode:calc")
async def cb_calc(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    CALC_STATE.pop(cb.from_user.id, None)
    await cb.message.answer(t("calc_sections", lang), reply_markup=calc_categories_kb(lang))
    await cb.answer()


@dp.callback_query(F.data == "calc:cat:compass")
async def cb_calc_compass(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    CALC_STATE.pop(cb.from_user.id, None)
    await cb.message.answer(t("calc_compass_pick", lang), reply_markup=calc_menu_kb(lang))
    await cb.answer()


# ── Раздел «Скорость · время · ETA» ──
# kind: t=время, d=дистанция, v=скорость, e=ETA, tide=прилив.
# Значение: (title_key, need_key, пример ввода). Title/need локализуются через t().
MARINE_KINDS = {
    "t": ("mk_t_title", "mk_t_need", "5.5 13.2"),
    "d": ("mk_d_title", "mk_d_need", "6 2.5"),
    "v": ("mk_v_title", "mk_v_need", "15 3"),
    "e": ("mk_e_title", "mk_e_need", "18 5 20 09:00"),
    "tide": ("mk_tide_title", "mk_tide_need", "2 8 3.5"),
}


def marine_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=t(MARINE_KINDS[k][0], lang), callback_data=f"calc:m:{k}")]
            for k in ("t", "d", "v", "e", "tide")]
    rows.append([InlineKeyboardButton(text=t("back_sections", lang), callback_data="mode:calc")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def marine_result_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("marine_result_more", lang), callback_data="calc:cat:marine")],
        [InlineKeyboardButton(text=t("mm_ptasks", lang), callback_data="mode:ptasks")],
        [InlineKeyboardButton(text=t("back_sections", lang), callback_data="mode:calc")],
    ])


@dp.callback_query(F.data == "calc:cat:marine")
async def cb_calc_marine(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    CALC_STATE.pop(cb.from_user.id, None)
    await cb.message.answer(t("marine_pick", lang), reply_markup=marine_menu_kb(lang))
    await cb.answer()


@dp.callback_query(F.data.startswith("calc:m:"))
async def cb_calc_marine_kind(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    kind = cb.data[len("calc:m:"):]
    if kind not in MARINE_KINDS:
        await cb.answer(t("unknown_calc", lang))
        return
    CALC_STATE[cb.from_user.id] = {"marine": kind}
    title_key, need_key, example = MARINE_KINDS[kind]
    await cb.message.answer(
        t("marine_input_prompt", lang, title=t(title_key, lang),
          need=t(need_key, lang), example=example),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("back", lang), callback_data="calc:cat:marine")],
        ]),
    )
    await cb.answer()


def _marine_numbers(text: str) -> list[float]:
    import re
    return [float(x.replace(",", ".")) for x in re.findall(r"[-+]?\d+(?:[.,]\d+)?", text)]


def compute_marine(kind: str, text: str, lang: str = "ru") -> str:
    """
    Посчитать выбранный морской расчёт по строке ввода. Бросает ValueError
    с понятным (локализованным) текстом, если данных не хватает или они
    некорректны.
    """
    nums = _marine_numbers(text)
    if kind == "t":
        if len(nums) < 2:
            raise ValueError(t("err_need_speed_dist", lang))
        v, d = nums[0], nums[1]
        h = marine.time_from(d, v, lang)
        return t("marine_res_time", lang, h=round(h, 2), hm=marine.hours_to_hm(h, lang),
                 d=marine._num(d), v=marine._num(v))
    if kind == "d":
        if len(nums) < 2:
            raise ValueError(t("err_need_speed_time", lang))
        v, tm = nums[0], nums[1]
        d = marine.distance_from(v, tm)
        return t("marine_res_dist", lang, d=round(d, 1),
                 v=marine._num(v), t=marine._num(tm))
    if kind == "v":
        if len(nums) < 2:
            raise ValueError(t("err_need_dist_time", lang))
        d, tm = nums[0], nums[1]
        v = marine.speed_from(d, tm, lang)
        return t("marine_res_speed", lang, v=round(v, 1),
                 d=marine._num(d), t=marine._num(tm))
    if kind == "e":
        # дистанция, скорость, [запас%], [старт ЧЧ:ММ]
        import re
        if len(nums) < 2:
            raise ValueError(t("err_need_dist_speed", lang))
        d, v = nums[0], nums[1]
        reserve = nums[2] if len(nums) >= 3 else 0.0
        mt = re.search(r"\b(\d{1,2}[:.]\d{2})\b", text)
        start = mt.group(1).replace(".", ":") if mt else None
        r = marine.plan_eta(d, v, reserve, start, lang)
        lines = [t("marine_eta_line_t", lang, d=marine._num(d), v=marine._num(v),
                   travel=round(r.travel_h, 2))]
        if reserve:
            lines.append(t("marine_eta_line_reserve", lang, r=marine._num(reserve),
                           w=round(r.travel_h_reserve, 2)))
        body = "\n".join(lines)
        head = t("marine_eta_head", lang, w=round(r.travel_h_reserve, 2),
                 hm=marine.hours_to_hm(r.travel_h_reserve, lang))
        if r.eta:
            head += t("marine_eta_arrival", lang, eta=r.eta)
        return f"{head}\n\n<pre>{body}</pre>"
    if kind == "tide":
        # LW, HW, часы после малой воды (по правилу двенадцатых)
        if len(nums) < 3:
            raise ValueError(t("err_need_tide", lang))
        lw, hw, hours = nums[0], nums[1], nums[2]
        water = tides.height_after_lw(hw, lw, hours)
        rng = hw - lw
        rows = [t("marine_tide_range", lang, hw=tides._num(hw), lw=tides._num(lw),
                  rng=tides._num(rng), tw=tides._num(rng / 12))]
        acc = lw
        for i, part in enumerate(tides.TWELFTHS, start=1):
            acc += rng * part / 12
            rows.append(t("marine_tide_step", lang, i=i, part=part, acc=tides._num(acc)))
        return t("marine_tide_header", lang, hours=tides._num(hours),
                 water=tides._num(water), rows="\n".join(rows))
    raise ValueError(t("unknown_calc", lang))


@dp.callback_query(F.data.startswith("calc:dir:"))
async def cb_calc_dir(cb: CallbackQuery) -> None:
    lang = user_lang(cb.from_user.id)
    code = cb.data[len("calc:dir:"):]  # напр. "TC"
    src, dst = code[0], code[1]
    if src not in calc.POINTS or dst not in calc.POINTS or src == dst:
        await cb.answer(t("unknown_direction", lang))
        return
    CALC_STATE[cb.from_user.id] = {"src": src, "dst": dst}
    label = next((l for s, d, l in CALC_DIRS if s == src and d == dst), f"{src}→{dst}")
    await cb.message.answer(
        t("calc_dir_header", lang, label=label, prompt=_calc_prompt(src, dst, lang)),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("back", lang), callback_data="mode:calc")],
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


def _format_calc_result(res: dict, lang: str = "ru") -> str:
    steps = "\n".join(s["text"] for s in res["steps"])
    return (
        f"✅ <b>{res['from']} → {res['to']} = {res['answer']:03d}°</b>\n\n"
        f"<pre>{steps}</pre>\n"
        f"<i>{calc.rule_hint(res['direction'], lang)}</i>"
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
    lang = user_lang(user_id)
    try:
        payload = json.loads(message.web_app_data.data)
    except (json.JSONDecodeError, TypeError):
        log.info("webapp_data: bad json from user=%s", user_id)
        await message.answer(t("webapp_bad_read", lang))
        return

    parsed = parse_webapp_quiz(payload)
    if not parsed:
        await message.answer(t("webapp_empty", lang))
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
    tline = t("webapp_time", lang, m=secs // 60, s=secs % 60) if is_exam and secs else ""

    if is_exam:
        passed = pct >= EXAM_PASS_PERCENT
        verdict = t("exam_passed", lang) if passed else t("exam_failed", lang)
        head = t("webapp_exam_head", lang, correct=correct, counted=counted, pct=pct,
                 tline=tline, verdict=verdict, **{"pass": EXAM_PASS_PERCENT})
    else:
        label = mode.split(":", 1)[1] if mode.startswith("topic:") else t("random_label", lang)
        head = t("webapp_train_head", lang, label=label, correct=correct, counted=counted, pct=pct)

    wrong = [QUESTIONS_BY_ID[qid] for qid in parsed["wrong_ids"]]
    if not wrong:
        await message.answer(head + "\n\n" + t("webapp_no_errors", lang),
                            reply_markup=main_menu_kb(lang))
        return

    blocks = [head, t("error_review_header", lang)]
    for q in wrong:
        blocks.append(f"• [{q['topic']}] {q['q']}\n  ✔️ {q['options'][q['answer']]}")
    blocks.append(t("added_to_mistakes", lang))

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
        kb = main_menu_kb(lang) if i == len(parts) - 1 else None
        await message.answer(part, reply_markup=kb)


# ──────────────────────────── Текстовый ответ на задачу ────────────────────────────
# Срабатывает на любой НЕ-командный текст; если у пользователя активна задача —
# трактуем как ответ. Иначе мягко подсказываем меню.

@dp.message(F.text & ~F.text.startswith("/"))
async def on_text_answer(message: Message) -> None:
    user_id = message.from_user.id
    lang = user_lang(user_id)

    # 0) Калькулятор: ждём строку со значениями
    state = CALC_STATE.get(user_id)
    if state and "marine" in state:
        kind = state["marine"]
        try:
            out = compute_marine(kind, message.text, lang)
        except ValueError as e:
            await message.answer(
                f"🤔 {e}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=t("back", lang), callback_data="calc:cat:marine")],
                ]),
            )
            return
        CALC_STATE.pop(user_id, None)
        await message.answer(out, reply_markup=marine_result_kb(lang))
        return
    if state:
        src, dst = state["src"], state["dst"]
        pair = {src, dst}
        need_var = pair == {"T", "M"} or pair == {"T", "C"}
        need_dev = pair == {"M", "C"} or pair == {"T", "C"}
        parsed = _parse_calc_input(message.text, need_var, need_dev)
        if not parsed:
            await message.answer(
                t("calc_not_understood", lang, prompt=_calc_prompt(src, dst, lang)),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=t("back", lang), callback_data="mode:calc")],
                ]),
            )
            return
        try:
            res = calc.solve(src, dst, parsed["course"],
                             parsed["var"], parsed["var_dir"],
                             parsed["dev"], parsed["dev_dir"])
        except ValueError as e:
            await message.answer(f"⚠️ {e}", reply_markup=calc_result_kb(lang))
            CALC_STATE.pop(user_id, None)
            return
        CALC_STATE.pop(user_id, None)
        await message.answer(_format_calc_result(res, lang), reply_markup=calc_result_kb(lang))
        return

    # 1) Режим поиска по словарю
    if user_id in GLOSSARY_SEARCH:
        GLOSSARY_SEARCH.discard(user_id)
        hits = glossary.search(message.text)
        if not hits:
            await message.answer(t("glossary_not_found", lang),
                                 reply_markup=glossary_menu_kb(lang))
            return
        # первый результат — карточкой, остальные — кнопками
        cat0, it0 = hits[0]
        rows = []
        for cat, it in hits[1:10]:
            i = glossary.YACHTING_GLOSSARY[cat].index(it)
            key = glossary.CATEGORY_KEY[cat]
            rows.append([InlineKeyboardButton(text=f"{it['term']} ({cat})",
                                              callback_data=f"gl:t:{key}:{i}")])
        rows.append([InlineKeyboardButton(text=t("categories_btn", lang), callback_data="mode:glossary")])
        head = t("glossary_found", lang, n=len(hits)) if len(hits) > 1 else ""
        await message.answer(head + glossary.render(cat0, it0),
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        return

    # 2) Ответ на практическую задачу (скорость/время/ETA)
    ptid = ACTIVE_PTASK.get(user_id)
    if ptid:
        ptask = marine.TASKS_BY_ID.get(ptid)
        if not ptask:
            ACTIVE_PTASK.pop(user_id, None)
            await message.answer(t("task_not_found", lang), reply_markup=main_menu_kb(lang))
            return
        if ptask.check(message.text):
            ACTIVE_PTASK.pop(user_id, None)
            p = record_ptask(user_id, True)
            streak_line = t("streak_line", lang, n=p["streak"])
            if p["streak"] == p["best"] and p["streak"] >= 3:
                streak_line += t("record_suffix", lang)
            await message.answer(
                t("ptask_correct", lang, answer=marine._num(ptask.answer),
                  unit=ptask.unit, streak_line=streak_line, solution=ptask.solution),
                reply_markup=ptask_kb(lang),
            )
        else:
            p = record_ptask(user_id, False)
            await message.answer(
                t("ptask_wrong", lang, best=p["best"]),
                reply_markup=ptask_kb(lang),
            )
        return

    # 3) Ответ на задачу T-V-M-D-C
    task_id = ACTIVE_TASK.get(user_id)
    if not task_id:
        await message.answer(t("not_understood_menu", lang), reply_markup=main_menu_kb(lang))
        return
    task = nav_tasks.TASKS_BY_ID.get(task_id)
    if not task:
        ACTIVE_TASK.pop(user_id, None)
        await message.answer(t("task_not_found", lang), reply_markup=main_menu_kb(lang))
        return
    if task.check(message.text):
        ACTIVE_TASK.pop(user_id, None)
        tk = record_task(user_id, True)
        streak_line = t("streak_line", lang, n=tk["streak"])
        if tk["streak"] == tk["best"] and tk["streak"] >= 3:
            streak_line += t("record_suffix", lang)
        await message.answer(
            t("task_correct", lang, answer=f"{task.answer:.0f}",
              streak_line=streak_line, solution=task.solution),
            reply_markup=task_kb(lang),
        )
    else:
        tk = record_task(user_id, False)
        await message.answer(
            t("task_wrong", lang, best=tk["best"]),
            reply_markup=task_kb(lang),
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
    _load_sessions()   # восстановить активные экзамены/опросы после рестарта
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
