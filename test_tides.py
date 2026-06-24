"""Тесты правила двенадцатых (tides.py). Запуск: python test_tides.py"""

import sys
import tides as t


def almost(a, b, eps=1e-9):
    return abs(a - b) <= eps


def test_blackboard_example():
    # Пример с доски: HW=8, LW=2 → 2.5, 3.5, 5.0, 6.5, 7.5, 8.0
    expected = {1: 2.5, 2: 3.5, 3: 5.0, 4: 6.5, 5: 7.5, 6: 8.0}
    for h, exp in expected.items():
        assert almost(t.height_after_lw(8, 2, h), exp), (h, t.height_after_lw(8, 2, h))


def test_bounds():
    assert almost(t.height_after_lw(8, 2, 0), 2.0)     # в LW
    assert almost(t.height_after_lw(8, 2, 6), 8.0)     # в HW
    assert almost(t.height_after_lw(8, 2, 10), 8.0)    # зажим до 6ч
    assert almost(t.height_after_lw(8, 2, -3), 2.0)    # зажим до 0


def test_fraction():
    # 3.5 ч: после 3ч = 5.0, плюс половина 4-го часа (3/12 от 6 = 1.5 → /2 = 0.75)
    assert almost(t.height_after_lw(8, 2, 3.5), 5.75)


def test_ebb():
    # отлив: HW=2, LW=8 (range отрицательный) — симметрично
    assert almost(t.height_after_lw(2, 8, 1), 7.5)
    assert almost(t.height_after_lw(2, 8, 6), 2.0)


def test_table():
    rows = t.twelfths_table(8, 2)
    assert len(rows) == 6
    assert [r["twelfths"] for r in rows] == [1, 2, 3, 3, 2, 1]
    assert almost(rows[2]["height"], 5.0)              # к концу 3-го часа
    assert almost(sum(r["rise"] for r in rows), 6.0)   # суммарный прирост = range


def test_tasks():
    for task in t.TASKS:
        assert task.check(str(task.answer)), f"{task.id} own answer fails"
        assert not task.check(str(task.answer + 1.0)), f"{task.id} tol too wide"
    assert len(t.TASKS_BY_ID) == len(t.TASKS)
    # сверим td-03 (8/2, 3ч) = 5.0
    assert almost(t.TASKS_BY_ID["td-03"].answer, 5.0)


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for fn in tests:
        fn()
    msg = f"OK: tides tests passed ({len(tests)} групп)"
    sys.stdout.buffer.write((msg + "\n").encode(sys.stdout.encoding or "utf-8", "replace"))


if __name__ == "__main__":
    main()
