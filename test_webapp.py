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


def _test_batch_equiv(bot, ids):
    """record_results_batch == поштучный record_answer()+mark_seen().

    Гарантирует, что пакетная запись результатов теста (без I/O-флуда) даёт
    тот же прогресс, что старая поштучная логика. Ловит регрессию, если кто-то
    изменит одну ветку, забыв про другую.
    """
    import tempfile
    from pathlib import Path

    assert len(ids) >= 30, "нужно больше вопросов для теста эквивалентности"
    bot.PROGRESS_DIR = Path(tempfile.mkdtemp())

    def per_item(uid, ok, wrong):
        for qid in ok:
            bot.record_answer(uid, qid, True)
            bot.mark_seen(uid, qid)
        for qid in wrong:
            bot.record_answer(uid, qid, False)
            bot.mark_seen(uid, qid)

    scenarios = [
        ("экзамен", ids[:20], ids[20:30]),
        ("все верные", ids[:15], []),
        ("все ошибки", [], ids[:15]),
        ("повтор id", ids[:5] + ids[:5], ids[5:8]),
        ("мусорные id", ids[:8] + ["zzz-9", "FAKE"], ids[8:12] + ["bad"]),
        ("пересечение ok/wrong", ids[:10], ids[5:15]),
    ]
    for name, ok, wrong in scenarios:
        # поверх непустого прогресса — проверяем накопление и исправление ошибок
        seed_ok, seed_wrong = ids[25:28], ids[28:31] if len(ids) >= 31 else []
        for u in ("A", "B"):
            p = bot._progress_path(u)
            if p.exists():
                p.unlink()
        per_item("A", seed_ok, seed_wrong)
        per_item("A", ok, wrong)
        bot.record_results_batch("B", seed_ok, seed_wrong)
        bot.record_results_batch("B", ok, wrong)
        a, b = bot.load_progress("A"), bot.load_progress("B")
        assert a["stats"] == b["stats"], f"{name}: stats {a['stats']} != {b['stats']}"
        assert set(a["seen"]) == set(b["seen"]), f"{name}: seen расходится"
        assert set(a["wrong"]) == set(b["wrong"]), f"{name}: wrong расходится"


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

    _test_batch_equiv(bot, ids)

    msg = "OK: webapp tests passed"
    sys.stdout.buffer.write((msg + "\n").encode(sys.stdout.encoding or "utf-8", "replace"))


if __name__ == "__main__":
    main()
