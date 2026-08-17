"""
Тесты пути «отправили quiz-poll → пришёл ответ» (волна A).

Проверяем ровно то, что волна A изменила в bot.py:
  • варианты перемешиваются, а правильный индекс пересчитывается — ответ
    засчитывается верно при ЛЮБОЙ перестановке;
  • голос чужого человека (пересланный опрос) не пишется в прогресс автора
    и не снимает привязку опроса;
  • ответ на опрос БРОШЕННОГО экзамена не двигает новый экзамен;
  • записи опросов, сохранённые до волны A (без ключа "ans"), обрабатываются
    по-старому — это важно, они переживают рестарт бота.

Telegram не нужен: bot.send_poll подменяем заглушкой.

Запуск:  python test_quiz_poll.py   (или pytest test_quiz_poll.py)
"""

import asyncio
import importlib.util
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).parent

fails = 0


def check(name, cond):
    global fails
    if cond:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name}")
        fails += 1


def _load_bot():
    spec = importlib.util.spec_from_file_location("bot", BASE / "bot.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _isolate(bot, tmp: Path):
    """Файлы сессий и прогресса — во временный каталог, боевые не трогаем."""
    bot._EXAMS_FILE = tmp / "exams.json"
    bot._POLLS_FILE = tmp / "active_polls.json"
    bot.PROGRESS_DIR = tmp / "progress"
    bot.PROGRESS_DIR.mkdir(exist_ok=True)
    bot.EXAMS.clear()
    bot.ACTIVE_POLLS.clear()


class FakePoll:
    def __init__(self, poll_id):
        self.id = poll_id


class FakeMessage:
    def __init__(self, poll_id):
        self.poll = FakePoll(poll_id)


class FakeBot:
    """Ловит вызовы send_poll вместо обращения к Telegram."""

    def __init__(self):
        self.sent = []

    async def send_poll(self, **kw):
        self.sent.append(kw)
        return FakeMessage(f"poll-{len(self.sent)}")

    async def send_message(self, *a, **kw):
        return None


class FakeUser:
    def __init__(self, uid):
        self.id = uid


class FakePollAnswer:
    def __init__(self, poll_id, user_id, option_ids):
        self.poll_id = poll_id
        self.user = FakeUser(user_id)
        self.option_ids = option_ids
        self.bot = FakeBot()


QUESTION = {
    "id": "q-test-1",
    "topic": "Навигация",
    "q": "Сколько градусов в румбе?",
    "options": ["11.25", "22.5", "45", "90"],
    "answer": 0,          # правильный — ПЕРВЫЙ вариант (позиционный биас банка)
    "expl": "360 / 32 = 11.25",
}


def _prepare(bot, tmp):
    _isolate(bot, Path(tmp))
    bot.QUESTIONS_BY_ID[QUESTION["id"]] = QUESTION


def test_shuffle_and_grading():
    """Перемешивание не ломает подсчёт: верный ответ верен, неверный неверен."""
    bot = _load_bot()
    with tempfile.TemporaryDirectory() as d:
        _prepare(bot, d)
        fb = FakeBot()
        positions = set()
        for _ in range(40):
            bot.ACTIVE_POLLS.clear()
            asyncio.run(bot.send_quiz(fb, 555, 555, QUESTION, mode="train"))
            kw = fb.sent[-1]
            poll_id = f"poll-{len(fb.sent)}"
            correct_id = kw["correct_option_id"]
            positions.add(correct_id)
            # вариант, на который указывает correct_option_id, — тот же текст,
            # что в банке помечен как правильный
            check_text = kw["options"][correct_id] == QUESTION["options"][QUESTION["answer"]]
            if not check_text:
                check("перемешивание: correct_option_id указывает на правильный текст", False)
                return
            # ответ по correct_option_id засчитывается как верный
            asyncio.run(bot.on_poll_answer(FakePollAnswer(poll_id, 555, [correct_id])))
            prog = bot.load_progress(555)
            if QUESTION["id"] in prog.get("wrong", []):
                check("перемешивание: верный ответ засчитан как верный", False)
                return
            # а любой другой — как ошибка
            wrong_id = (correct_id + 1) % len(kw["options"])
            bot.ACTIVE_POLLS.clear()
            asyncio.run(bot.send_quiz(fb, 556, 556, QUESTION, mode="train"))
            kw2 = fb.sent[-1]
            poll_id2 = f"poll-{len(fb.sent)}"
            wrong_id = (kw2["correct_option_id"] + 1) % len(kw2["options"])
            asyncio.run(bot.on_poll_answer(FakePollAnswer(poll_id2, 556, [wrong_id])))
            if QUESTION["id"] not in bot.load_progress(556).get("wrong", []):
                check("перемешивание: неверный ответ засчитан как ошибка", False)
                return

        check("перемешивание: correct_option_id всегда указывает на правильный текст", True)
        check("перемешивание: верный ответ засчитан как верный", True)
        check("перемешивание: неверный ответ засчитан как ошибка", True)
        # 40 отправок вопроса с 4 вариантами: позиция правильного обязана
        # гулять — иначе позиционный биас банка так и торчит наружу
        check(f"перемешивание: правильный побывал на разных позициях ({sorted(positions)})",
              len(positions) >= 3)


def test_legacy_poll_without_ans():
    """Записи опросов до волны A (без "ans") считаются по значению из банка."""
    bot = _load_bot()
    with tempfile.TemporaryDirectory() as d:
        _prepare(bot, d)
        import time as _t
        bot.ACTIVE_POLLS["old-poll"] = {
            "user_id": 777, "qid": QUESTION["id"], "mode": "train",
            "exam": False, "ts": int(_t.time()),
        }   # ключа "ans" нет — как в сессиях, сохранённых до обновления
        asyncio.run(bot.on_poll_answer(FakePollAnswer("old-poll", 777, [QUESTION["answer"]])))
        prog = bot.load_progress(777)
        check("старая запись опроса (без ans): ответ по банку засчитан верно",
              QUESTION["id"] not in prog.get("wrong", []) and prog["stats"]["correct"] == 1)


def test_foreign_voter_ignored():
    """Голос чужого человека в пересланном опросе не трогает прогресс автора."""
    bot = _load_bot()
    with tempfile.TemporaryDirectory() as d:
        _prepare(bot, d)
        fb = FakeBot()
        asyncio.run(bot.send_quiz(fb, 111, 111, QUESTION, mode="train"))
        poll_id = "poll-1"
        correct_id = fb.sent[-1]["correct_option_id"]
        asyncio.run(bot.on_poll_answer(FakePollAnswer(poll_id, 999, [correct_id])))
        owner = bot.load_progress(111)
        check("чужой голос не пишется в прогресс владельца",
              owner.get("stats", {}).get("answered", 0) == 0)
        check("чужой голос не пишется в свой прогресс",
              bot.load_progress(999).get("stats", {}).get("answered", 0) == 0)
        check("чужой голос не снимает привязку опроса (владелец ещё ответит)",
              poll_id in bot.ACTIVE_POLLS)
        # владелец отвечает после чужака — его ответ по-прежнему принимается
        asyncio.run(bot.on_poll_answer(FakePollAnswer(poll_id, 111, [correct_id])))
        check("ответ владельца после чужого голоса принят",
              bot.load_progress(111).get("stats", {}).get("answered", 0) == 1)


def test_stale_exam_poll_does_not_advance_new_exam():
    """Ответ на опрос брошенного экзамена не двигает новый экзамен."""
    bot = _load_bot()
    with tempfile.TemporaryDirectory() as d:
        _prepare(bot, d)
        import time as _t
        uid = 222
        # экзамен №1: отправлен вопрос, пользователь ушёл, не ответив
        bot.EXAMS[uid] = {"queue": [QUESTION["id"]], "idx": 0, "correct": 0,
                          "results": [], "ts": int(_t.time()), "sid": "exam-1"}
        fb = FakeBot()
        asyncio.run(bot.send_quiz(fb, uid, uid, QUESTION, mode="exam", is_exam=True))
        stale_poll = "poll-1"
        stale_correct = fb.sent[-1]["correct_option_id"]
        check("опрос экзамена помечен идентификатором попытки",
              bot.ACTIVE_POLLS[stale_poll].get("sid") == "exam-1")

        # экзамен №2 стартовал (привязки прошлого экзамена снимаются)
        bot.EXAMS[uid] = {"queue": [QUESTION["id"], QUESTION["id"]], "idx": 0,
                          "correct": 0, "results": [], "ts": int(_t.time()), "sid": "exam-2"}
        # эмулируем «опрос пережил старт» (например, restore из файла сессий)
        bot.ACTIVE_POLLS[stale_poll] = {
            "user_id": uid, "qid": QUESTION["id"], "mode": "exam", "exam": True,
            "ts": int(_t.time()), "ans": stale_correct, "sid": "exam-1",
        }
        asyncio.run(bot.on_poll_answer(FakePollAnswer(stale_poll, uid, [stale_correct])))
        ex = bot.EXAMS[uid]
        check("ответ старого экзамена не сдвинул idx нового", ex["idx"] == 0)
        check("ответ старого экзамена не добавил очко новому", ex["correct"] == 0)
        check("ответ старого экзамена не попал в results нового", ex["results"] == [])


class FakeChat:
    def __init__(self, cid):
        self.id = cid


class FakeCbMessage:
    def __init__(self, cid):
        self.chat = FakeChat(cid)

    async def answer(self, *a, **kw):
        return None


class FakeCallback:
    """Минимальный CallbackQuery для вызова настоящего обработчика."""

    def __init__(self, uid, fake_bot):
        self.from_user = FakeUser(uid)
        self.message = FakeCbMessage(uid)
        self.bot = fake_bot

    async def answer(self, *a, **kw):
        return None


def test_exam_start_clears_previous_polls():
    """Старт экзамена снимает привязки опросов прошлой попытки.

    Вызываем НАСТОЯЩИЙ обработчик cb_exam_start, а не копию его логики.
    """
    bot = _load_bot()
    with tempfile.TemporaryDirectory() as d:
        _prepare(bot, d)
        import time as _t
        uid = 333
        bot.ACTIVE_POLLS["old"] = {"user_id": uid, "qid": QUESTION["id"], "mode": "exam",
                                   "exam": True, "ts": int(_t.time()), "sid": "exam-old"}
        bot.ACTIVE_POLLS["train"] = {"user_id": uid, "qid": QUESTION["id"], "mode": "train",
                                     "exam": False, "ts": int(_t.time())}
        bot.ACTIVE_POLLS["other-user"] = {"user_id": 444, "qid": QUESTION["id"], "mode": "exam",
                                          "exam": True, "ts": int(_t.time()), "sid": "x"}
        fb = FakeBot()
        asyncio.run(bot.cb_exam_start(FakeCallback(uid, fb)))
        check("снят опрос прошлого экзамена", "old" not in bot.ACTIVE_POLLS)
        check("тренировочный опрос не тронут", "train" in bot.ACTIVE_POLLS)
        check("опрос другого пользователя не тронут", "other-user" in bot.ACTIVE_POLLS)
        check("новый экзамен получил свой идентификатор попытки",
              bool(bot.EXAMS.get(uid, {}).get("sid")))
        # первый вопрос нового экзамена отправлен и помечен этим же sid
        sent_polls = [i for i in bot.ACTIVE_POLLS.values()
                      if i.get("exam") and i.get("user_id") == uid]
        check("опрос нового экзамена привязан к новой попытке",
              len(sent_polls) == 1 and sent_polls[0].get("sid") == bot.EXAMS[uid]["sid"])


if __name__ == "__main__":
    print("QUIZ-POLL TESTS")
    test_shuffle_and_grading()
    test_legacy_poll_without_ans()
    test_foreign_voter_ignored()
    test_stale_exam_poll_does_not_advance_new_exam()
    test_exam_start_clears_previous_polls()
    print()
    if fails:
        print(f"QUIZ-POLL TESTS: {fails} провал(ов)")
        sys.exit(1)
    print("QUIZ-POLL TESTS OK")
