#!/usr/bin/env bash
# Опубликовать Mini App: скопировать статические страницы туда, откуда их
# отдаёт Caddy (заглушку заменяем на настоящее приложение).
#
# Запуск на сервере:  sudo bash /opt/issa-bot/deploy/update_webapp.sh
#
# ПРАВИЛО ВЛАДЕНИЯ (волна 0, находка H2). Root нужен ТОЛЬКО для публикации в
# системные каталоги раздачи (/opt/issa-bot/miniapp, /opt/issa-site) — это
# копирование, туда пишет Caddy-хост. Всё, что трогает /opt/issa-bot (git pull,
# pip, генерация данных, кэш озвучки), выполняется ОТ issa через as_issa().
# Иначе в дереве и в .venv появляются файлы root:root, и следующий деплой от
# issa падает по правам, а бот (он работает от issa) теряет доступ к своим же
# данным. Проверка после деплоя:
#   sudo find /opt/issa-bot/.venv ! -user issa | wc -l     # должно быть 0
#
# Структура (статика, без сборки — никакого npm/vite/dist не нужно):
#   webapp/home.html   — стартовый экран (выбор: Тесты / Калькулятор)
#   webapp/quiz.html   — тесты
#   webapp/index.html  — морской калькулятор
#   webapp/quiz_data.js — вопросы (генерируются из questions.json)
set -euo pipefail

# Всё тело — в функции: скрипт обновляет сам себя через git pull, а bash
# дочитывает файл по ходу выполнения. Без обёртки после pull исполняется
# смесь старой и новой версий (2026-07-15 так потерялись cp-строки dock/i18n).
main() {

APP_DIR=/opt/issa-bot
SRC="$APP_DIR/webapp"
DST=/opt/issa-bot/miniapp        # каталог, который раздаёт Caddy (root в Caddyfile)
PY="$APP_DIR/.venv/bin/python"

# Единая точка «выполнить от issa». Всё, что пишет внутрь $APP_DIR, идёт через неё.
as_issa() { sudo -u issa "$@"; }

echo "→ обновляем код из git (от issa)"
# Фолбэка `|| git pull` (то есть «не вышло от issa — сделаем от root») здесь
# больше нет: он тихо превращал сбой прав в деплой от root и оставлял в дереве
# файлы root:root. Если pull от issa не проходит — деплой обязан остановиться.
as_issa git -C "$APP_DIR" pull --ff-only

# Предполётная проверка владения: после старых деплоев от root в дереве могли
# остаться файлы root:root — тогда шаги ниже (они идут от issa) упадут по правам.
# Сами ничего не чиним и деплой не валим: печатаем ровно ту команду, которой лечится.
BAD_OWNER="$(find "$APP_DIR/webapp" "$APP_DIR/.venv" ! -user issa -print -quit 2>/dev/null || true)"
if [ -n "$BAD_OWNER" ]; then
  echo "  ⚠ в дереве есть файлы не от issa (например: $BAD_OWNER)"
  echo "    почини один раз:  sudo chown -R issa:issa $APP_DIR"
fi

# Каталоги рантайм-состояния бота (в .gitignore, git их не приносит). Создаём
# заранее с владельцем issa: иначе ReadWritePaths в issa-bot.service указывает
# на несуществующий путь → systemd падает с 226/NAMESPACE при чистом деплое.
echo "→ гарантируем каталоги состояния бота (progress/, sessions/)"
as_issa mkdir -p "$APP_DIR/progress" "$APP_DIR/sessions"

echo "→ перегенерируем данные (вопросы, конспект, задачи, словарь) — от issa"
# Скрипты пишут *_data.js прямо в репозиторий ($SRC). От root они оставляли бы
# там файлы root:root, после чего следующий `git pull` от issa падал бы.
as_issa "$PY" "$SRC/build_quiz_data.py"
as_issa "$PY" "$SRC/build_konspekt_data.py"
as_issa "$PY" "$SRC/build_tasks_data.py"
as_issa "$PY" "$SRC/build_glossary_data.py"
as_issa "$PY" "$SRC/build_content_data.py"
as_issa "$PY" "$SRC/build_zeglarz_data.py"      # польская лицензия Żeglarz
as_issa "$PY" "$SRC/build_sternik_data.py"      # польская лицензия Sternik
as_issa "$PY" "$SRC/build_konspekt_pl_data.py"  # польский конспект (Żeglarz+Sternik)

echo "→ нейроозвучка (edge-tts): генерируем недостающие фразы"
# Пакет здесь БОЛЬШЕ НЕ СТАВИМ. Раньше на каждом деплое выполнялось
# `pip install -q edge-tts` от root: свежая версия с PyPI прямо в root на
# боевой машине, плюс файлы root:root в .venv. Теперь версия запинена в
# requirements.txt (edge-tts==7.2.8) и ставится один раз через deploy/update.sh.
# Отсутствие пакета деплой НЕ валит — плеер дочитает системным синтезом.
if as_issa "$PY" -c 'import edge_tts' 2>/dev/null; then
  as_issa "$PY" "$SRC/build_audio_tts.py" --cache "$APP_DIR/tts_cache" \
    || echo "  (генерация неполная — плеер дочитает системным голосом)"
else
  echo "  edge-tts нет в $APP_DIR/.venv — озвучка пропущена, плеер читает системным голосом."
  echo "  поставить один раз:  sudo -u issa $APP_DIR/.venv/bin/pip install -r $APP_DIR/requirements.txt"
fi

# Ниже — публикация в системный каталог раздачи ($DST). Здесь root уместен:
# это копирование наружу, в дерево, которым владеет хост, а не запись в $APP_DIR.
mkdir -p "$DST/tts"
if command -v rsync >/dev/null; then
  rsync -a --delete "$APP_DIR/tts_cache/" "$DST/tts/"
else
  cp -f "$APP_DIR/tts_cache/"*.mp3 "$DST/tts/" 2>/dev/null || true
fi
[ -f "$SRC/tts_index.js" ] && cp -f "$SRC/tts_index.js" "$DST/tts_index.js"

echo "→ публикуем страницы в $DST"
mkdir -p "$DST"
cp -f "$SRC/robots.txt"      "$DST/robots.txt"   # anti-AI-scraping + TDM opt-out
cp -f "$APP_DIR/AI-POLICY.md" "$DST/AI-POLICY.md" # политика ИИ (на неё ссылается robots.txt)
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
cp -f "$SRC/exam_pl.html"    "$DST/exam_pl.html"  # польские лицензии (Żeglarz/Sternik)
cp -f "$SRC/konspekt_pl.html" "$DST/konspekt_pl.html"  # польский конспект (разбор ответов)
cp -f "$SRC/weather.html"    "$DST/weather.html"  # BETA: погода (Open-Meteo, без бэкенда)
cp -f "$SRC/lights.html"     "$DST/lights.html"   # бонус: огни судов ночью (COLREG)
cp -f "$SRC/buoys.html"      "$DST/buoys.html"    # бонус: буи IALA (проблески)
cp -f "$SRC/shapes.html"     "$DST/shapes.html"   # бонус: дневные знаки + флаги МСС
cp -f "$SRC/audio.html"      "$DST/audio.html"    # аудио-повторение (Web Speech API)
cp -f "$SRC/dock.html"       "$DST/dock.html"     # бонус: 2D-тренажёр швартовок
cp -f "$SRC/cams.html"       "$DST/cams.html"     # BETA: веб-камеры (HLS gdansk.pl/TASK)
cp -f "$SRC/sw.js"           "$DST/sw.js"          # PWA: офлайн-кэш (service worker)
cp -f "$SRC/manifest.webmanifest" "$DST/manifest.webmanifest" # PWA-манифест
cp -f "$SRC/icon.svg"        "$DST/icon.svg"       # PWA-иконка (компас)
cp -f "$SRC/nav.js"          "$DST/nav.js"        # общая навигация (BackButton) + регистрация SW
cp -f "$SRC/i18n.dict.js"    "$DST/i18n.dict.js"  # словарь интерфейса (RU/PL/UA/EN)
cp -f "$SRC/i18n.js"         "$DST/i18n.js"       # движок i18n (t()/hydrate/пикер языка)
cp -f "$SRC/lightbox.js"     "$DST/lightbox.js"   # зум картинок
cp -f "$SRC/migration.js"    "$DST/migration.js"  # версионирование localStorage (грузится первым)
cp -f "$SRC/srs.js"          "$DST/srs.js"        # интервальное повторение (SRS)
cp -f "$SRC/progress.js"     "$DST/progress.js"   # мотивация: готовность/цель/streak
cp -f "$SRC/pl_progress.js"  "$DST/pl_progress.js" # прогресс польских лицензий (Żeglarz/Sternik)
cp -f "$SRC/sync.js"         "$DST/sync.js"       # синхрон прогресса через /api/state
cp -f "$SRC/heatmap.js"      "$DST/heatmap.js"    # heatmap активности на дашборде
cp -f "$SRC/badges.js"       "$DST/badges.js"     # достижения (бейджи)
cp -f "$SRC/mistakes.js"     "$DST/mistakes.js"   # журнал ошибок (learning loop)
cp -f "$SRC/icons.js"        "$DST/icons.js"      # SVG-иконки (Lucide, ISC)
cp -f "$SRC/theme.css"       "$DST/theme.css"     # единая дизайн-система
cp -f "$SRC/quiz_data.js"     "$DST/quiz_data.js"
cp -f "$SRC/konspekt_data.js" "$DST/konspekt_data.js"
cp -f "$SRC/tasks_data.js"    "$DST/tasks_data.js"
cp -f "$SRC/glossary_data.js" "$DST/glossary_data.js"
cp -f "$SRC/content_data.js"  "$DST/content_data.js"
cp -f "$SRC/zeglarz_data.js"  "$DST/zeglarz_data.js"
cp -f "$SRC/sternik_data.js"  "$DST/sternik_data.js"
cp -f "$SRC/konspekt_pl_data.js" "$DST/konspekt_pl_data.js"
cp -f "$SRC/lights_data.js"   "$DST/lights_data.js"   # огни судов (COLREG)
cp -f "$SRC/buoys_data.js"    "$DST/buoys_data.js"    # буи IALA
cp -f "$SRC/shapes_data.js"   "$DST/shapes_data.js"   # дневные знаки + флаги МСС

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

echo "→ копируем Leaflet (карта ветра, локально; тайлы CARTO — внешние)"
mkdir -p "$DST/vendor/leaflet"
cp -f "$SRC/vendor/leaflet/leaflet.js"  "$DST/vendor/leaflet/" 2>/dev/null && echo "  leaflet.js"
cp -f "$SRC/vendor/leaflet/leaflet.css" "$DST/vendor/leaflet/" 2>/dev/null && echo "  leaflet.css"

echo "→ копируем hls.js (веб-камеры, локально; сам поток — kamera.task.gda.pl)"
mkdir -p "$DST/vendor/hls"
cp -f "$SRC/vendor/hls/hls.light.min.js" "$DST/vendor/hls/" 2>/dev/null && echo "  hls.light.min.js"

echo "→ копируем картинки (схемы конспекта)"
mkdir -p "$DST/images"
cp -f "$APP_DIR/images/"*.png "$APP_DIR/images/"*.jpg "$DST/images/" 2>/dev/null || true

echo "→ копируем фото узлов (images/knots/)"
mkdir -p "$DST/images/knots"
cp -f "$APP_DIR/images/knots/"*.jpg "$DST/images/knots/" 2>/dev/null && echo "  knots: $(ls "$APP_DIR/images/knots/"*.jpg 2>/dev/null | wc -l) фото" || true

echo "→ копируем знаки польских лицензий (images/zj/, images/st/)"
mkdir -p "$DST/images/zj" "$DST/images/st"
cp -f "$SRC/images/zj/"*.png "$DST/images/zj/" 2>/dev/null && echo "  zj: $(ls "$SRC/images/zj/"*.png 2>/dev/null | wc -l) знаков" || true
cp -f "$SRC/images/st/"*.png "$DST/images/st/" 2>/dev/null && echo "  st: $(ls "$SRC/images/st/"*.png 2>/dev/null | wc -l) знаков" || true

echo "→ публикуем промо-сайт (site/ → /opt/issa-site)"
if [ -d "$APP_DIR/site" ]; then
  mkdir -p /opt/issa-site
  cp -rf "$APP_DIR/site/." /opt/issa-site/
fi

echo "✅ опубликовано:"
ls -1 "$DST"
echo
echo "Открой https://<ваш-домен> — должен быть стартовый экран."

}
main "$@"
