"""
Проверка подлинности Telegram WebApp initData (HMAC-SHA256) — чистая функция,
без FastAPI, чтобы тестировать офлайн.

Алгоритм (док. Telegram Bot API, «Validating data received via the Mini App»):
  secret_key   = HMAC_SHA256(key="WebAppData", msg=BOT_TOKEN)
  data_check   = "\n".join(f"{k}={v}" for k,v in sorted(pairs) if k != "hash")
  expected     = hex( HMAC_SHA256(key=secret_key, msg=data_check) )
  valid        = expected == переданный hash

Возвращаем разобранного пользователя ТОЛЬКО если подпись верна. user_id берём
исключительно отсюда, никогда из тела запроса.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


class InitDataError(Exception):
    pass


def verify_init_data(init_data: str, bot_token: str, max_age_sec: int = 86400) -> dict:
    """Проверяет initData и возвращает {'user_id': int, 'user': {...}, 'auth_date': int}.

    Бросает InitDataError при любой проблеме (нет подписи, не сходится, протухло).
    """
    if not init_data or not bot_token:
        raise InitDataError("empty init_data or bot_token")

    # parse_qsl сохраняет порядок и декодирует проценты; не выкидываем пустые значения
    pairs = parse_qsl(init_data, keep_blank_values=True)
    data = dict(pairs)

    received_hash = data.pop("hash", None)
    if not received_hash:
        raise InitDataError("no hash in init_data")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, received_hash):
        raise InitDataError("hash mismatch")

    # защита от replay: auth_date не должен быть слишком старым
    auth_date = int(data.get("auth_date", "0") or "0")
    if max_age_sec and auth_date and (time.time() - auth_date) > max_age_sec:
        raise InitDataError("init_data expired")

    user_raw = data.get("user")
    if not user_raw:
        raise InitDataError("no user in init_data")
    try:
        user = json.loads(user_raw)
        user_id = int(user["id"])
    except (ValueError, KeyError, TypeError) as e:
        raise InitDataError(f"bad user payload: {e}")

    return {"user_id": user_id, "user": user, "auth_date": auth_date}


def build_init_data(bot_token: str, user: dict, auth_date: int | None = None) -> str:
    """Сформировать ВАЛИДНЫЙ initData (для тестов) — тем же алгоритмом."""
    if auth_date is None:
        auth_date = int(time.time())
    fields = {"auth_date": str(auth_date), "user": json.dumps(user, separators=(",", ":"))}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    h = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    from urllib.parse import urlencode
    return urlencode({**fields, "hash": h})
