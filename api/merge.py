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

import logging

log = logging.getLogger("issa-api.merge")

# Сколько дней активности храним для тепловой карты (heatmap). 365 ≈ год —
# покрывает длительную подготовку, не ломая карту. ВАЖНО: должно совпадать с
# лимитом в webapp/sync.js (JS-merge сверяется с Python через _sync_check.mjs).
MAX_HEATMAP_DAYS = 365

# ── Потолки состояния (волна 0, находка H1) ─────────────────────────────────
# Задача: остановить БЕСКОНЕЧНЫЙ рост состояния. Раньше srs/flags/pl solved
# объединялись без верхней границы — подписанный клиент мог за час залить
# гигабайты мусора в общий диск.
#
# Политика (решение владельца):
#   • потолки применяются к ВХОДЯЩЕМУ payload при слиянии;
#   • существующее серверное состояние сохраняется целиком и НИКОГДА не режется —
#     даже если оно уже превышает потолок (чистка старых данных — не задача этой волны);
#   • при переполнении лишнее из incoming отбрасывается ДЕТЕРМИНИРОВАННО
#     (обход ключей в отсортированном порядке), с log.warning;
#   • qid НЕ сверяется с текущим банком вопросов — банк меняется, а прогресс
#     пользователя из-за этого терять нельзя.
#
# Калибровка по реальным банкам: RU 605 вопросов, Żeglarz 150, Sternik 460
# (всего 1215), бейджей 12–14, самый длинный id — 11 символов.
MAX_KEY_LEN = 64        # ~6× запаса к самому длинному реальному id (11)
MAX_SRS_KEYS = 2000     # ~1,6× всех банков разом — рост под будущие вопросы есть
MAX_FLAGS = 64          # бейджей 14; запас на 4× новых достижений
MAX_PL_LICENSES = 16    # сейчас 2 (zeglarz, sternik)
MAX_PL_SOLVED = 2000    # на лицензию; самый большой польский банк — 460


def merge_srs(server: dict | None, incoming: dict | None) -> dict:
    """Для каждого вопроса берём более «выученное» состояние.

    Критерий: выше box — лучше. При равном box берём более поздний due
    (его уже отодвинули дальше = недавнее верное повторение).

    Потолок MAX_SRS_KEYS применяется только к НОВЫМ ключам из incoming: всё,
    что уже лежит на сервере, переносится без ограничений (см. политику вверху
    файла). Обновление существующего ключа проходит всегда — оно не растит объём.
    """
    server = server or {}
    incoming = incoming or {}
    out: dict = {}
    # 1) серверное состояние — целиком, без потолка (ничего не удаляем)
    for qid, a in server.items():
        if _valid_srs(a):
            out[qid] = {"box": int(a["box"]), "due": int(a["due"])}
    # 2) входящее — детерминированным порядком, новые ключи под потолком
    over_len = over_cap = 0
    for qid in sorted(incoming):
        b = incoming[qid]
        if not _valid_srs(b):
            continue
        b = {"box": int(b["box"]), "due": int(b["due"])}
        a = out.get(qid)
        if a is None:
            if len(qid) > MAX_KEY_LEN:
                over_len += 1
                continue
            if len(out) >= MAX_SRS_KEYS:
                over_cap += 1
                continue
            out[qid] = b
        elif b["box"] > a["box"] or (b["box"] == a["box"] and b["due"] > a["due"]):
            out[qid] = b
    if over_len or over_cap:
        log.warning("merge_srs: отброшено из incoming — %d по длине ключа, %d по потолку "
                    "(%d ключей, лимит %d); серверное состояние сохранено",
                    over_len, over_cap, len(out), MAX_SRS_KEYS)
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
    # Серверные флаги идут первыми и без потолка; новые из incoming — под MAX_FLAGS.
    flags: dict = {}
    s_flags = server.get("flags")
    i_flags = incoming.get("flags")
    if isinstance(s_flags, dict):
        for k, v in s_flags.items():
            if v:
                flags[k] = True
    over = 0
    if isinstance(i_flags, dict):
        for k in sorted(i_flags):
            if not i_flags[k] or k in flags:
                continue
            if len(k) > MAX_KEY_LEN or len(flags) >= MAX_FLAGS:
                over += 1
                continue
            flags[k] = True
    if over:
        log.warning("merge_progress: отброшено %d входящих флагов (потолок %d), "
                    "серверные сохранены", over, MAX_FLAGS)
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

    # Список лицензий: серверные — все, без потолка; новые из incoming — под
    # MAX_PL_LICENSES, детерминированным порядком.
    licenses = list(server)
    over_lic = 0
    for lic in sorted(incoming):
        if lic in server:
            continue
        if len(lic) > MAX_KEY_LEN or len(licenses) >= MAX_PL_LICENSES:
            over_lic += 1
            continue
        licenses.append(lic)
    if over_lic:
        log.warning("merge_pl_progress: отброшено %d входящих лицензий (потолок %d)",
                    over_lic, MAX_PL_LICENSES)

    over_solved = 0
    for license in licenses:
        s_lic = server.get(license) or {}
        i_lic = incoming.get(license) or {}
        if not isinstance(s_lic, dict):
            s_lic = {}
        if not isinstance(i_lic, dict):
            i_lic = {}

        # solved: серверное множество целиком, входящее — под потолком на лицензию
        solved: dict = {}
        s_solved = s_lic.get("solved")
        i_solved = i_lic.get("solved")
        if isinstance(s_solved, dict):
            for qid in s_solved:
                solved[qid] = 1
        if isinstance(i_solved, dict):
            for qid in sorted(i_solved):
                if qid in solved:
                    continue
                if len(qid) > MAX_KEY_LEN or len(solved) >= MAX_PL_SOLVED:
                    over_solved += 1
                    continue
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
    if over_solved:
        log.warning("merge_pl_progress: отброшено %d входящих solved (потолок %d на лицензию), "
                    "серверные сохранены", over_solved, MAX_PL_SOLVED)
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
