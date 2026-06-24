"""
Приливы: правило двенадцатых (Rule of Twelfths).

Упрощённая модель приливного цикла: от малой воды (LW) до полной (HW) проходит
≈6 часов, и за эти часы вода прибывает долями диапазона:

    1/12, 2/12, 3/12, 3/12, 2/12, 1/12   (по часам 1..6)

Это стандартное учебное приближение (реальный полупериод ~6 ч 12 мин).
Здесь — расчёт высоты воды и генератор задач. Чистые функции (без I/O):
общий источник правды для бота, Mini App и тестов.
"""

from dataclasses import dataclass

TWELFTHS = (1, 2, 3, 3, 2, 1)  # доли диапазона по часам 1..6


def height_after_lw(hw: float, lw: float, hours_after_lw: float) -> float:
    """
    Высота воды через `hours_after_lw` часов после малой воды по правилу 12.

    hw — высота полной воды, lw — высота малой воды (hw может быть > или < lw,
    функция работает и на отлив: rng просто станет отрицательным).
    Часы зажимаются в диапазон 0..6.
    """
    rng = hw - lw
    h = max(0.0, min(6.0, float(hours_after_lw)))
    full = int(h)
    frac = h - full

    water = lw
    for i in range(full):
        water += rng * TWELFTHS[i] / 12
    if full < 6:
        water += rng * TWELFTHS[full] / 12 * frac
    return water


def twelfths_table(hw: float, lw: float) -> list[dict]:
    """Таблица по часам 1..6: доля, прирост за час и высота к концу часа."""
    rng = hw - lw
    rows = []
    for i, part in enumerate(TWELFTHS, start=1):
        rows.append({
            "hour": i,
            "twelfths": part,                       # сколько двенадцатых в этот час
            "rise": rng * part / 12,                # прирост за час
            "height": height_after_lw(hw, lw, i),   # высота к концу часа
        })
    return rows


# ──────────────────────── Задачи на приливы ────────────────────────

@dataclass
class TideTask:
    id: str
    text: str
    answer: float      # высота воды, м
    tol: float         # допуск, м
    solution: str

    def check(self, user: str) -> bool:
        try:
            val = float(str(user).strip().replace(",", ".").replace("м", "").strip())
        except ValueError:
            return False
        return abs(val - self.answer) <= self.tol + 1e-9


def _num(x: float) -> str:
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def make_tide_task(n: str, hw: float, lw: float, hours: int) -> TideTask:
    ans = height_after_lw(hw, lw, hours)
    rng = hw - lw
    # пошаговое решение: накапливаем двенадцатые до нужного часа
    parts = []
    acc = lw
    for i in range(hours):
        acc += rng * TWELFTHS[i] / 12
        parts.append(f"{i+1}ч: +{TWELFTHS[i]}/12 = {_num(rng*TWELFTHS[i]/12)} → {_num(acc)} м")
    sol = (f"Диапазон = HW − LW = {_num(hw)} − {_num(lw)} = {_num(rng)} м; "
           f"1/12 = {_num(rng/12)} м.\n" + "\n".join(parts))
    return TideTask(
        id=n,
        text=(f"Малая вода LW = {_num(lw)} м, полная HW = {_num(hw)} м. "
              f"Сколько воды через {hours} ч после малой воды? (по правилу 12, в метрах)"),
        answer=round(ans, 2), tol=0.05, solution=sol,
    )


# Воспроизводимый банк задач на приливы.
TASKS: list[TideTask] = [
    make_tide_task("td-01", 8, 2, 1),
    make_tide_task("td-02", 8, 2, 2),
    make_tide_task("td-03", 8, 2, 3),
    make_tide_task("td-04", 8, 2, 4),
    make_tide_task("td-05", 8, 2, 5),
    make_tide_task("td-06", 5.4, 1.2, 2),
    make_tide_task("td-07", 5.4, 1.2, 3),
    make_tide_task("td-08", 6, 0.5, 4),
    make_tide_task("td-09", 4.8, 0.8, 5),
    make_tide_task("td-10", 7.2, 1.0, 2),
]

TASKS_BY_ID = {t.id: t for t in TASKS}
