"""
Морские расчёты: скорость–дистанция–время (S-D-T) и ETA.

Единицы:
- скорость — узлы (мор. мили в час),
- дистанция — морские мили (NM),
- время — часы (внутри), наружу отдаём ещё и «ч:мм».

Чистые функции (без I/O) — общий источник правды для бота, Mini App и тестов.
Здесь же генератор практических задач с проверкой ответа и допуском.
"""

from dataclasses import dataclass

# ──────────────────────── Базовые расчёты ────────────────────────

def time_from(distance_nm: float, speed_kn: float) -> float:
    """Время в часах = дистанция / скорость."""
    if speed_kn <= 0:
        raise ValueError("Скорость должна быть больше 0")
    return distance_nm / speed_kn


def distance_from(speed_kn: float, time_h: float) -> float:
    """Дистанция (NM) = скорость × время."""
    return speed_kn * time_h


def speed_from(distance_nm: float, time_h: float) -> float:
    """Скорость (узлы) = дистанция / время."""
    if time_h <= 0:
        raise ValueError("Время должно быть больше 0")
    return distance_nm / time_h


def hours_to_hm(hours: float) -> str:
    """0.5 -> «0 ч 30 мин», 2.25 -> «2 ч 15 мин»."""
    if hours < 0:
        hours = 0.0
    total_min = round(hours * 60)
    h, m = divmod(total_min, 60)
    return f"{h} ч {m:02d} мин"


def eta_clock(start_hhmm: str, travel_h: float) -> str:
    """
    Прибавить время в пути к времени старта «ЧЧ:ММ» -> «ЧЧ:ММ» (24ч, по кругу).
    Возвращает строку времени прибытия; переход через полночь учитывается.
    """
    start = _parse_hhmm(start_hhmm)
    arrive = (start + round(travel_h * 60)) % (24 * 60)
    return f"{arrive // 60:02d}:{arrive % 60:02d}"


def _parse_hhmm(s: str) -> int:
    """«09:30» / «0930» / «9:5» -> минуты от полуночи. Бросает ValueError."""
    s = str(s).strip().replace(".", ":")
    if ":" in s:
        hh, mm = s.split(":", 1)
    elif len(s) in (3, 4) and s.isdigit():
        hh, mm = s[:-2], s[-2:]
    else:
        raise ValueError("Время старта в формате ЧЧ:ММ")
    h, m = int(hh), int(mm)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError("Недопустимое время")
    return h * 60 + m


# ──────────────────────── ETA с запасом ────────────────────────

@dataclass
class EtaResult:
    travel_h: float          # чистое время в пути, ч
    travel_h_reserve: float  # время с запасом, ч
    reserve_pct: float
    eta: str | None          # «ЧЧ:ММ», если задано время старта


def plan_eta(distance_nm: float, speed_kn: float,
             reserve_pct: float = 0.0, start_hhmm: str | None = None) -> EtaResult:
    """
    Время в пути и ETA. reserve_pct — добавочный запас на течения/манёвры
    (например 20 -> время ×1.2). start_hhmm — опционально время отхода.
    """
    base = time_from(distance_nm, speed_kn)
    with_reserve = base * (1 + max(0.0, reserve_pct) / 100.0)
    eta = eta_clock(start_hhmm, with_reserve) if start_hhmm else None
    return EtaResult(base, with_reserve, reserve_pct, eta)


# ──────────────────────── Практические задачи ────────────────────────

@dataclass
class MarineTask:
    id: str
    text: str          # условие
    answer: float      # верный ответ (в указанных единицах)
    unit: str          # единицы ответа: «ч», «NM», «узлов», «мин»
    tol: float         # допуск (±), в тех же единицах
    solution: str      # пошаговое решение

    def check(self, user: str) -> bool:
        try:
            val = float(str(user).strip().replace(",", ".")
                        .replace("ч", "").replace("h", "").strip())
        except ValueError:
            return False
        return abs(val - self.answer) <= self.tol + 1e-9


# Набор «формочек» задач. Значения подставляются генератором; ответы и
# решения считаются теми же функциями, что выше (без рассинхрона).

def task_time(n: str, speed: float, dist: float) -> MarineTask:
    h = time_from(dist, speed)
    return MarineTask(
        id=n,
        text=f"Идём {_num(speed)} узла. До точки {_num(dist)} NM. "
             f"Сколько времени идти? (часов)",
        answer=round(h, 2), unit="ч", tol=0.05,
        solution=f"t = D / V = {_num(dist)} / {_num(speed)} = "
                 f"{round(h,2)} ч ({hours_to_hm(h)}).",
    )


def task_distance(n: str, speed: float, time_h: float) -> MarineTask:
    d = distance_from(speed, time_h)
    return MarineTask(
        id=n,
        text=f"Скорость {_num(speed)} узла, идём {_num(time_h)} ч. "
             f"Какое расстояние пройдём? (NM)",
        answer=round(d, 1), unit="NM", tol=0.2,
        solution=f"D = V × t = {_num(speed)} × {_num(time_h)} = {round(d,1)} NM.",
    )


def task_speed(n: str, dist: float, time_h: float) -> MarineTask:
    v = speed_from(dist, time_h)
    return MarineTask(
        id=n,
        text=f"Прошли {_num(dist)} NM за {_num(time_h)} ч. "
             f"Какая средняя скорость? (узлов)",
        answer=round(v, 1), unit="узлов", tol=0.2,
        solution=f"V = D / t = {_num(dist)} / {_num(time_h)} = {round(v,1)} узла.",
    )


def task_eta(n: str, dist: float, speed: float, reserve: int, start: str) -> MarineTask:
    r = plan_eta(dist, speed, reserve, start)
    return MarineTask(
        id=n,
        text=f"Отход в {start}. Идти {_num(dist)} NM со скоростью {_num(speed)} "
             f"узла, запас {reserve}%. Во сколько прибудем? (ЧЧ:ММ → ответь часами "
             f"в пути, напр. 2.4)",
        answer=round(r.travel_h_reserve, 2), unit="ч", tol=0.05,
        solution=(f"t = D / V = {_num(dist)} / {_num(speed)} = "
                  f"{round(r.travel_h,2)} ч; с запасом {reserve}% → "
                  f"{round(r.travel_h_reserve,2)} ч ({hours_to_hm(r.travel_h_reserve)}). "
                  f"ETA = {r.eta}."),
    )


def _num(x: float) -> str:
    """Красивое число: 5.0 -> «5», 5.5 -> «5,5» (рус. запятая)."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


# Готовый воспроизводимый банк практических задач (как у nav_tasks — список
# фиксирован, чтобы прогресс был воспроизводим; можно расширять).
TASKS: list[MarineTask] = [
    task_time("mt-01", 5.5, 13.2),
    task_time("mt-02", 6, 18),
    task_time("mt-03", 4.5, 9),
    task_time("mt-04", 7, 21),
    task_time("mt-05", 5, 12.5),
    task_distance("mt-06", 6, 2.5),
    task_distance("mt-07", 5.5, 3),
    task_distance("mt-08", 8, 1.5),
    task_distance("mt-09", 4, 4),
    task_distance("mt-10", 6.5, 2),
    task_speed("mt-11", 15, 3),
    task_speed("mt-12", 22, 4),
    task_speed("mt-13", 9, 1.5),
    task_speed("mt-14", 30, 5),
    task_speed("mt-15", 11, 2),
    task_eta("mt-16", 18, 5, 20, "09:00"),
    task_eta("mt-17", 24, 6, 15, "07:30"),
    task_eta("mt-18", 12, 4, 25, "14:00"),
    task_eta("mt-19", 30, 5, 10, "06:00"),
    task_eta("mt-20", 16, 8, 20, "22:30"),
]

TASKS_BY_ID = {t.id: t for t in TASKS}
