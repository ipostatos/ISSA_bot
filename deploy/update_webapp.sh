#!/usr/bin/env bash
# Опубликовать Mini App: скопировать статические страницы туда, откуда их
# отдаёт Caddy (заглушку заменяем на настоящее приложение).
#
# Запуск на сервере:  sudo bash /opt/issa-bot/deploy/update_webapp.sh
#
# Структура (статика, без сборки — никакого npm/vite/dist не нужно):
#   webapp/home.html   — стартовый экран (выбор: Тесты / Калькулятор)
#   webapp/quiz.html   — тесты
#   webapp/index.html  — морской калькулятор
#   webapp/quiz_data.js — вопросы (генерируются из questions.json)
set -euo pipefail

APP_DIR=/opt/issa-bot
SRC="$APP_DIR/webapp"
DST=/opt/issa-bot/miniapp        # каталог, который раздаёт Caddy (root в Caddyfile)

echo "→ обновляем код из git"
sudo -u issa git -C "$APP_DIR" pull --ff-only || git -C "$APP_DIR" pull --ff-only

echo "→ перегенерируем quiz_data.js из questions.json"
"$APP_DIR/.venv/bin/python" "$SRC/build_quiz_data.py"

echo "→ публикуем страницы в $DST"
mkdir -p "$DST"
cp -f "$SRC/home.html"  "$DST/index.html"   # стартовый экран — на корень
cp -f "$SRC/quiz.html"  "$DST/quiz.html"
cp -f "$SRC/index.html" "$DST/calc.html"    # калькулятор под calc.html
cp -f "$SRC/quiz_data.js" "$DST/quiz_data.js"

echo "✅ опубликовано:"
ls -1 "$DST"
echo
echo "Открой https://issa-46-224-220-94.sslip.io — должен быть стартовый экран."
