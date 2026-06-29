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

echo "→ перегенерируем данные (вопросы, конспект, задачи, словарь)"
"$APP_DIR/.venv/bin/python" "$SRC/build_quiz_data.py"
"$APP_DIR/.venv/bin/python" "$SRC/build_konspekt_data.py"
"$APP_DIR/.venv/bin/python" "$SRC/build_tasks_data.py"
"$APP_DIR/.venv/bin/python" "$SRC/build_glossary_data.py"
"$APP_DIR/.venv/bin/python" "$SRC/build_content_data.py"

echo "→ публикуем страницы в $DST"
mkdir -p "$DST"
cp -f "$SRC/home.html"       "$DST/index.html"   # стартовый экран — на корень
cp -f "$SRC/quiz.html"       "$DST/quiz.html"
cp -f "$SRC/index.html"      "$DST/calc.html"    # калькулятор под calc.html
cp -f "$SRC/konspekt.html"   "$DST/konspekt.html"
cp -f "$SRC/tasks.html"      "$DST/tasks.html"
cp -f "$SRC/glossary.html"   "$DST/glossary.html"
cp -f "$SRC/navtasks.html"   "$DST/navtasks.html"
cp -f "$SRC/cheatsheet.html" "$DST/cheatsheet.html"
cp -f "$SRC/book.html"       "$DST/book.html"
cp -f "$SRC/about.html"      "$DST/about.html"    # экран «О банке» (прозрачность)
cp -f "$SRC/profile.html"    "$DST/profile.html"  # профиль и достижения
cp -f "$SRC/history.html"    "$DST/history.html"  # история прохождений
cp -f "$SRC/reader.html"     "$DST/reader.html"   # встроенный PDF-просмотрщик
cp -f "$SRC/nav.js"          "$DST/nav.js"        # общая навигация (BackButton)
cp -f "$SRC/lightbox.js"     "$DST/lightbox.js"   # зум картинок
cp -f "$SRC/srs.js"          "$DST/srs.js"        # интервальное повторение (SRS)
cp -f "$SRC/progress.js"     "$DST/progress.js"   # мотивация: готовность/цель/streak
cp -f "$SRC/sync.js"         "$DST/sync.js"       # синхрон прогресса через /api/state
cp -f "$SRC/heatmap.js"      "$DST/heatmap.js"    # heatmap активности на дашборде
cp -f "$SRC/badges.js"       "$DST/badges.js"     # достижения (бейджи)
cp -f "$SRC/icons.js"        "$DST/icons.js"      # SVG-иконки (Lucide, ISC)
cp -f "$SRC/theme.css"       "$DST/theme.css"     # единая дизайн-система
cp -f "$SRC/quiz_data.js"     "$DST/quiz_data.js"
cp -f "$SRC/konspekt_data.js" "$DST/konspekt_data.js"
cp -f "$SRC/tasks_data.js"    "$DST/tasks_data.js"
cp -f "$SRC/glossary_data.js" "$DST/glossary_data.js"
cp -f "$SRC/content_data.js"  "$DST/content_data.js"

echo "→ копируем PDF-книги (если есть)"
# Книги кладём в $SRC/books/ под латинскими именами (book.pdf / studbook.pdf / toghill.pdf).
# На Linux важно: без пробелов и кириллицы в именах, иначе Caddy не отдаст файл.
BOOKS_SRC="$SRC/books"
for f in book.pdf studbook.pdf toghill.pdf; do
  if [ -f "$BOOKS_SRC/$f" ]; then
    cp -f "$BOOKS_SRC/$f" "$DST/$f" && echo "  $f"
  elif [ -f "$SRC/$f" ]; then           # запасной путь: файл лежит прямо в webapp/
    cp -f "$SRC/$f" "$DST/$f" && echo "  $f (из webapp/)"
  else
    echo "  ($f нет — положи в $BOOKS_SRC/)"
  fi
done

echo "→ копируем pdf.js (локальный просмотрщик, без CDN)"
mkdir -p "$DST/vendor/pdfjs"
cp -f "$SRC/vendor/pdfjs/pdf.min.js"        "$DST/vendor/pdfjs/" 2>/dev/null && echo "  pdf.min.js"
cp -f "$SRC/vendor/pdfjs/pdf.worker.min.js" "$DST/vendor/pdfjs/" 2>/dev/null && echo "  pdf.worker.min.js"

echo "→ копируем картинки (схемы конспекта)"
mkdir -p "$DST/images"
cp -f "$APP_DIR/images/"*.png "$APP_DIR/images/"*.jpg "$DST/images/" 2>/dev/null || true

echo "✅ опубликовано:"
ls -1 "$DST"
echo
echo "Открой https://issa-46-224-220-94.sslip.io — должен быть стартовый экран."
