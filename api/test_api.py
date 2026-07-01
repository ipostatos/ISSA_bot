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
from merge import merge_srs, merge_progress, merge_state

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
        check("новое состояние пустое", r["state"]["srs"] == {} and r["state"]["progress"] == {})

        # POST мёрджит и возвращает merged
        body = {"srs": {"q1": {"box": 2, "due": 500}}, "progress": {"streak": 4, "best": 4, "days": {"2026-06-25": 6}, "lastDay": "2026-06-25"}}
        r = client.post("/api/state", headers=h, content=json.dumps(body)).json()
        check("POST вернул merged srs", r["state"]["srs"]["q1"]["box"] == 2)

        # второй POST с другого «устройства» — мёрдж, не перезапись
        body2 = {"srs": {"q1": {"box": 1, "due": 9999}, "q2": {"box": 0, "due": 1}}, "progress": {"streak": 2, "best": 2, "days": {"2026-06-26": 3}, "lastDay": "2026-06-26"}}
        r = client.post("/api/state", headers=h, content=json.dumps(body2)).json()
        check("merge: q1 сохранил box=2 (не затёрт)", r["state"]["srs"]["q1"]["box"] == 2)
        check("merge: q2 добавлен", r["state"]["srs"]["q2"]["box"] == 0)
        check("merge: streak=max(4,2)=4", r["state"]["progress"]["streak"] == 4)
        check("merge: days объединены", set(r["state"]["progress"]["days"]) == {"2026-06-25", "2026-06-26"})

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


if __name__ == "__main__":
    test_auth()
    test_merge_srs()
    test_merge_progress()
    test_endpoints()
    test_attempts()
    test_rate_limit()
    if fails:
        print(f"\nAPI TESTS: {fails} провал(ов)")
        sys.exit(1)
    print("\nAPI TESTS OK")
