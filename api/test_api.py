"""
Тесты API синхронизации: HMAC initData, merge-логика, эндпоинты.
Запуск:  python api/test_api.py   (или pytest api/test_api.py)

Часть тестов (merge, auth) не требует fastapi и идёт всегда.
Эндпоинты проверяются через TestClient, если установлен fastapi+httpx.
"""
import json
import os
import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth import verify_init_data, build_init_data, InitDataError
from merge import (merge_srs, merge_progress, merge_pl_progress, merge_state,
                   MAX_SRS_KEYS, MAX_FLAGS, MAX_KEY_LEN, MAX_PL_SOLVED, MAX_PL_LICENSES)

TOKEN = "123456:TEST-TOKEN-abcdef"
fails = 0


def check(name, cond):
    global fails
    print(("  ✓ " if cond else "  ✗ ") + name)
    if not cond:
        fails += 1


# ── auth: HMAC initData ──
def test_auth():
    init = build_init_data(TOKEN, {"id": 777, "first_name": "Skip"})
    info = verify_init_data(init, TOKEN)
    check("валидный initData → user_id", info["user_id"] == 777)

    # подделка: чужой токен не проходит
    try:
        verify_init_data(init, "999:WRONG"); ok = False
    except InitDataError:
        ok = True
    check("неверный токен → отказ", ok)

    # подмена user_id внутри строки ломает подпись
    tampered = init.replace("777", "778")
    try:
        verify_init_data(tampered, TOKEN); ok = False
    except InitDataError:
        ok = True
    check("подмена user_id → отказ", ok)

    # протухший auth_date
    old = build_init_data(TOKEN, {"id": 1}, auth_date=int(time.time()) - 100000)
    try:
        verify_init_data(old, TOKEN, max_age_sec=3600); ok = False
    except InitDataError:
        ok = True
    check("протухший initData → отказ", ok)


# ── merge: SRS ──
def test_merge_srs():
    server = {"a": {"box": 3, "due": 100}, "b": {"box": 1, "due": 50}}
    incoming = {"a": {"box": 2, "due": 999}, "c": {"box": 0, "due": 10}}
    m = merge_srs(server, incoming)
    check("SRS: выше box побеждает (a=3)", m["a"]["box"] == 3)
    check("SRS: server-only сохранён (b)", m["b"]["box"] == 1)
    check("SRS: incoming-only добавлен (c)", m["c"]["box"] == 0)

    # равный box → больший due
    m2 = merge_srs({"x": {"box": 2, "due": 100}}, {"x": {"box": 2, "due": 200}})
    check("SRS: равный box → больший due", m2["x"]["due"] == 200)

    # битые записи игнорируются
    m3 = merge_srs({"x": {"box": 9, "due": 1}}, {"x": {"box": 4, "due": 5}})
    check("SRS: невалидный box>5 отброшен", m3["x"]["box"] == 4)


# ── merge: progress ──
def test_merge_progress():
    server = {"streak": 5, "best": 7, "days": {"2026-06-20": 3}, "lastDay": "2026-06-20", "goal": 15}
    incoming = {"streak": 3, "best": 4, "days": {"2026-06-20": 5, "2026-06-21": 2}, "lastDay": "2026-06-21", "goal": 20}
    m = merge_progress(server, incoming)
    check("progress: streak = max", m["streak"] == 5)
    check("progress: best = max(best, streak)", m["best"] == 7)
    check("progress: days union, max по дню", m["days"]["2026-06-20"] == 5 and m["days"]["2026-06-21"] == 2)
    check("progress: lastDay = более поздний", m["lastDay"] == "2026-06-21")
    check("progress: goal из incoming", m["goal"] == 20)

    # пустые/None не падают
    check("progress: None-входы → дефолт", merge_progress(None, None)["streak"] == 0)

    # heatmap: храним до 365 дней (раньше резалось на 120 — ломало карту >4 мес)
    from merge import MAX_HEATMAP_DAYS
    check("heatmap лимит = 365", MAX_HEATMAP_DAYS == 365)
    many = {f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}": 1 for i in range(300)}
    m200 = merge_progress({"days": many}, {})
    check("heatmap: 300 дней (<365) хранятся целиком", len(m200["days"]) == 300)
    over = {f"day-{i:04d}": 1 for i in range(500)}    # 500 «дней» → обрезка до 365
    mover = merge_progress({"days": over}, {})
    check("heatmap: 500 дней обрезаются до 365", len(mover["days"]) == MAX_HEATMAP_DAYS)
    # и остаются именно ПОСЛЕДНИЕ (по сортировке) — старейшие удалены
    check("heatmap: остаются последние (старейшие удалены)",
          "day-0000" not in mover["days"] and "day-0499" in mover["days"])


def test_merge_pl_progress():
    # ТЕ ЖЕ кейсы, что в webapp/_sync_check.mjs — паритет JS↔Python.
    server = {"zeglarz": {"solved": {"zj-1": 1, "zj-2": 1}, "bestCorrect": 40, "bestTotal": 50},
              "sternik": {"solved": {"st-1": 1}, "bestCorrect": 20, "bestTotal": 50}}
    incoming = {"zeglarz": {"solved": {"zj-2": 1, "zj-3": 1}, "bestCorrect": 35, "bestTotal": 45}}
    m = merge_pl_progress(server, incoming)
    check("pl: solved union", sorted(m["zeglarz"]["solved"]) == ["zj-1", "zj-2", "zj-3"])
    check("pl: лучший best со своим total",
          m["zeglarz"]["bestCorrect"] == 40 and m["zeglarz"]["bestTotal"] == 50)
    check("pl: server-only лицензия сохранена",
          m["sternik"]["bestCorrect"] == 20 and m["sternik"]["solved"].get("st-1") == 1)
    check("pl: None → {}", merge_pl_progress(None, None) == {})
    check("pl: solved без экзамена → bestCorrect None",
          merge_pl_progress({"zeglarz": {"solved": {"a": 1}}}, {})["zeglarz"]["bestCorrect"] is None)
    # incoming с бОльшим best забирает и свой total (не max по total)
    mt = merge_pl_progress({"zeglarz": {"bestCorrect": 30, "bestTotal": 50}},
                           {"zeglarz": {"bestCorrect": 44, "bestTotal": 45}})
    check("pl: total идёт за лучшим correct, а не max",
          mt["zeglarz"]["bestCorrect"] == 44 and mt["zeglarz"]["bestTotal"] == 45)
    # обратная совместимость: пустой сервер НЕ затирает локальные solved
    keep = merge_pl_progress({}, {"zeglarz": {"solved": {"zj-9": 1}}})
    check("pl: пустой сервер не теряет incoming solved", keep["zeglarz"]["solved"].get("zj-9") == 1)


# ── потолки состояния (волна 0, H1) ──
# Политика: потолок применяется к ВХОДЯЩЕМУ payload; серверное состояние
# сохраняется целиком и никогда не режется; лишнее из incoming отбрасывается
# детерминированно. Банк вопросов при этом НЕ проверяется.
def test_merge_caps():
    check("потолки заданы с запасом к реальным банкам (RU 605 + PL 610 = 1215)",
          MAX_SRS_KEYS >= 1500 and MAX_KEY_LEN >= 11 and MAX_FLAGS >= 14)

    # 1) полтора банка ключей проходят НЕТРОНУТЫМИ (регресс-страж: потолок не
    #    должен задевать реального пользователя)
    bank15 = {f"q-{i:04d}": {"box": 2, "due": 1000 + i} for i in range(1500)}
    m = merge_srs({}, bank15)
    check("SRS: 1500 ключей (полтора банка) проходят нетронутыми",
          len(m) == 1500 and m["q-0000"]["box"] == 2 and m["q-1499"]["due"] == 2499)

    # 2) поток сверх потолка обрезается, но ровно до MAX_SRS_KEYS и детерминированно
    flood = {f"z-{i:05d}": {"box": 1, "due": i} for i in range(3000)}
    mf = merge_srs({}, flood)
    check(f"SRS: {3000} входящих ключей обрезаются до MAX_SRS_KEYS",
          len(mf) == MAX_SRS_KEYS)
    check("SRS: обрезка детерминированная (остаются первые по сортировке)",
          "z-00000" in mf and f"z-{MAX_SRS_KEYS:05d}" not in mf)
    check("SRS: повторный merge даёт тот же результат (детерминизм)",
          merge_srs({}, flood) == mf)

    # 3) серверное состояние НЕ режется, даже если оно уже больше потолка
    huge_server = {f"s-{i:05d}": {"box": 3, "due": i} for i in range(MAX_SRS_KEYS + 500)}
    ms = merge_srs(huge_server, {"new-1": {"box": 1, "due": 1}})
    check("SRS: серверные ключи сверх потолка сохранены (ничего не удалено)",
          len(ms) == MAX_SRS_KEYS + 500 and "s-00000" in ms)
    check("SRS: при переполнении новый входящий ключ отброшен, сервер выигрывает",
          "new-1" not in ms)
    # но обновление УЖЕ существующего ключа проходит — объём от этого не растёт
    ms2 = merge_srs(huge_server, {"s-00000": {"box": 5, "due": 9999}})
    check("SRS: апдейт существующего ключа проходит и при переполнении",
          ms2["s-00000"]["box"] == 5)

    # 4) длина ключа
    long_key = "x" * (MAX_KEY_LEN + 1)
    ml = merge_srs({}, {long_key: {"box": 1, "due": 1}, "ok": {"box": 1, "due": 1}})
    check("SRS: слишком длинный входящий ключ отброшен",
          long_key not in ml and "ok" in ml)
    keep = merge_srs({long_key: {"box": 2, "due": 5}}, {})
    check("SRS: длинный ключ, уже лежащий на сервере, не удаляется", long_key in keep)

    # 5) флаги-достижения
    mflags = merge_progress({"flags": {"exam_pass": True}},
                            {"flags": {f"f{i:03d}": True for i in range(500)}})
    check(f"flags: обрезаны до MAX_FLAGS ({MAX_FLAGS})", len(mflags["flags"]) == MAX_FLAGS)
    check("flags: серверный бейдж пережил поток входящих",
          mflags["flags"].get("exam_pass") is True)

    # 6) pl_progress: solved и лицензии
    mpl = merge_pl_progress({"zeglarz": {"solved": {"zj-001": 1}}},
                            {"zeglarz": {"solved": {f"x-{i:05d}": 1 for i in range(3000)}}})
    check(f"pl: solved обрезан до MAX_PL_SOLVED ({MAX_PL_SOLVED})",
          len(mpl["zeglarz"]["solved"]) == MAX_PL_SOLVED)
    check("pl: серверный solved сохранён при потоке входящих",
          mpl["zeglarz"]["solved"].get("zj-001") == 1)
    mlic = merge_pl_progress({"zeglarz": {"solved": {"zj-001": 1}}},
                             {f"lic{i}": {"solved": {"a": 1}} for i in range(50)})
    check(f"pl: число лицензий обрезано до MAX_PL_LICENSES ({MAX_PL_LICENSES})",
          len(mlic) == MAX_PL_LICENSES)
    check("pl: серверная лицензия на месте после обрезки",
          mlic["zeglarz"]["solved"].get("zj-001") == 1)

    # 7) реальный размер банков заведомо ниже потолков — обычный пользователь
    #    потолков не видит вовсе
    real = merge_state(
        {"srs": {f"q-{i:03d}": {"box": 1, "due": i} for i in range(605)},
         "progress": {"flags": {"exam_pass": True}},
         "pl_progress": {"zeglarz": {"solved": {f"zj-{i:03d}": 1 for i in range(150)}},
                         "sternik": {"solved": {f"st-{i:03d}": 1 for i in range(460)}}}},
        {"srs": {"q-000": {"box": 2, "due": 5}}, "progress": {}, "pl_progress": {}})
    check("реальные банки (605 + 150 + 460) проходят целиком",
          len(real["srs"]) == 605
          and len(real["pl_progress"]["zeglarz"]["solved"]) == 150
          and len(real["pl_progress"]["sternik"]["solved"]) == 460)


# ── эндпоинты (если есть fastapi) ──
def test_endpoints():
    try:
        from fastapi.testclient import TestClient
    except Exception:
        print("  ⚠ fastapi/httpx не установлены — пропускаю тесты эндпоинтов")
        return
    # отдельная временная БД и токен
    tmp = tempfile.mkdtemp()
    os.environ["ISSA_API_DB"] = str(Path(tmp) / "t.db")
    os.environ["BOT_TOKEN"] = TOKEN
    # переимпорт модуля с новым окружением
    import importlib
    import api as apimod
    importlib.reload(apimod)
    # with-контекст обязателен: иначе lifespan (init_db) не отработает
    with TestClient(apimod.app) as client:
        init = build_init_data(TOKEN, {"id": 42, "first_name": "T"})
        h = {"X-Init-Data": init}

        check("health 200", client.get("/api/health").status_code == 200)
        check("state без initData → 401", client.get("/api/state").status_code == 401)

        # пустое состояние
        r = client.get("/api/state", headers=h).json()
        check("новое состояние пустое",
              r["state"]["srs"] == {} and r["state"]["progress"] == {}
              and r["state"].get("pl_progress") == {})

        # POST мёрджит и возвращает merged (включая польский прогресс)
        body = {"srs": {"q1": {"box": 2, "due": 500}},
                "progress": {"streak": 4, "best": 4, "days": {"2026-06-25": 6}, "lastDay": "2026-06-25"},
                "pl_progress": {"zeglarz": {"solved": {"zj-1": 1}, "bestCorrect": 30, "bestTotal": 50}}}
        r = client.post("/api/state", headers=h, content=json.dumps(body)).json()
        check("POST вернул merged srs", r["state"]["srs"]["q1"]["box"] == 2)
        check("POST вернул merged pl_progress", r["state"]["pl_progress"]["zeglarz"]["solved"]["zj-1"] == 1)

        # второй POST с другого «устройства» — мёрдж, не перезапись
        body2 = {"srs": {"q1": {"box": 1, "due": 9999}, "q2": {"box": 0, "due": 1}},
                 "progress": {"streak": 2, "best": 2, "days": {"2026-06-26": 3}, "lastDay": "2026-06-26"},
                 "pl_progress": {"zeglarz": {"solved": {"zj-2": 1}, "bestCorrect": 44, "bestTotal": 50},
                                 "sternik": {"solved": {"st-9": 1}}}}
        r = client.post("/api/state", headers=h, content=json.dumps(body2)).json()
        check("merge: q1 сохранил box=2 (не затёрт)", r["state"]["srs"]["q1"]["box"] == 2)
        check("merge: q2 добавлен", r["state"]["srs"]["q2"]["box"] == 0)
        check("merge: streak=max(4,2)=4", r["state"]["progress"]["streak"] == 4)
        check("merge: days объединены", set(r["state"]["progress"]["days"]) == {"2026-06-25", "2026-06-26"})
        pl = r["state"]["pl_progress"]
        check("merge pl: zeglarz.solved union", set(pl["zeglarz"]["solved"]) == {"zj-1", "zj-2"})
        check("merge pl: zeglarz.best=max(30,44)=44", pl["zeglarz"]["bestCorrect"] == 44)
        check("merge pl: sternik добавлен новой лицензией", pl["sternik"]["solved"]["st-9"] == 1)

        # обратная совместимость: пустой incoming.pl_progress НЕ затирает серверный
        r = client.post("/api/state", headers=h,
                        content=json.dumps({"srs": {}, "progress": {}})).json()
        check("pl: POST без pl_progress не теряет серверный прогресс",
              r["state"]["pl_progress"]["zeglarz"]["solved"].get("zj-1") == 1)

        # лимит тела
        big = client.post("/api/state", headers=h, content=b"x" * (300 * 1024))
        check("слишком большое тело → 413", big.status_code == 413)

        # /api/invoice — благодарность (Stars)
        check("invoice без initData → 401",
              client.post("/api/invoice", json={"amount": 50}).status_code == 401)
        check("invoice: недопустимая сумма → 422",
              client.post("/api/invoice", headers=h, json={"amount": 77}).status_code == 422)
        check("invoice: отрицательная сумма → 422",
              client.post("/api/invoice", headers=h, json={"amount": -5}).status_code == 422)
        # допустимая сумма проходит валидацию и доходит до Telegram (фейк-токен →
        # createInvoiceLink не ok → 502). Главное: не 401/422, т.е. авторизация и
        # валидация пройдены.
        r = client.post("/api/invoice", headers=h, json={"amount": 50})
        check("invoice: валидная сумма проходит валидацию (не 401/422)",
              r.status_code not in (401, 422))


def test_attempts():
    try:
        from fastapi.testclient import TestClient
    except Exception:
        return
    tmp = tempfile.mkdtemp()
    os.environ["ISSA_API_DB"] = str(Path(tmp) / "a.db")
    os.environ["BOT_TOKEN"] = TOKEN
    import importlib, api as apimod
    importlib.reload(apimod)
    with TestClient(apimod.app) as client:
        init = build_init_data(TOKEN, {"id": 99, "first_name": "H"})
        h = {"X-Init-Data": init}

        check("attempts без initData → 401", client.get("/api/attempts").status_code == 401)
        check("история сначала пуста", client.get("/api/attempts", headers=h).json()["attempts"] == [])

        # добавить экзамен
        ex = {"ts": 1000, "mode": "exam", "total": 100, "correct": 80, "pct": 80, "secs": 1200}
        r = client.post("/api/attempts", headers=h, content=json.dumps(ex)).json()
        check("attempt добавлен, в ответе история", len(r["attempts"]) == 1 and r["attempts"][0]["pct"] == 80)

        # добавить тренировку позже — она первой (сортировка по ts DESC)
        tr = {"ts": 2000, "mode": "random", "total": 20, "correct": 15, "pct": 75, "secs": 200}
        r = client.post("/api/attempts", headers=h, content=json.dumps(tr)).json()
        check("2 записи, свежая первой", len(r["attempts"]) == 2 and r["attempts"][0]["mode"] == "random")

        # пустой total → 422 (Pydantic-валидация: total обязателен и ≥ 1)
        bad = client.post("/api/attempts", headers=h, content=json.dumps({"mode": "x"}))
        check("attempt без total → 422", bad.status_code == 422)

        # мусорный тип total → 422 (раньше падало 500 на int('abc'))
        badtype = client.post("/api/attempts", headers=h, content=json.dumps({"total": "abc"}))
        check("attempt total='abc' → 422 (не 500)", badtype.status_code == 422)

        # чужой пользователь не видит историю
        h2 = {"X-Init-Data": build_init_data(TOKEN, {"id": 1234, "first_name": "Z"})}
        check("чужая история пуста (изоляция по user_id)", client.get("/api/attempts", headers=h2).json()["attempts"] == [])


def test_body_limits():
    """Ранний 413 по Content-Length (до буферизации тела) + обычный POST → 200."""
    try:
        from fastapi.testclient import TestClient
    except Exception:
        print("  ⚠ fastapi/httpx не установлены — пропускаю тесты лимита тела")
        return
    tmp = tempfile.mkdtemp()
    os.environ["ISSA_API_DB"] = str(Path(tmp) / "b.db")
    os.environ["BOT_TOKEN"] = TOKEN
    import importlib, api as apimod
    importlib.reload(apimod)

    # чистая функция: решение принимается ДО чтения тела
    check("Content-Length сверх лимита → отказ без чтения тела",
          apimod._declared_too_large(str(apimod.MAX_BODY + 1)) is True)
    check("Content-Length в пределах лимита → пропуск",
          apimod._declared_too_large(str(apimod.MAX_BODY)) is False)
    check("отсутствующий/мусорный Content-Length не ломает обработку",
          apimod._declared_too_large(None) is False
          and apimod._declared_too_large("abc") is False)

    with TestClient(apimod.app) as client:
        h = {"X-Init-Data": build_init_data(TOKEN, {"id": 4242, "first_name": "B"})}

        # объявлен гигантский Content-Length при крошечном теле — тело не читаем
        r = client.post("/api/state",
                        headers={**h, "Content-Length": str(2 * 1024 * 1024 * 1024)},
                        content=b"{}")
        check("объявленный Content-Length 2 ГБ → 413 без буферизации",
              r.status_code == 413)
        # и это работает даже без initData (проверка стоит до auth)
        r = client.post("/api/state",
                        headers={"Content-Length": str(2 * 1024 * 1024 * 1024)},
                        content=b"{}")
        check("ранний 413 срабатывает и без initData", r.status_code == 413)

        # реально большое тело тоже отвергается
        big = client.post("/api/state", headers=h, content=b"x" * (300 * 1024))
        check("реальное тело 300 КБ → 413", big.status_code == 413)

        # НОРМАЛЬНЫЙ POST от sync-подобного клиента: банк RU + оба польских
        payload = {
            "srs": {f"q-{i:03d}": {"box": i % 6, "due": 1_700_000 + i} for i in range(605)},
            "progress": {"goal": 20, "streak": 9, "best": 12,
                         "days": {f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}": 5
                                  for i in range(300)},
                         "lastDay": "2026-07-30",
                         "flags": {"exam_pass": True, "flawless": True}},
            "pl_progress": {
                "zeglarz": {"solved": {f"zj-{i:03d}": 1 for i in range(150)},
                            "bestCorrect": 70, "bestTotal": 75},
                "sternik": {"solved": {f"st-{i:03d}": 1 for i in range(460)},
                            "bestCorrect": 60, "bestTotal": 75}},
        }
        raw = json.dumps(payload)
        check(f"payload реального клиента укладывается в MAX_BODY ({len(raw)} байт)",
              len(raw.encode()) < apimod.MAX_BODY)
        r = client.post("/api/state", headers=h, content=raw)
        check("нормальный POST от sync-подобного клиента → 200", r.status_code == 200)
        st = r.json()["state"]
        check("нормальный POST: ничего не обрезано",
              len(st["srs"]) == 605
              and len(st["pl_progress"]["zeglarz"]["solved"]) == 150
              and len(st["pl_progress"]["sternik"]["solved"]) == 460
              and set(st["progress"]["flags"]) == {"exam_pass", "flawless"})

        # повторный POST того же состояния ничего не теряет (идемпотентность)
        r2 = client.post("/api/state", headers=h, content=raw)
        check("повторный POST не теряет ключей",
              len(r2.json()["state"]["srs"]) == 605)


def test_rate_limit():
    try:
        from fastapi.testclient import TestClient
    except Exception:
        return
    tmp = tempfile.mkdtemp()
    os.environ["ISSA_API_DB"] = str(Path(tmp) / "r.db")
    os.environ["BOT_TOKEN"] = TOKEN
    os.environ["ISSA_RATE_MAX"] = "5"        # маленький лимит для теста
    os.environ["ISSA_RATE_WINDOW"] = "60"
    import importlib, api as apimod
    importlib.reload(apimod)
    with TestClient(apimod.app) as client:
        h = {"X-Init-Data": build_init_data(TOKEN, {"id": 555})}
        codes = [client.get("/api/state", headers=h).status_code for _ in range(7)]
        check("первые 5 запросов в пределах лимита → 200",
              codes[:5] == [200] * 5)
        check("6-й и далее → 429 (rate limit)", codes[5] == 429 and codes[6] == 429)
        # health не лимитируется (без auth)
        hc = [client.get("/api/health").status_code for _ in range(10)]
        check("health не лимитируется", all(c == 200 for c in hc))
        # другой пользователь не затронут чужим лимитом
        h2 = {"X-Init-Data": build_init_data(TOKEN, {"id": 777})}
        check("другой пользователь — свой лимит (200)",
              client.get("/api/state", headers=h2).status_code == 200)
    # сбросим env, чтобы не влиять на другие прогоны
    os.environ.pop("ISSA_RATE_MAX", None)
    os.environ.pop("ISSA_RATE_WINDOW", None)


def test_concurrent_state():
    """API-1: параллельные POST /api/state не теряют SRS-записи (атомарный merge)."""
    try:
        import importlib, threading
        import api as apimod
    except Exception:
        return
    tmp = tempfile.mkdtemp()
    os.environ["ISSA_API_DB"] = str(Path(tmp) / "c.db")
    os.environ["BOT_TOKEN"] = TOKEN
    importlib.reload(apimod)
    apimod.init_db()
    uid = 555
    # 10 потоков, каждый добавляет свой уникальный SRS-ключ
    def worker(i):
        apimod.merge_and_save_state(uid, {"srs": {f"q{i}": {"box": 1, "due": i}}, "progress": {}})
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    final = apimod.load_state(uid)
    # все 10 ключей должны сохраниться — ни один не затёрт гонкой
    check("concurrent: все 10 SRS-записей сохранены (нет lost update)",
          len(final["srs"]) == 10)


if __name__ == "__main__":
    test_auth()
    test_merge_srs()
    test_merge_progress()
    test_merge_pl_progress()
    test_merge_caps()
    test_endpoints()
    test_attempts()
    test_body_limits()
    test_rate_limit()
    test_concurrent_state()
    if fails:
        print(f"\nAPI TESTS: {fails} провал(ов)")
        sys.exit(1)
    print("\nAPI TESTS OK")
