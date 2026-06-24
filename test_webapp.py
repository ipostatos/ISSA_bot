"""
Тесты разбора результата из Mini App «Тесты» (bot.parse_webapp_quiz).

Запуск:  python test_webapp.py
"""

import importlib.util
import sys
from pathlib import Path

BASE = Path(__file__).parent


def _load_bot():
    spec = importlib.util.spec_from_file_location("bot", BASE / "bot.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    bot = _load_bot()
    p = bot.parse_webapp_quiz
    ids = list(bot.QUESTIONS_BY_ID.keys())
    assert len(ids) >= 5, "нужен непустой банк"

    # нормальный экзамен
    res = [[ids[0], 1], [ids[1], 0], [ids[2], 1]]
    out = p({"t": "quiz", "mode": "exam", "results": res, "secs": 120})
    assert out and out["is_exam"] is True
    assert out["ok_ids"] == [ids[0], ids[2]]
    assert out["wrong_ids"] == [ids[1]]
    assert out["secs"] == 120

    # тренировка по теме
    out = p({"t": "quiz", "mode": "topic:Навигация", "results": [[ids[0], 1]]})
    assert out and out["is_exam"] is False and out["mode"] == "topic:Навигация"

    # неизвестные id отбрасываются, считаются только известные
    out = p({"t": "quiz", "mode": "random",
             "results": [["zzz-999", 1], [ids[0], 0]]})
    assert out and out["ok_ids"] == [] and out["wrong_ids"] == [ids[0]]

    # полностью неизвестные id -> None
    assert p({"t": "quiz", "mode": "exam", "results": [["zzz-1", 1]]}) is None

    # битые формы -> None
    assert p(None) is None
    assert p({"t": "other", "results": [[ids[0], 1]]}) is None
    assert p({"t": "quiz", "results": []}) is None
    assert p({"t": "quiz", "results": "nope"}) is None
    assert p({"t": "quiz"}) is None

    # кривые элементы внутри results пропускаются, но валидные учитываются
    out = p({"t": "quiz", "mode": "random",
             "results": [["x"], [ids[0], 1], 42, [ids[1], 0]]})
    assert out and out["ok_ids"] == [ids[0]] and out["wrong_ids"] == [ids[1]]

    # лимит на размер результата
    big = [[ids[0], 1]] * (bot.MAX_WEBAPP_RESULTS + 50)
    out = p({"t": "quiz", "mode": "exam", "results": big})
    assert len(out["ok_ids"]) == bot.MAX_WEBAPP_RESULTS

    # битый secs не валит
    out = p({"t": "quiz", "mode": "exam", "results": [[ids[0], 1]], "secs": "abc"})
    assert out and out["secs"] == 0

    msg = "OK: webapp tests passed"
    sys.stdout.buffer.write((msg + "\n").encode(sys.stdout.encoding or "utf-8", "replace"))


if __name__ == "__main__":
    main()
