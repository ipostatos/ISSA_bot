#!/usr/bin/env bash
# Обновление бота на сервере: подтянуть код из git и перезапустить.
# Запуск:  sudo bash /opt/issa-bot/deploy/update.sh
set -euo pipefail

APP_DIR=/opt/issa-bot
SERVICE=issa-bot

cd "$APP_DIR"
echo "→ git pull"
sudo -u issa git pull --ff-only

echo "→ обновление зависимостей"
"$APP_DIR/.venv/bin/pip" install -q -r requirements.txt

echo "→ перезапуск сервиса"
systemctl restart "$SERVICE"
sleep 2
systemctl --no-pager status "$SERVICE" | head -5
echo "✅ готово"
