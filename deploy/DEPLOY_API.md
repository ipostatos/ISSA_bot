# Развёртывание Sync API (Фаза 4)

API синхронизации прогресса между устройствами. Тот же домен Mini App,
путь `/api/*` → локальный `127.0.0.1:4100` (FastAPI/uvicorn + SQLite).

```
https://issa-46-224-220-94.sslip.io/        → статика Mini App (как было)
https://issa-46-224-220-94.sslip.io/api/*   → этот API (127.0.0.1:4100)
```

> ⚠️ Блок `api.nestingcenter.io` в Caddy НЕ трогаем.

Синхронизируются только `issa_srs_v1` и `issa_progress_v1`. Подлинность
пользователя — по Telegram `initData` (HMAC), `user_id` берётся только оттуда.
BOT_TOKEN — из общего `/opt/issa-bot/.env`.

---

## 1. Код и зависимости

```bash
cd /opt/issa-bot
sudo -u issa git pull --ff-only
# поставить зависимости API в то же venv, что у бота
sudo -u issa /opt/issa-bot/.venv/bin/pip install -r api/requirements.txt
```

## 2. systemd-сервис

```bash
sudo cp /opt/issa-bot/deploy/issa-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now issa-api
sudo systemctl status issa-api --no-pager     # должно быть active (running)
# локальная проверка:
curl -s http://127.0.0.1:4100/api/health       # {"ok":true,"schema":1}
```

## 3. Caddy — добавить маршрут /api/* в СУЩЕСТВУЮЩИЙ блок Mini App

Открой Caddyfile (обычно `/etc/caddy/Caddyfile`). Найди блок сайта
`issa-46-224-220-94.sslip.io { ... }` и добавь в НЕГО (до общей раздачи статики):

```caddy
issa-46-224-220-94.sslip.io {
    # ── НОВОЕ: API синхронизации ──
    handle /api/* {
        reverse_proxy 127.0.0.1:4100
    }

    # ── существующая раздача статики Mini App (оставить как было) ──
    root * /opt/issa-bot/miniapp
    file_server
}
```

> Важно: `handle /api/*` должен идти ВЫШЕ `file_server`, иначе статика перехватит
> запросы. Если у тебя уже структура с `handle`/`route` — просто добавь блок
> `handle /api/*` первым. Блок `api.nestingcenter.io` оставь без изменений.

Применить:
```bash
sudo caddy validate --config /etc/caddy/Caddyfile     # проверка синтаксиса
sudo systemctl reload caddy
```

## 4. Проверка снаружи

```bash
curl -s https://issa-46-224-220-94.sslip.io/api/health   # {"ok":true,"schema":1}
# без initData state должен дать 401:
curl -s -o /dev/null -w "%{http_code}\n" https://issa-46-224-220-94.sslip.io/api/state
```

Затем переоткрой Mini App на двух устройствах под одним аккаунтом Telegram:
ответь на вопросы на одном → на другом счётчик «Повторить» и готовность подтянутся.

---

## Обновление API

```bash
cd /opt/issa-bot && sudo -u issa git pull --ff-only
sudo -u issa /opt/issa-bot/.venv/bin/pip install -r api/requirements.txt   # если менялись зависимости
sudo systemctl restart issa-api
```

## Бэкап

Скрипт делает онлайн-снимок БД (корректно с WAL, не мешает живому API) и
ротирует копии (хранит последние 14):

```bash
sudo bash /opt/issa-bot/deploy/backup_db.sh          # разово
# по расписанию — добавить в crontab пользователя issa:
#   0 4 * * *  bash /opt/issa-bot/deploy/backup_db.sh
```

Копии складываются в `/opt/issa-bot/api/backups/state-<timestamp>.db`.

## Smoke-проверка (после деплоя)

Быстрая проверка, что API и статика живы (health, 401 без initData, отдача
страниц). Запускать после `restart`/`git pull`:

```bash
bash /opt/issa-bot/deploy/smoke.sh                    # локально (127.0.0.1:4100 + домен)
# или против другого домена:
BASE=https://issa-46-224-220-94.sslip.io bash /opt/issa-bot/deploy/smoke.sh
```

Код выхода ≠0, если хоть одна проверка упала. Токены/initData не печатаются.

## Диагностика

```bash
sudo journalctl -u issa-api -n 50 --no-pager     # логи API
sudo systemctl status issa-api --no-pager
```

- `401 invalid initData` снаружи при открытии из Telegram — проверь, что
  BOT_TOKEN в `.env` совпадает с токеном бота (initData подписан им).
- `500 no BOT_TOKEN` — EnvironmentFile не подхватился; проверь путь к `.env`.
- Sync молчит, всё работает локально — это штатный фолбэк (нет сети/initData).
