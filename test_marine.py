"""
Тесты морских расчётов (marine.py): S-D-T, ETA, практические задачи.

Запуск:  python test_marine.py
"""

import sys

import marine as m


def almost(a, b, eps=1e-6):
    return abs(a - b) <= eps


def test_sdt():
    assert almost(m.time_from(13.2, 5.5), 2.4)        # 13.2/5.5
    assert almost(m.distance_from(6, 2.5), 15.0)
    assert almost(m.speed_from(15, 3), 5.0)
    # деления на ноль
    for bad in (lambda: m.time_from(10, 0), lambda: m.speed_from(10, 0)):
        try:
            bad(); assert False
        except ValueError:
            pass


def test_hm():
    assert m.hours_to_hm(0.5) == "0 ч 30 мин"
    assert m.hours_to_hm(2.25) == "2 ч 15 мин"
    assert m.hours_to_hm(0) == "0 ч 00 мин"


def test_eta_clock():
    assert m.eta_clock("09:00", 2.5) == "11:30"
    assert m.eta_clock("22:30", 2.0) == "00:30"      # через полночь
    assert m.eta_clock("0700", 1.5) == "08:30"       # формат без двоеточия
    assert m.eta_clock("23:45", 1.0) == "00:45"
    try:
        m.eta_clock("25:00", 1); assert False
    except ValueError:
        pass


def test_plan_eta():
    r = m.plan_eta(18, 5, 20, "09:00")
    assert almost(r.travel_h, 3.6)                   # 18/5
    assert almost(r.travel_h_reserve, 4.32)          # ×1.2
    assert r.eta == "13:19"                          # 09:00 + 4ч19м (259 мин)
    r2 = m.plan_eta(10, 5)                            # без запаса и без старта
    assert almost(r2.travel_h_reserve, 2.0) and r2.eta is None


def test_tasks_consistent():
    # каждый эталонный ответ задачи проходит её же check()
    for t in m.TASKS:
        assert t.check(str(t.answer)), f"{t.id}: own answer fails check"
        # за пределами допуска — не принимает
        assert not t.check(str(t.answer + t.tol + 1.0)), f"{t.id}: tol too wide"
    # уникальные id
    assert len(m.TASKS_BY_ID) == len(m.TASKS)


def test_check_parsing():
    t = m.task_time("x", 5.5, 13.2)   # ответ 2.4 ч
    assert t.check("2.4") and t.check("2,4") and t.check("2.4 ч")
    assert t.check("2.38") and t.check("2.45")   # в пределах ±0.05
    assert not t.check("3") and not t.check("abc")


def test_num_format():
    assert m._num(5.0) == "5"
    assert m._num(5.5) == "5,5"
    assert m._num(13.2) == "13,2"


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
    msg = f"OK: marine tests passed ({len(tests)} групп)"
    sys.stdout.buffer.write((msg + "\n").encode(sys.stdout.encoding or "utf-8", "replace"))


if __name__ == "__main__":
    main()
