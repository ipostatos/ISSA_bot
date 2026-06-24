"""
TVMDC-калькулятор: универсальный пересчёт курсов True ↔ Magnetic ↔ Compass
с поправками Variation и Deviation.

Вся арифметика берётся из nav_tasks (один источник правды — там же она
покрыта тестами). Здесь только «обёртка»: по выбранному направлению считаем
ответ и собираем пошаговое решение.

Цепочка:  True ←(Variation)→ Magnetic ←(Deviation)→ Compass
Правило знаков (вниз, True→Compass): East −, West +. Вверх — наоборот.

solve() возвращает dict, пригодный и для текста в боте, и для JSON в Mini App.
"""

from dataclasses import dataclass

from nav_tasks import (
    norm360,
    true_to_magnetic,
    magnetic_to_compass,
    compass_to_magnetic,
    magnetic_to_true,
)

# Что известно / что ищем. Любая пара (from → to) из трёх точек цепочки.
POINTS = ("T", "M", "C")  # True, Magnetic, Compass
POINT_NAME = {"T": "True", "M": "Magnetic", "C": "Compass"}


def _norm_dir(d: str) -> str:
    """Нормализовать направление поправки к 'E' или 'W'."""
    d = (d or "").strip().upper()
    if d in ("E", "EAST", "В", "ВОСТ", "О"):
        return "E"
    if d in ("W", "WEST", "З", "ЗАП"):
        return "W"
    raise ValueError(f"Направление должно быть E или W, получено: {d!r}")


@dataclass
class Step:
    text: str          # «True→Magnetic: 100 − 6 = 94»
    label: str         # «True→Magnetic»
    expr: str          # «100 − 6»
    result: float      # 94


def solve(src: str, dst: str, course: float,
          var: float, var_dir: str, dev: float, dev_dir: str) -> dict:
    """
    Пересчитать курс из точки src в точку dst.

    src, dst ∈ {'T','M','C'} (True/Magnetic/Compass), src != dst.
    course — известный курс в точке src (любое число, нормализуется).
    var/var_dir — Variation и её направление (E/W); dev/dev_dir — Deviation.

    Возвращает: {answer, steps:[{label,expr,result,text}], from, to,
                 direction: 'down'|'up'}.
    """
    if src not in POINTS or dst not in POINTS:
        raise ValueError("src/dst должны быть T, M или C")
    if src == dst:
        raise ValueError("src и dst должны различаться")

    vd = _norm_dir(var_dir)
    dd = _norm_dir(dev_dir)
    var = abs(float(var))
    dev = abs(float(dev))
    cur = norm360(float(course))

    i, j = POINTS.index(src), POINTS.index(dst)
    going_down = j > i  # True→Magnetic→Compass — «вниз» по цепочке
    direction = "down" if going_down else "up"

    # Последовательность переходов между соседними точками.
    order = list(range(i, j, 1)) if going_down else list(range(i, j, -1))

    steps: list[Step] = []
    for k in order:
        a, b = POINTS[k], POINTS[k + 1] if going_down else POINTS[k - 1]
        if going_down:
            seg = (a, b)
        else:
            seg = (a, b)
        steps.append(_apply(seg, cur, var, vd, dev, dd, going_down))
        cur = steps[-1].result

    return {
        "answer": round(cur),
        "from": POINT_NAME[src],
        "to": POINT_NAME[dst],
        "direction": direction,
        "steps": [{"label": s.label, "expr": s.expr,
                   "result": round(s.result), "text": s.text} for s in steps],
    }


def _apply(seg, cur, var, vd, dev, dd, going_down) -> Step:
    """Один переход между соседними точками цепочки."""
    a, b = seg
    # Какая поправка участвует: T↔M это Variation, M↔C это Deviation.
    if {a, b} == {"T", "M"}:
        val, vdir = var, vd
        if going_down:
            res = true_to_magnetic(cur, val, vdir)
        else:
            res = magnetic_to_true(cur, val, vdir)
    else:  # {"M","C"}
        val, vdir = dev, dd
        if going_down:
            res = magnetic_to_compass(cur, val, vdir)
        else:
            res = compass_to_magnetic(cur, val, vdir)

    # Знак в формуле для показа: вниз East −/West +, вверх наоборот.
    if going_down:
        sign = "−" if vdir == "E" else "+"
    else:
        sign = "+" if vdir == "E" else "−"

    label = f"{POINT_NAME[a]}→{POINT_NAME[b]}"
    expr = f"{cur:.0f} {sign} {val:.0f}{vdir}"
    return Step(text=f"{label}: {expr} = {res:.0f}", label=label, expr=expr, result=res)


def rule_hint(direction: str) -> str:
    if direction == "down":
        return "Правило (вниз, True→Compass): East вычитаем (−), West прибавляем (+)."
    return "Правило (вверх, Compass→True): East прибавляем (+), West вычитаем (−)."
