"""
Слияние состояния синхронизации (server vs incoming) — чистые функции, без БД
и без FastAPI, чтобы легко тестировать.

Принцип: НИКОГДА не затираем прогресс вслепую. При конфликте устройств берём
«лучшее»: для SRS-коробок и due — более продвинутое состояние; для streak/best —
максимум; для дней активности — объединение. Агрегированную статистику здесь
НЕ суммируем (двойной счёт), оставляем серверную как есть.

ИСКЛЮЧЕНИЕ из «лучшего» — SRS (волна A, находка о потере сбросов). Там
«лучшее» = более СВЕЖЕЕ, а не более выученное: сброс коробки после ошибки
обязан пережить синхронизацию с устройством, которое об ошибке не знает.

Синхронизируем три пространства:
  srs         — issa_srs_v1:         { qid: {box, due, ts} }
  progress    — issa_progress_v1:    { goal, days:{ "YYYY-MM-DD": n }, streak,
                                       best, lastDay, frozenUsed, flags }
  pl_progress — issa_pl_progress_v1: { lic: {solved:{qid:1}, bestCorrect, bestTotal} }
"""
from __future__ import annotations

import logging
import math
import re

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

# Ключ дня активности: строго YYYY-MM-DD. Без этой проверки длина ключа ничем
# не ограничена (потолок был только по ЧИСЛУ ключей), и подписанный клиент мог
# растить состояние сотнями мегабайт по четверти мегабайта за запрос.
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_DAY_COUNT = 100_000     # ответов за день; заведомо недостижимо человеком
# Верхняя граница ts (мс): 2100-01-01. Отсекает мусор и «вечно свежие» записи.
MAX_TS_MS = 4_102_444_800_000


def merge_srs(server: dict | None, incoming: dict | None) -> dict:
    """Для каждого вопроса берём более СВЕЖЕЕ состояние.

    Почему не «более выученное» (как было до волны A): при критерии «выше box»
    ошибка, сделанная на телефоне (box 4 → 0), проигрывала устаревшей записи
    box 4 с планшета — сброс молча откатывался, и вопрос уходил на 21 день
    вместо скорого повтора. Теперь побеждает запись с более поздним ts.

    Совместимость со старыми записями (без ts):
      • обе с ts        → больший ts; при равном ts — выше box;
      • только одна с ts → побеждает она (её писал уже обновлённый клиент);
      • ни одной с ts    → прежнее правило (выше box, при равном — больший due).
    Средний случай сознательно ошибается в сторону ЛИШНЕГО повторения: если
    устройство на старом коде дало верный ответ, мы можем оставить более раннюю
    коробку, и вопрос повторится раньше нужного. Обратная ошибка (потерять
    сброс и не показать забытый вопрос три недели) для обучения куда дороже.

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
            out[qid] = _norm_srs(a)
    # 2) входящее — детерминированным порядком, новые ключи под потолком
    over_len = over_cap = 0
    for qid in sorted(incoming):
        b = incoming[qid]
        if not _valid_srs(b):
            continue
        b = _norm_srs(b)
        a = out.get(qid)
        if a is None:
            if len(qid) > MAX_KEY_LEN:
                over_len += 1
                continue
            if len(out) >= MAX_SRS_KEYS:
                over_cap += 1
                continue
            out[qid] = b
        elif _srs_newer(a, b):
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

    # дни активности: объединяем, при совпадении берём больший счётчик.
    # Ключ обязан быть датой YYYY-MM-DD: иначе длина ключа ничем не ограничена
    # (потолок был только по их числу) — см. DAY_RE. Мусорные ключи отбрасываем
    # из ОБОИХ источников, включая серверный: легальный клиент их не создаёт,
    # а сохранять их — значит хранить чужой мусор вечно.
    days: dict = {}
    bad_days = 0
    for src in (server.get("days") or {}, incoming.get("days") or {}):
        if not isinstance(src, dict):
            continue
        for day, n in src.items():
            if not isinstance(day, str) or not DAY_RE.match(day):
                bad_days += 1
                continue
            n = _num(n)
            if n is None:
                continue
            n = max(0, min(MAX_DAY_COUNT, int(n)))
            days[day] = max(days.get(day, 0), n)
    if bad_days:
        log.warning("merge_progress: отброшено %d дней активности с некорректным ключом "
                    "(ожидается YYYY-MM-DD)", bad_days)
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

    # lastDay — лексикографически больший (формат YYYY-MM-DD сортируется как дата).
    # Тот же DAY_RE: иначе это ещё один неограниченный по длине ключ в состоянии.
    def day_or_empty(v) -> str:
        return v if isinstance(v, str) and DAY_RE.match(v) else ""

    last_s = day_or_empty(server.get("lastDay"))
    last_i = day_or_empty(incoming.get("lastDay"))
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


def _num(v):
    """Число или None. bool отсекаем (в JS `typeof true !== "number"` — держим
    паритет), NaN/Infinity тоже: json.loads их принимает, а int(NaN) роняет
    запрос в 500."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if not math.isfinite(v):
        return None
    return v


def _valid_srs(s) -> bool:
    if not isinstance(s, dict):
        return False
    box, due = _num(s.get("box")), _num(s.get("due"))
    return box is not None and due is not None and 0 <= box <= 5


def _norm_srs(s: dict) -> dict:
    """Привести запись к {box, due[, ts]} — ts только если он осмысленный."""
    out = {"box": int(s["box"]), "due": int(s["due"])}
    ts = _num(s.get("ts"))
    if ts is not None and 0 < ts <= MAX_TS_MS:
        out["ts"] = int(ts)
    return out


def _srs_newer(a: dict, b: dict) -> bool:
    """Свежее ли b, чем a (обе записи уже нормализованы). См. merge_srs."""
    ta, tb = a.get("ts"), b.get("ts")
    if ta is not None and tb is not None:
        return tb > ta or (tb == ta and b["box"] > a["box"])
    if tb is not None:
        return True         # b писал обновлённый клиент, a — старый
    if ta is not None:
        return False
    # обе старые: прежнее правило «более выученное»
    return b["box"] > a["box"] or (b["box"] == a["box"] and b["due"] > a["due"])
