# Развёртывание Sync API (Фаза 4)

API синхронизации прогресса между устройствами. Тот же домен Mini App,
путь `/api/*` → локальный `127.0.0.1:4100` (FastAPI/uvicorn + SQLite).

```
https://<домен-mini-app>/        → статика Mini App (как было)
https://<домен-mini-app>/api/*   → этот API (127.0.0.1:4100)
```

> ⚠️ Блоки других сайтов в Caddyfile на этом сервере не трогаем.

Синхронизируются `issa_srs_v1`, `issa_progress_v1`, `issa_pl_progress_v1` и `issa_quiz_session_v1`. Подлинность
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
`<домен-mini-app> { ... }` и добавь в НЕГО (до общей раздачи статики):

```caddy
<домен-mini-app> {
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
> `handle /api/*` первым. Блоки других сайтов оставь без изменений.

Применить:
```bash
sudo caddy validate --config /etc/caddy/Caddyfile     # проверка синтаксиса
sudo systemctl reload caddy
```

## 4. Проверка снаружи

```bash
curl -s https://<домен-mini-app>/api/health   # {"ok":true,"schema":1}
# без initData state должен дать 401:
curl -s -o /dev/null -w "%{http_code}\n" https://<домен-mini-app>/api/state
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

Скрипт делает онлайн-снимок БД (корректно с WAL, не мешает живому API),
проверяет его `PRAGMA integrity_check` (битый снимок удаляется, код выхода 1)
и архивирует файлы бота `progress/` и `sessions/`. Хранит последние 14 копий
каждого вида. Если базы нет, скрипт падает с кодом 1: на боевой машине это
авария (для свежей установки — `ISSA_ALLOW_NO_DB=1`).

Копии складываются в **`/var/backups/issa/`** — вне рабочего дерева git:
`state-<timestamp>.db` (база синхронизации Mini App) и
`files-<timestamp>.tgz` (`progress/` — прогресс в чате бота, `sessions/` —
активные опросы). Раньше каталог был внутри репозитория (`api/backups/`), и один
`git add -A` опубликовал бы базу всех пользователей (Telegram user_id, прогресс).
Путь переопределяется переменной `ISSA_BACKUP_DIR`.

**Шаг 1 (один раз, от root) — создать каталог.** Скрипт его сам не создаёт:
от учётки `issa` запись в `/var/backups` запрещена, и молчаливая ошибка оборвала бы
цепочку бэкапов. Без каталога скрипт падает с этой же подсказкой:

```bash
sudo install -d -o issa -g issa -m 700 /var/backups/issa
```

**Шаг 2 — запускать ОТ issa** (не `sudo bash`): владелец файлов в каталоге должен
быть один, иначе ротация от другой учётки упрётся в права.

```bash
sudo -u issa bash /opt/issa-bot/deploy/backup_db.sh      # разово
# по расписанию — в crontab пользователя issa (crontab -u issa -e):
#   0 4 * * *  bash /opt/issa-bot/deploy/backup_db.sh
```

Права: каталог `700`, каждый снимок `600` — содержимое читает только `issa`.

> Если на сервере уже лежат старые копии в `/opt/issa-bot/api/backups/` — перенести
> и удалить каталог вручную:
> `sudo mv /opt/issa-bot/api/backups/*.db /var/backups/issa/ && sudo chown issa:issa /var/backups/issa/*.db && sudo chmod 600 /var/backups/issa/*.db && sudo rmdir /opt/issa-bot/api/backups`

## Восстановление

Порядок важен: сначала остановить писателей, потом подменять файлы, иначе
живой сервис перезапишет восстановленное. Все шаги, которые пишут в
`/opt/issa-bot`, — от `issa`.

```bash
# 0. Выбрать снимок (самый свежий — последний в списке)
sudo ls -1 /var/backups/issa/

# 1. Остановить писателей
sudo systemctl stop issa-api issa-bot

# 2. Отложить текущее состояние рядом (не удалять: вдруг снимок хуже)
TS=$(date -u +%Y%m%d-%H%M%S)
sudo -u issa mkdir -p /opt/issa-bot/api/pre-restore-$TS
sudo -u issa mv /opt/issa-bot/api/state.db* /opt/issa-bot/api/pre-restore-$TS/ 2>/dev/null || true
sudo -u issa tar -czf /opt/issa-bot/api/pre-restore-$TS/files.tgz -C /opt/issa-bot progress sessions

# 3. База: положить снимок на место. Файлы -wal/-shm от старой базы НЕ
#    возвращать — они относятся к ней, а не к снимку (шаг 2 их уже убрал).
sudo install -o issa -g issa -m 600 /var/backups/issa/state-<timestamp>.db /opt/issa-bot/api/state.db
sudo -u issa python3 -c "import sqlite3; print(sqlite3.connect('/opt/issa-bot/api/state.db').execute('PRAGMA integrity_check').fetchone()[0])"   # ok

# 4. Файлы бота (progress/, sessions/): распаковать поверх, от issa
sudo cat /var/backups/issa/files-<timestamp>.tgz | sudo -u issa tar -xzf - -C /opt/issa-bot

# 5. Запустить и проверить
sudo systemctl start issa-api issa-bot
bash /opt/issa-bot/deploy/smoke.sh
```

Что теряется: всё, что пользователи сделали между снимком и аварией (снимок
ежедневный, 04:00 UTC). Mini App хранит прогресс ещё и на устройстве и при
следующем входе досинхронизирует его на сервер (merge по свежести), так что
для активных пользователей потеря меньше суток обычно затягивается сама.
`pre-restore-<TS>/` удалить вручную, когда убедились, что всё на месте:
там PII.

## Smoke-проверка (после деплоя)

Быстрая проверка, что API и статика живы (health, 401 без initData, отдача
страниц). Запускать после `restart`/`git pull`:

```bash
bash /opt/issa-bot/deploy/smoke.sh                    # локально (127.0.0.1:4100 + домен)
# или против другого домена:
BASE=https://<домен-mini-app> bash /opt/issa-bot/deploy/smoke.sh
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
