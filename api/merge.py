"""
Слияние состояния синхронизации (server vs incoming) — чистые функции, без БД
и без FastAPI, чтобы легко тестировать.

Принцип: НИКОГДА не затираем прогресс вслепую. При конфликте устройств берём
«лучшее»: для SRS-коробок и due — более продвинутое состояние; для streak/best —
максимум; для дней активности — объединение. Агрегированную статистику здесь
НЕ суммируем (двойной счёт), оставляем серверную как есть.

Синхронизируем только два пространства:
  srs       — issa_srs_v1:      { qid: {box, due} }
  progress  — issa_progress_v1: { goal, days:{ "YYYY-MM-DD": n }, streak, best,
                                   lastDay, frozenUsed }
"""
from __future__ import annotations

# Сколько дней активности храним для тепловой карты (heatmap). 365 ≈ год —
# покрывает длительную подготовку, не ломая карту. ВАЖНО: должно совпадать с
# лимитом в webapp/sync.js (JS-merge сверяется с Python через _sync_check.mjs).
MAX_HEATMAP_DAYS = 365


def merge_srs(server: dict | None, incoming: dict | None) -> dict:
    """Для каждого вопроса берём более «выученное» состояние.

    Критерий: выше box — лучше. При равном box берём более поздний due
    (его уже отодвинули дальше = недавнее верное повторение).
    """
    server = server or {}
    incoming = incoming or {}
    out: dict = {}
    for qid in set(server) | set(incoming):
        a = server.get(qid)
        b = incoming.get(qid)
        if not _valid_srs(a):
            a = None
        if not _valid_srs(b):
            b = None
        if a is None:
            if b is not None:
                out[qid] = {"box": int(b["box"]), "due": int(b["due"])}
            continue
        if b is None:
            out[qid] = {"box": int(a["box"]), "due": int(a["due"])}
            continue
        if b["box"] > a["box"] or (b["box"] == a["box"] and b["due"] > a["due"]):
            out[qid] = {"box": int(b["box"]), "due": int(b["due"])}
        else:
            out[qid] = {"box": int(a["box"]), "due": int(a["due"])}
    return out


def merge_progress(server: dict | None, incoming: dict | None) -> dict:
    """streak/best — max; days — объединение (max по дню); цель/lastDay — свежее."""
    server = server or {}
    incoming = incoming or {}

    # дни активности: объединяем, при совпадении берём больший счётчик
    days: dict = {}
    for src in (server.get("days") or {}, incoming.get("days") or {}):
        if not isinstance(src, dict):
            continue
        for day, n in src.items():
            try:
                n = int(n)
            except (TypeError, ValueError):
                continue
            days[day] = max(days.get(day, 0), n)
    # держим компактно — последние MAX_HEATMAP_DAYS дней
    if len(days) > MAX_HEATMAP_DAYS:
        for day in sorted(days)[:-MAX_HEATMAP_DAYS]:
            del days[day]

    def num(d, key, default=0):
        try:
            return int(d.get(key, default))
        except (TypeError, ValueError):
            return default

    streak = max(num(server, "streak"), num(incoming, "streak"))
    best = max(num(server, "best"), num(incoming, "best"), streak)
    goal = num(incoming, "goal") or num(server, "goal") or 15

    # lastDay — лексикографически больший (формат YYYY-MM-DD сортируется как дата)
    last_s = server.get("lastDay") or ""
    last_i = incoming.get("lastDay") or ""
    last_day = max(last_s, last_i) or None

    out = {
        "goal": max(5, min(100, goal)),
        "days": days,
        "streak": streak,
        "best": best,
    }
    if last_day:
        out["lastDay"] = last_day
        # frozenUsed относится к актуальному lastDay — берём из его источника
        out["frozenUsed"] = bool(
            (incoming if last_i >= last_s else server).get("frozenUsed", False)
        )
    # флаги-достижения (examPass/flawless) — заслуженный бейдж не должен теряться:
    # объединяем (OR) из обоих источников. Иначе sync стирает только что выданные бейджи.
    flags = {}
    for src in (server.get("flags") or {}, incoming.get("flags") or {}):
        if isinstance(src, dict):
            for k, v in src.items():
                if v:
                    flags[k] = True
    if flags:
        out["flags"] = flags
    return out


def merge_state(server: dict | None, incoming: dict | None) -> dict:
    """Слить целое состояние {srs, progress}."""
    server = server or {}
    incoming = incoming or {}
    return {
        "srs": merge_srs(server.get("srs"), incoming.get("srs")),
        "progress": merge_progress(server.get("progress"), incoming.get("progress")),
    }


def _valid_srs(s) -> bool:
    return (
        isinstance(s, dict)
        and isinstance(s.get("box"), (int, float))
        and isinstance(s.get("due"), (int, float))
        and 0 <= s["box"] <= 5
    )
