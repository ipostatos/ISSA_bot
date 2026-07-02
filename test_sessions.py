"""
Тесты персистентности чат-сессий (EXAMS / ACTIVE_POLLS переживают рестарт).

Проверяем: round-trip save→load, int-ключи user_id, TTL-очистку протухших,
устойчивость к битому файлу и что после «рестарта» отвеченный опрос не
теряет привязку. bot.py грузим как модуль (Telegram не требуется — трогаем
только функции хранения).

Запуск:  python test_sessions.py   (или pytest test_sessions.py)
"""

import importlib.util
import sys
import tempfile
import time
from pathlib import Path

BASE = Path(__file__).parent


def _load_bot():
    spec = importlib.util.spec_from_file_location("bot", BASE / "bot.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _isolate(bot, tmp: Path):
    """Направить файлы сессий во временный каталог (не трогать боевые)."""
    bot._EXAMS_FILE = tmp / "exams.json"
    bot._POLLS_FILE = tmp / "active_polls.json"
    bot.EXAMS.clear()
    bot.ACTIVE_POLLS.clear()


def test_exam_round_trip():
    bot = _load_bot()
    with tempfile.TemporaryDirectory() as d:
        _isolate(bot, Path(d))
        now = int(time.time())
        bot.EXAMS[123] = {"queue": ["q-1", "q-2"], "idx": 1, "correct": 1,
                          "results": [("q-1", True)], "ts": now}
        bot._save_exams()
        # «рестарт»: очищаем память и грузим с диска
        bot.EXAMS.clear()
        bot._load_sessions()
        assert 123 in bot.EXAMS, "экзамен не восстановился"
        ex = bot.EXAMS[123]
        assert ex["idx"] == 1 and ex["correct"] == 1
        assert ex["queue"] == ["q-1", "q-2"]
        # user_id-ключ должен снова быть int, а не строкой из JSON
        assert all(isinstance(k, int) for k in bot.EXAMS), "ключ user_id не int"


def test_poll_round_trip_and_answer_binding():
    bot = _load_bot()
    with tempfile.TemporaryDirectory() as d:
        _isolate(bot, Path(d))
        bot.ACTIVE_POLLS["poll-abc"] = {
            "user_id": 55, "qid": "q-7", "mode": "exam", "exam": True,
            "ts": int(time.time()),
        }
        bot._save_polls()
        # «рестарт»: привязка опроса должна пережить перезапуск
        bot.ACTIVE_POLLS.clear()
        bot._load_sessions()
        assert "poll-abc" in bot.ACTIVE_POLLS, "привязка опроса потеряна при рестарте"
        info = bot.ACTIVE_POLLS["poll-abc"]
        assert info["user_id"] == 55 and info["qid"] == "q-7" and info["exam"] is True


def test_ttl_prunes_stale():
    bot = _load_bot()
    with tempfile.TemporaryDirectory() as d:
        _isolate(bot, Path(d))
        old = int(time.time()) - bot._SESSION_TTL_SEC - 10   # старше TTL
        fresh = int(time.time())
        bot.EXAMS[1] = {"queue": ["a"], "idx": 0, "correct": 0, "results": [], "ts": old}
        bot.EXAMS[2] = {"queue": ["b"], "idx": 0, "correct": 0, "results": [], "ts": fresh}
        bot.ACTIVE_POLLS["stale"] = {"user_id": 1, "qid": "a", "mode": "exam", "exam": True, "ts": old}
        bot.ACTIVE_POLLS["live"] = {"user_id": 2, "qid": "b", "mode": "exam", "exam": True, "ts": fresh}
        bot._save_exams()
        bot._save_polls()
        bot.EXAMS.clear()
        bot.ACTIVE_POLLS.clear()
        bot._load_sessions()
        assert 1 not in bot.EXAMS and 2 in bot.EXAMS, "TTL не отсеял старый экзамен"
        assert "stale" not in bot.ACTIVE_POLLS and "live" in bot.ACTIVE_POLLS, "TTL не отсеял старый опрос"


def test_corrupt_file_does_not_crash():
    bot = _load_bot()
    with tempfile.TemporaryDirectory() as d:
        _isolate(bot, Path(d))
        bot._EXAMS_FILE.write_text("{ это не JSON", encoding="utf-8")
        bot._POLLS_FILE.write_text("тоже мусор ]", encoding="utf-8")
        # не должно бросать — просто стартуем с пустого стора
        bot._load_sessions()
        assert bot.EXAMS == {} and bot.ACTIVE_POLLS == {}


def test_missing_files_ok():
    bot = _load_bot()
    with tempfile.TemporaryDirectory() as d:
        _isolate(bot, Path(d))
        # файлов нет вообще — тоже нормально
        bot._load_sessions()
        assert bot.EXAMS == {} and bot.ACTIVE_POLLS == {}


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
    msg = f"OK: session persistence tests passed ({len(tests)} групп)"
    sys.stdout.buffer.write((msg + "\n").encode(sys.stdout.encoding or "utf-8", "replace"))


if __name__ == "__main__":
    main()
