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

import contextlib
import json
import logging
import os
import sqlite3
import time
from collections.abc import Iterator
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("issa-api")

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

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


def init_db() -> None:
    """Создать схему один раз (при старте приложения, см. lifespan).

    Раньше DDL выполнялся в db() на КАЖДЫЙ запрос — лишняя дисковая нагрузка и
    TTFB. Теперь — единожды.
    """
    with contextlib.closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")      # устойчивее к параллельным запросам
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
        conn.commit()


@contextlib.contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    """Соединение с БД на время запроса с ГАРАНТИРОВАННЫМ закрытием.

    Раньше использовался `with sqlite3.connect(...) as conn` — он коммитит, но
    НЕ закрывает соединение (оно висит до сборки мусора → при нагрузке
    «database is locked» / «too many open files»). Здесь try/finally закрывает
    всегда; commit — при успешном выходе, rollback — при исключении.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


HISTORY_LIMIT = 100      # сколько последних попыток храним/отдаём на пользователя


class AttemptIn(BaseModel):
    """Тело POST /api/attempts. Строгая валидация типов и границ.

    Раньше поля приводились через int(...) вручную — мусорный тип ("abc")
    ронял запрос 500-й. Теперь Pydantic отвергает невалидный ввод как 422.
    """
    model_config = {"extra": "ignore"}            # лишние поля игнорируем, не падаем

    total:   int = Field(ge=1, le=1000)           # вопросов в попытке (обязателен, ≥1)
    correct: int = Field(default=0, ge=0, le=1000)
    pct:     int = Field(default=0, ge=0, le=100)
    secs:    int = Field(default=0, ge=0, le=24 * 3600)   # ≤ сутки
    ts:      int = Field(default=0, ge=0)         # 0 → проставим now на сервере
    mode:    str = Field(default="?", max_length=40)


def add_attempt(user_id: int, a: AttemptIn) -> None:
    now = int(time.time())
    with get_db() as conn:
        conn.execute(
            """INSERT INTO attempts(user_id, ts, mode, total, correct, pct, secs)
               VALUES(?,?,?,?,?,?,?)""",
            (user_id,
             a.ts or now,
             a.mode[:40],
             a.total,
             a.correct,
             a.pct,
             a.secs),
        )
        # держим только последние HISTORY_LIMIT записей пользователя
        conn.execute(
            """DELETE FROM attempts WHERE user_id=? AND id NOT IN (
                 SELECT id FROM attempts WHERE user_id=? ORDER BY ts DESC LIMIT ?
               )""",
            (user_id, user_id, HISTORY_LIMIT),
        )


def list_attempts(user_id: int, limit: int = HISTORY_LIMIT) -> list:
    with get_db() as conn:
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
    with get_db() as conn:
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
    with get_db() as conn:
        conn.execute(
            """INSERT INTO state(user_id, srs, progress, schema_version, created_at, updated_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 srs=excluded.srs, progress=excluded.progress,
                 schema_version=excluded.schema_version, updated_at=excluded.updated_at""",
            (user_id, srs, prog, SCHEMA_VERSION, now, now),
        )


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()          # схема создаётся один раз при старте, а не на каждый запрос
    yield


app = FastAPI(title="ISSA Trainer Sync API", docs_url=None, redoc_url=None,
              lifespan=lifespan)


# ── простой rate-limiter в памяти (без внешних зависимостей) ──
# Скользящее окно на пользователя. Настраивается через env:
#   ISSA_RATE_MAX   — запросов в окне (по умолчанию 60)
#   ISSA_RATE_WINDOW — длина окна в секундах (по умолчанию 60)
# 0 в любом из них отключает лимит. Состояние per-process (одного uvicorn-воркера
# хватает для пилота; для масштаба — вынести в Redis).
RATE_MAX = int(os.environ.get("ISSA_RATE_MAX", "60"))
RATE_WINDOW = int(os.environ.get("ISSA_RATE_WINDOW", "60"))
_rate_hits: dict[int, list[float]] = {}


def _check_rate(user_id: int) -> None:
    if RATE_MAX <= 0 or RATE_WINDOW <= 0:
        return                                  # лимит отключён
    now = time.time()
    hits = _rate_hits.get(user_id)
    if hits is None:
        hits = _rate_hits[user_id] = []
    cutoff = now - RATE_WINDOW
    # выкидываем устаревшие отметки, считаем оставшиеся в окне
    hits[:] = [t for t in hits if t > cutoff]
    if len(hits) >= RATE_MAX:
        retry = max(1, int(hits[0] + RATE_WINDOW - now))
        log.warning("rate limit hit: user=%s (%d/%ds), retry-after=%ds",
                    user_id, RATE_MAX, RATE_WINDOW, retry)
        raise HTTPException(429, "rate limit exceeded",
                            headers={"Retry-After": str(retry)})
    hits.append(now)
    # лёгкая защита от роста словаря: периодически чистим пустые записи
    if len(_rate_hits) > 5000:
        for uid in [u for u, h in _rate_hits.items() if not h or h[-1] < cutoff]:
            _rate_hits.pop(uid, None)


def _auth(init_data: str | None) -> int:
    if not BOT_TOKEN:
        log.error("auth failed: BOT_TOKEN not configured")
        raise HTTPException(500, "server misconfigured: no BOT_TOKEN")
    if not init_data:
        log.info("auth 401: missing initData")        # сам initData НЕ логируем
        raise HTTPException(401, "missing initData")
    try:
        info = verify_init_data(init_data, BOT_TOKEN)
    except InitDataError as e:
        log.info("auth 401: %s", e)                   # причина без секретов
        raise HTTPException(401, f"invalid initData: {e}")
    user_id = info["user_id"]
    _check_rate(user_id)        # лимит после успешной auth (per-user)
    return user_id


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
    if not isinstance(a, dict):
        raise HTTPException(422, "expected object")
    try:
        attempt = AttemptIn.model_validate(a)
    except ValidationError as e:
        raise HTTPException(422, f"invalid attempt: {e.errors()[0]['msg']}")
    add_attempt(user_id, attempt)
    return {"ok": True, "attempts": list_attempts(user_id)}


# ── благодарность автору: ссылка на счёт Telegram Stars ──
# Mini App просит invoice-ссылку → открывает её через tg.openInvoice() ПРЯМО в
# окне (без ухода в чат). Ссылку создаёт Telegram методом createInvoiceLink;
# оплату (pre_checkout / successful_payment) обрабатывает БОТ, не API.
DONATE_AMOUNTS = {50, 100, 300}   # допустимые суммы в звёздах (совпадают с ботом)


class InvoiceIn(BaseModel):
    amount: int = Field(..., ge=1, le=100000)


@app.post("/api/invoice")
async def create_invoice(
    request: Request,
    x_init_data: str | None = Header(default=None, alias="X-Init-Data"),
):
    _auth(x_init_data)   # аутентификация обязательна, user_id тут не нужен
    if not BOT_TOKEN:
        raise HTTPException(500, "server misconfigured: no BOT_TOKEN")
    raw = await request.body()
    if len(raw) > 1024:
        raise HTTPException(413, "payload too large")
    try:
        body = InvoiceIn.model_validate_json(raw or b"{}")
    except ValidationError:
        raise HTTPException(422, "invalid amount")
    amount = body.amount
    if amount not in DONATE_AMOUNTS:
        raise HTTPException(422, "amount not allowed")

    import httpx
    payload = {
        "title": "Поддержка ISSA Trainer",
        "description": "Благодарность автору тренажёра. Спасибо за поддержку! ⚓",
        "payload": f"donate_{amount}",
        "currency": "XTR",
        "prices": [{"label": f"{amount} Stars", "amount": amount}],
    }
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createInvoiceLink"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
        data = r.json()
    except Exception as e:  # сеть/парсинг
        log.error("createInvoiceLink failed: %s", type(e).__name__)
        raise HTTPException(502, "telegram unreachable")
    if not data.get("ok"):
        log.error("createInvoiceLink not ok: %s", data.get("description"))
        raise HTTPException(502, "invoice creation failed")
    return {"ok": True, "link": data["result"]}


# CORS: домен Mini App берётся из окружения (ISSA_API_ORIGIN), хост не хардкодим.
# За Caddy запросы same-origin и CORS не нужен — поэтому если переменная не задана,
# заголовки CORS просто не добавляются (безопасный дефолт без привязки к серверу).
ALLOWED_ORIGIN = os.environ.get("ISSA_API_ORIGIN", "").strip()


@app.middleware("http")
async def cors_and_guard(request: Request, call_next):
    if request.method == "OPTIONS":
        return JSONResponse({}, headers=_cors_headers())
    resp = await call_next(request)
    for k, v in _cors_headers().items():
        resp.headers[k] = v
    return resp


def _cors_headers() -> dict:
    if not ALLOWED_ORIGIN:
        return {}      # same-origin за Caddy — CORS-заголовки не требуются
    return {
        "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
        "Access-Control-Allow-Headers": "Content-Type, X-Init-Data",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    }
