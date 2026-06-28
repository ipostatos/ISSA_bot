"""
ISSA Trainer — API синхронизации прогресса между устройствами.

Маршруты (за Caddy на пути /api/*):
  GET  /api/health          — проверка живости
  GET  /api/state           — вернуть состояние пользователя (по initData)
  POST /api/state           — merge(server, incoming) → сохранить → вернуть merged

Безопасность:
  - подлинность пользователя — строго через Telegram initData (HMAC), см. auth.py;
  - user_id берётся ТОЛЬКО из проверенного initData, не из тела;
  - BOT_TOKEN из окружения (общий .env с ботом);
  - лимит размера тела;
  - no blind overwrite — слияние, см. merge.py.

Запуск:  uvicorn api:app --host 127.0.0.1 --port 4100
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from auth import InitDataError, verify_init_data
from merge import merge_state

SCHEMA_VERSION = 1
MAX_BODY = 256 * 1024            # 256 КБ хватает на SRS+progress с запасом
DB_PATH = Path(os.environ.get("ISSA_API_DB", Path(__file__).resolve().parent / "state.db"))


def _bot_token() -> str:
    tok = os.environ.get("BOT_TOKEN", "")
    if not tok:
        # пытаемся прочитать из ../.env (тот же, что у бота)
        env = Path(__file__).resolve().parent.parent / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("BOT_TOKEN="):
                    tok = line.split("=", 1)[1].strip()
                    break
    return tok


BOT_TOKEN = _bot_token()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")          # устойчивее к параллельным запросам
    conn.execute(
        """CREATE TABLE IF NOT EXISTS state(
             user_id        INTEGER PRIMARY KEY,
             srs            TEXT NOT NULL DEFAULT '{}',
             progress       TEXT NOT NULL DEFAULT '{}',
             schema_version INTEGER NOT NULL DEFAULT 1,
             created_at     INTEGER NOT NULL,
             updated_at     INTEGER NOT NULL
           )"""
    )
    # История прохождений (append-only). Отдельно от state — не мёрджится.
    conn.execute(
        """CREATE TABLE IF NOT EXISTS attempts(
             id       INTEGER PRIMARY KEY AUTOINCREMENT,
             user_id  INTEGER NOT NULL,
             ts       INTEGER NOT NULL,   -- когда пройдено (мс или сек, как прислал клиент)
             mode     TEXT NOT NULL,      -- exam | random | review | topic:<...>
             total    INTEGER NOT NULL,
             correct  INTEGER NOT NULL,
             pct      INTEGER NOT NULL,
             secs     INTEGER NOT NULL DEFAULT 0
           )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts(user_id, ts DESC)")
    return conn


HISTORY_LIMIT = 100      # сколько последних попыток храним/отдаём на пользователя


def add_attempt(user_id: int, a: dict) -> None:
    now = int(time.time())
    with db() as conn:
        conn.execute(
            """INSERT INTO attempts(user_id, ts, mode, total, correct, pct, secs)
               VALUES(?,?,?,?,?,?,?)""",
            (user_id,
             int(a.get("ts") or now),
             str(a.get("mode", "?"))[:40],
             int(a.get("total", 0)),
             int(a.get("correct", 0)),
             int(a.get("pct", 0)),
             int(a.get("secs", 0))),
        )
        # держим только последние HISTORY_LIMIT записей пользователя
        conn.execute(
            """DELETE FROM attempts WHERE user_id=? AND id NOT IN (
                 SELECT id FROM attempts WHERE user_id=? ORDER BY ts DESC LIMIT ?
               )""",
            (user_id, user_id, HISTORY_LIMIT),
        )


def list_attempts(user_id: int, limit: int = HISTORY_LIMIT) -> list:
    with db() as conn:
        rows = conn.execute(
            """SELECT ts, mode, total, correct, pct, secs FROM attempts
               WHERE user_id=? ORDER BY ts DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return [
        {"ts": r[0], "mode": r[1], "total": r[2], "correct": r[3], "pct": r[4], "secs": r[5]}
        for r in rows
    ]


def load_state(user_id: int) -> dict:
    with db() as conn:
        row = conn.execute(
            "SELECT srs, progress FROM state WHERE user_id=?", (user_id,)
        ).fetchone()
    if not row:
        return {"srs": {}, "progress": {}}
    try:
        return {"srs": json.loads(row[0] or "{}"), "progress": json.loads(row[1] or "{}")}
    except json.JSONDecodeError:
        return {"srs": {}, "progress": {}}


def save_state(user_id: int, state: dict) -> None:
    now = int(time.time())
    srs = json.dumps(state.get("srs", {}), ensure_ascii=False)
    prog = json.dumps(state.get("progress", {}), ensure_ascii=False)
    with db() as conn:
        conn.execute(
            """INSERT INTO state(user_id, srs, progress, schema_version, created_at, updated_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 srs=excluded.srs, progress=excluded.progress,
                 schema_version=excluded.schema_version, updated_at=excluded.updated_at""",
            (user_id, srs, prog, SCHEMA_VERSION, now, now),
        )


app = FastAPI(title="ISSA Trainer Sync API", docs_url=None, redoc_url=None)


def _auth(init_data: str | None) -> int:
    if not BOT_TOKEN:
        raise HTTPException(500, "server misconfigured: no BOT_TOKEN")
    if not init_data:
        raise HTTPException(401, "missing initData")
    try:
        info = verify_init_data(init_data, BOT_TOKEN)
    except InitDataError as e:
        raise HTTPException(401, f"invalid initData: {e}")
    return info["user_id"]


@app.get("/api/health")
def health():
    return {"ok": True, "schema": SCHEMA_VERSION}


@app.get("/api/state")
def get_state(x_init_data: str | None = Header(default=None, alias="X-Init-Data")):
    user_id = _auth(x_init_data)
    st = load_state(user_id)
    return {"ok": True, "state": st}


@app.post("/api/state")
async def post_state(
    request: Request,
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
):
    user_id = _auth(x_init_data)

    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "payload too large")
    try:
        incoming = json.loads(raw or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(400, "bad json")
    if not isinstance(incoming, dict):
        raise HTTPException(400, "expected object")

    server = load_state(user_id)
    merged = merge_state(server, {"srs": incoming.get("srs"), "progress": incoming.get("progress")})
    save_state(user_id, merged)
    return {"ok": True, "state": merged}


# ── история прохождений (append-only, отдельно от state) ──
@app.get("/api/attempts")
def get_attempts(x_init_data: str | None = Header(default=None, alias="X-Init-Data")):
    user_id = _auth(x_init_data)
    return {"ok": True, "attempts": list_attempts(user_id)}


@app.post("/api/attempts")
async def post_attempt(
    request: Request,
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
):
    user_id = _auth(x_init_data)
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "payload too large")
    try:
        a = json.loads(raw or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(400, "bad json")
    if not isinstance(a, dict) or not a.get("total"):
        raise HTTPException(400, "expected attempt object with total")
    add_attempt(user_id, a)
    return {"ok": True, "attempts": list_attempts(user_id)}


# CORS: разрешаем только домен Mini App (и пусто — same-origin за Caddy не требует CORS,
# но на случай прямых запросов оставляем явный заголовок через middleware).
ALLOWED_ORIGIN = os.environ.get("ISSA_API_ORIGIN", "https://issa-46-224-220-94.sslip.io")


@app.middleware("http")
async def cors_and_guard(request: Request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse({}, headers=_cors_headers())
    resp = await call_next(request)
    for k, v in _cors_headers().items():
        resp.headers[k] = v
    return resp


def _cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Access-Control-Allow-Headers": "Content-Type, X-Init-Data",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    }
