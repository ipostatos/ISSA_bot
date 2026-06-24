"""
Тесты калькулятора TVMDC (calc.solve) и парсера ввода из bot.py.

Запуск:  python test_calc.py
Использует только стандартную библиотеку (bot.py грузим как модуль —
для теста парсера это не требует подключения к Telegram).
"""

import importlib.util
import sys
from pathlib import Path

import calc
import nav_tasks as nt

BASE = Path(__file__).parent


def _load_bot():
    spec = importlib.util.spec_from_file_location("bot", BASE / "bot.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_reference_cases():
    cases = [
        # (src, dst, course, var, vdir, dev, ddir, expected)
        ("T", "M", 100, 6, "E", 0, "E", 94),
        ("T", "M", 80, 5, "W", 0, "E", 85),
        ("M", "C", 120, 0, "E", 4, "E", 116),
        ("M", "C", 120, 0, "E", 4, "W", 124),
        ("M", "C", 200, 0, "E", 3, "W", 203),
        ("T", "C", 45, 3, "W", 2, "E", 46),
        ("C", "T", 46, 3, "W", 2, "E", 45),
        # переход через 360°
        ("T", "C", 357, 6, "W", 3, "W", 6),
        ("T", "C", 3, 5, "E", 4, "E", 354),
        ("M", "C", 359, 0, "E", 4, "W", 3),
    ]
    for src, dst, c, v, vd, d, dd, exp in cases:
        got = calc.solve(src, dst, c, v, vd, d, dd)["answer"]
        assert nt.angle_diff(got, exp) == 0, f"{src}->{dst} {c}: got {got}, want {exp}"


def test_round_trip():
    """Вниз и обратно вверх должно вернуть исходный курс для всех углов."""
    for T in range(0, 360, 3):
        for v, vd, d, dd in [(6, "E", 3, "W"), (5, "W", 4, "E"), (10, "E", 7, "E")]:
            c = calc.solve("T", "C", T, v, vd, d, dd)["answer"]
            back = calc.solve("C", "T", c, v, vd, d, dd)["answer"]
            assert nt.angle_diff(back, T) <= 1, f"round-trip {T}: back {back}"


def test_matches_nav_tasks():
    """calc.solve должен совпадать с проверенной арифметикой nav_tasks."""
    for T in range(0, 360, 7):
        for v, vd, d, dd in [(6, "E", 3, "W"), (5, "W", 4, "E"),
                             (8, "W", 2, "W"), (3, "E", 6, "E")]:
            a = calc.solve("T", "C", T, v, vd, d, dd)["answer"]
            b = round(nt.true_to_compass(T, v, vd, d, dd))
            assert nt.angle_diff(a, b) == 0, f"{T}: calc {a} vs nav {b}"


def test_bad_direction():
    for bad in [("T", "T"), ("X", "C")]:
        try:
            calc.solve(bad[0], bad[1], 100, 0, "E", 0, "E")
            assert False, f"должно было упасть на {bad}"
        except ValueError:
            pass


def test_parser():
    bot = _load_bot()
    p = bot._parse_calc_input

    # T↔C: нужны и var, и dev
    r = p("045 3W 2E", True, True)
    assert r and r["course"] == 45 and r["var"] == 3 and r["var_dir"] == "W" \
        and r["dev"] == 2 and r["dev_dir"] == "E"

    # русские буквы направления
    r = p("45 3з 2в", True, True)
    assert r and r["var_dir"] == "W" and r["dev_dir"] == "E"

    # дробное и запятая как разделитель
    r = p("120,5 4w", False, True)
    assert r and abs(r["course"] - 120.5) < 1e-9 and r["dev_dir"] == "W"

    # ошибки: нет буквы направления / не хватает чисел / мусор
    assert p("100 6", True, False) is None
    assert p("100", False, True) is None
    assert p("abc", True, True) is None
    assert p("", True, True) is None


def test_format_no_crash():
    bot = _load_bot()
    res = calc.solve("T", "C", 45, 3, "W", 2, "E")
    out = bot._format_calc_result(res)
    assert "046" in out and "True" in out and "Compass" in out


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
    msg = f"OK: calc tests passed ({len(tests)} групп)"
    sys.stdout.buffer.write((msg + "\n").encode(sys.stdout.encoding or "utf-8", "replace"))


if __name__ == "__main__":
    main()
