"""
Слияние состояния синхронизации (server vs incoming) — чистые функции, без БД
и без FastAPI, чтобы легко тестировать.

Принцип: НИКОГДА не затираем прогресс вслепую. При конфликте устройств берём
«лучшее»: для SRS-коробок и due — более продвинутое состояние; для streak/best —
максимум; для дней активности — объединение. Агрегированную статистику здесь
НЕ суммируем (двойной счёт), оставляем серверную как есть.

Синхронизируем три пространства:
  srs         — issa_srs_v1:         { qid: {box, due} }
  progress    — issa_progress_v1:    { goal, days:{ "YYYY-MM-DD": n }, streak,
                                       best, lastDay, frozenUsed, flags }
  pl_progress — issa_pl_progress_v1: { lic: {solved:{qid:1}, bestCorrect, bestTotal} }
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


def merge_pl_progress(server: dict | None, incoming: dict | None) -> dict:
    """Слить прогресс польских лицензий: { lic: {solved, bestCorrect, bestTotal} }.

    У польских банков нет SRS — только «решено верно хотя бы раз» и лучший
    результат экзамена. Поэтому:
      solved      — объединение множеств (union), чтобы не терять решённое;
      bestCorrect — максимум; bestTotal берём У ТОГО источника, что дал лучший
                    bestCorrect (иначе total разъедется с correct).
    Лицензии не хардкодим — идём по всем ключам из обоих источников.
    """
    server = server or {}
    incoming = incoming or {}
    out: dict = {}
    for license in set(server) | set(incoming):
        s_lic = server.get(license) or {}
        i_lic = incoming.get(license) or {}
        if not isinstance(s_lic, dict):
            s_lic = {}
        if not isinstance(i_lic, dict):
            i_lic = {}

        solved: dict = {}
        for src in (s_lic.get("solved") or {}, i_lic.get("solved") or {}):
            if isinstance(src, dict):
                for qid in src:
                    solved[qid] = 1

        def best_pair(d):
            try:
                c = int(d["bestCorrect"])
            except (KeyError, TypeError, ValueError):
                return None
            try:
                t = int(d.get("bestTotal"))
            except (TypeError, ValueError):
                t = None
            return (c, t)

        s_best = best_pair(s_lic)
        i_best = best_pair(i_lic)
        best = None
        if s_best and i_best:
            best = i_best if i_best[0] > s_best[0] else s_best
        else:
            best = s_best or i_best

        if solved or best:
            out[license] = {
                "solved": solved,
                "bestCorrect": best[0] if best else None,
                "bestTotal": best[1] if best else None,
            }
    return out


def merge_state(server: dict | None, incoming: dict | None) -> dict:
    """Слить целое состояние {srs, progress, pl_progress}."""
    server = server or {}
    incoming = incoming or {}
    return {
        "srs": merge_srs(server.get("srs"), incoming.get("srs")),
        "progress": merge_progress(server.get("progress"), incoming.get("progress")),
        "pl_progress": merge_pl_progress(server.get("pl_progress"), incoming.get("pl_progress")),
    }


def _valid_srs(s) -> bool:
    return (
        isinstance(s, dict)
        and isinstance(s.get("box"), (int, float))
        and isinstance(s.get("due"), (int, float))
        and 0 <= s["box"] <= 5
    )
