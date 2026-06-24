"""
Решение задач T-V-M-D-C (поправки компаса) для тренажёра ISSA Inshore Skipper.

Цепочка:  True ←→ (Variation) ←→ Magnetic ←→ (Deviation) ←→ Compass

Правило знаков (вниз по цепочке, от True к Compass):
    East — вычитаем (−),  West — прибавляем (+).
Вверх по цепочке (от Compass к True) — наоборот.
Мнемоника: «East is least, West is best» (для перехода Compass→True
восточные прибавляем; здесь функции сами считают в нужную сторону).

Здесь 50 задач (TASKS): обычные + со звёздочкой (с подвохом — переход
через 360°, отрицательные значения, «тихие» вычисления). Задачи можно
повторять — цель научиться решать. Можно догенерировать ещё (gen_random),
но фиксированный список делает прогресс воспроизводимым.
"""

from dataclasses import dataclass


def norm360(x: float) -> float:
    """Привести курс к диапазону 0..359 (включая переход через 360°)."""
    return x % 360


def angle_diff(a: float, b: float) -> float:
    """Кратчайшая разница углов по кругу (учитывает границу 0°/360°)."""
    d = abs(norm360(a) - norm360(b))
    return min(d, 360 - d)


# ──────────────── Базовые преобразования ────────────────
# Вниз (True→Compass): East −, West +.

def true_to_magnetic(true: float, var: float, var_dir: str) -> float:
    sign = -1 if var_dir.upper() in ("E", "EAST", "В", "ВОСТ") else +1
    return norm360(true + sign * var)


def magnetic_to_compass(mag: float, dev: float, dev_dir: str) -> float:
    sign = -1 if dev_dir.upper() in ("E", "EAST", "В", "ВОСТ") else +1
    return norm360(mag + sign * dev)


def true_to_compass(true: float, var: float, var_dir: str, dev: float, dev_dir: str) -> float:
    return magnetic_to_compass(true_to_magnetic(true, var, var_dir), dev, dev_dir)


# Вверх (Compass→True): East +, West −.

def compass_to_magnetic(compass: float, dev: float, dev_dir: str) -> float:
    sign = +1 if dev_dir.upper() in ("E", "EAST", "В", "ВОСТ") else -1
    return norm360(compass + sign * dev)


def magnetic_to_true(mag: float, var: float, var_dir: str) -> float:
    sign = +1 if var_dir.upper() in ("E", "EAST", "В", "ВОСТ") else -1
    return norm360(mag + sign * var)


def compass_to_true(compass: float, dev: float, dev_dir: str, var: float, var_dir: str) -> float:
    return magnetic_to_true(compass_to_magnetic(compass, dev, dev_dir), var, var_dir)


# ──────────────── Модель задачи ────────────────

@dataclass
class NavTask:
    id: str
    text: str           # условие
    answer: float       # правильный ответ (курс 0..359)
    solution: str       # пошаговое решение
    starred: bool = False  # «со звёздочкой» (с подвохом)

    def check(self, user: str) -> bool:
        """Проверка ответа пользователя (допуск ±1° на округление)."""
        try:
            val = float(str(user).strip().replace("°", "").replace(",", "."))
        except ValueError:
            return False
        return angle_diff(val, self.answer) <= 1.0


# ──────────────── 50 задач ────────────────
# Формат helper'ов делает условие и решение единообразными.

def _t2c(n, T, V, Vd, D, Dd, star=False):
    ans = true_to_compass(T, V, Vd, D, Dd)
    M = true_to_magnetic(T, V, Vd)
    vs = "−" if Vd == "E" else "+"
    ds = "−" if Dd == "E" else "+"
    sol = (f"True→Magnetic: {T} {vs} {V} = {M:.0f}\n"
           f"Magnetic→Compass: {M:.0f} {ds} {D} = {ans:.0f}\n"
           f"Правило (вниз): East −, West +.")
    txt = f"True {T}°, Variation {V}°{Vd}, Deviation {D}°{Dd}. Найти Compass course (CC)."
    return NavTask(n, txt, ans, sol, star)


def _t2m(n, T, V, Vd, star=False):
    ans = true_to_magnetic(T, V, Vd)
    vs = "−" if Vd == "E" else "+"
    sol = f"True→Magnetic: {T} {vs} {V} = {ans:.0f}\nEast вычитаем, West прибавляем."
    return NavTask(n, f"True course {T}°, Variation {V}°{Vd}. Найти Magnetic course (MC).", ans, sol, star)


def _m2c(n, M, D, Dd, star=False):
    ans = magnetic_to_compass(M, D, Dd)
    ds = "−" if Dd == "E" else "+"
    sol = f"Magnetic→Compass: {M} {ds} {D} = {ans:.0f}\nEast вычитаем, West прибавляем."
    return NavTask(n, f"Magnetic course {M}°, Deviation {D}°{Dd}. Найти Compass course (CC).", ans, sol, star)


def _c2t(n, C, D, Dd, V, Vd, star=False):
    ans = compass_to_true(C, D, Dd, V, Vd)
    M = compass_to_magnetic(C, D, Dd)
    ds = "+" if Dd == "E" else "−"
    vs = "+" if Vd == "E" else "−"
    sol = (f"Compass→Magnetic: {C} {ds} {D} = {M:.0f}\n"
           f"Magnetic→True: {M:.0f} {vs} {V} = {ans:.0f}\n"
           f"Правило (вверх): East +, West −.")
    return NavTask(n, f"Compass {C}°, Deviation {D}°{Dd}, Variation {V}°{Vd}. Найти True course (TC).", ans, sol, star)


def _c2m(n, C, D, Dd, star=False):
    ans = compass_to_magnetic(C, D, Dd)
    ds = "+" if Dd == "E" else "−"
    sol = f"Compass→Magnetic: {C} {ds} {D} = {ans:.0f}\n(вверх) East прибавляем, West вычитаем."
    return NavTask(n, f"Compass course {C}°, Deviation {D}°{Dd}. Найти Magnetic course (MC).", ans, sol, star)


TASKS: list[NavTask] = [
    # ── Базовые True→Magnetic ──
    _t2m("nt-01", 100, 6, "E"),
    _t2m("nt-02", 80, 5, "W"),
    _t2m("nt-03", 215, 4, "E"),
    _t2m("nt-04", 45, 8, "W"),
    _t2m("nt-05", 270, 10, "E"),
    # ── Magnetic→Compass ──
    _m2c("nt-06", 120, 4, "E"),
    _m2c("nt-07", 200, 3, "W"),
    _m2c("nt-08", 330, 6, "E"),
    _m2c("nt-09", 15, 5, "W"),
    _m2c("nt-10", 178, 2, "E"),
    # ── Полная цепочка True→Compass ──
    _t2c("nt-11", 45, 3, "W", 2, "E"),
    _t2c("nt-12", 100, 6, "E", 4, "E"),
    _t2c("nt-13", 200, 5, "W", 3, "W"),
    _t2c("nt-14", 135, 4, "E", 2, "W"),
    _t2c("nt-15", 80, 5, "W", 3, "E"),
    _t2c("nt-16", 250, 7, "E", 4, "W"),
    _t2c("nt-17", 310, 6, "W", 3, "E"),
    _t2c("nt-18", 20, 4, "E", 5, "W"),
    _t2c("nt-19", 160, 8, "W", 2, "E"),
    _t2c("nt-20", 290, 3, "E", 6, "E"),
    # ── Обратная цепочка Compass→True ──
    _c2t("nt-21", 180, 5, "W", 2, "E"),
    _c2t("nt-22", 46, 2, "E", 3, "W"),
    _c2t("nt-23", 225, 2, "W", 6, "E"),
    _c2t("nt-24", 315, 5, "E", 4, "W"),
    _c2t("nt-25", 90, 4, "W", 5, "E"),
    _c2m("nt-26", 95, 5, "E"),
    _c2m("nt-27", 180, 5, "W"),
    _c2m("nt-28", 200, 3, "E"),
    _c2m("nt-29", 350, 4, "W"),
    _c2m("nt-30", 10, 7, "E"),
    # ── Ещё полная цепочка (закрепление) ──
    _t2c("nt-31", 45, 4, "W", 3, "E"),
    _t2c("nt-32", 123, 6, "E", 2, "E"),
    _t2c("nt-33", 270, 7, "W", 3, "E"),
    _t2c("nt-34", 60, 3, "E", 1, "E"),
    _t2c("nt-35", 199, 5, "W", 4, "W"),
    _c2t("nt-36", 137, 4, "W", 3, "E"),
    _c2t("nt-37", 305, 2, "W", 6, "E"),
    _c2t("nt-38", 274, 3, "E", 7, "W"),
    _c2t("nt-39", 221, 2, "W", 6, "E"),
    _c2t("nt-40", 14, 5, "E", 4, "W"),

    # ── ★ Со звёздочкой: переход через 360° / 0° (подвох) ──
    _t2c("nt-41", 357, 6, "W", 3, "W", star=True),   # 357+6+3=366 → 6
    _t2c("nt-42", 3, 5, "E", 4, "E", star=True),   # 3−5−4 = −6 → 354
    _t2m("nt-43", 358, 5, "W", star=True),           # 358+5=363 → 3
    _t2m("nt-44", 2, 7, "E", star=True),           # 2−7 = −5 → 355
    _c2t("nt-45", 5, 4, "W", 6, "W", star=True),   # 5−4−6 = −5 → 355
    _c2t("nt-46", 356, 3, "E", 5, "E", star=True),   # 356+3+5=364 → 4
    _m2c("nt-47", 359, 4, "W", star=True),           # 359+4=363 → 3
    _t2c("nt-48", 1, 3, "E", 5, "E", star=True),   # 1−3−5 = −7 → 353
    _c2m("nt-49", 358, 5, "E", star=True),           # 358+5=363 → 3
    _t2c("nt-50", 350, 8, "W", 7, "W", star=True),   # 350+8+7=365 → 5
]

TASKS_BY_ID = {t.id: t for t in TASKS}


def starred_tasks() -> list[NavTask]:
    return [t for t in TASKS if t.starred]
