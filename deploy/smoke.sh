#!/usr/bin/env bash
# Production smoke-check: быстрая проверка, что боевой API и статика живы.
#
# Покрывает чек-лист «Этап 0»:
#   • /api/health отвечает 200
#   • /api/state без initData → 401 (auth обязателен)
#   • /api/attempts без initData → 401
#   • статика Mini App отдаётся (home → 200)
#
# Запуск на сервере (локально, без внешнего трафика):
#   bash /opt/issa-bot/deploy/smoke.sh
# Или против боевого домена:
#   BASE=https://<ваш-домен> bash deploy/smoke.sh
#
# Не печатает BOT_TOKEN / initData. Код выхода ≠0, если хоть одна проверка упала.
set -uo pipefail

# По умолчанию бьёмся в локальный uvicorn (за Caddy) + статику на том же хосте.
# Адреса берём из окружения (хост не хардкодим). API локальный по умолчанию;
# WEB_BASE для проверки статики задаётся через BASE=… (см. шапку). Если не задан —
# статику пропускаем, проверяем только API.
API_BASE="${API_BASE:-http://127.0.0.1:4100}"
WEB_BASE="${BASE:-}"

fails=0
check() {  # check "имя" ожидаемый_код URL
  local name="$1" want="$2" url="$3"
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" 2>/dev/null || echo 000)"
  if [ "$code" = "$want" ]; then
    echo "  OK  $name ($code)"
  else
    echo "  FAIL $name — ожидал $want, получил $code  [$url]"
    fails=$((fails + 1))
  fi
}

echo "== API ($API_BASE) =="
check "health 200"              200 "$API_BASE/api/health"
check "state без initData 401"  401 "$API_BASE/api/state"
check "attempts без initData 401" 401 "$API_BASE/api/attempts"

if [ -n "$WEB_BASE" ]; then
  echo "== Статика ($WEB_BASE) =="
  check "home 200"               200 "$WEB_BASE/"
  check "quiz 200"               200 "$WEB_BASE/quiz.html"
  check "reader 200"             200 "$WEB_BASE/reader.html"
  check "weather 200"            200 "$WEB_BASE/weather.html"
else
  echo "== Статика по HTTP — пропущена (задай BASE=https://… для проверки) =="
fi

# Опубликованные файлы на диске (DST — каталог раздачи Caddy). Ловит «страница
# есть, а то, что она грузит, не скопировано»: книги каталога, pdf.js, Leaflet,
# данные экзаменов. Книги берём из самого каталога book.html, а не из списка
# здесь — добавил книгу в каталог, забыл положить PDF → смоук красный.
DST="${DST:-/opt/issa-bot/miniapp}"
if [ -d "$DST" ]; then
  echo "== Опубликованные файлы ($DST) =="
  need() {  # need "файл относительно DST"
    if [ -s "$DST/$1" ]; then
      echo "  OK  $1"
    else
      echo "  FAIL $1 — нет или пустой"
      fails=$((fails + 1))
    fi
  }
  for f in index.html quiz.html book.html reader.html weather.html exam_pl.html \
           quiz_data.js zeglarz_data.js sternik_data.js \
           vendor/pdfjs/pdf.min.js vendor/pdfjs/pdf.worker.min.js \
           vendor/leaflet/leaflet.js vendor/leaflet/leaflet.css; do
    need "$f"
  done
  books="$(grep -oE 'file: *"[^"]+\.pdf"' "$DST/book.html" 2>/dev/null | sed -E 's/.*"([^"]+)"/\1/' || true)"
  if [ -z "$books" ]; then
    echo "  FAIL каталог книг пуст или не читается ($DST/book.html)"
    fails=$((fails + 1))
  fi
  for b in $books; do need "$b"; done
else
  echo "== Опубликованные файлы — пропущено ($DST нет) =="
fi

# health должен содержать ok:true (контентная проверка, без секретов)
body="$(curl -s --max-time 10 "$API_BASE/api/health" 2>/dev/null || true)"
case "$body" in
  *'"ok":true'*) echo "  OK  health тело содержит ok:true" ;;
  *)             echo "  FAIL health тело без ok:true"; fails=$((fails + 1)) ;;
esac

echo
if [ "$fails" -eq 0 ]; then
  echo "SMOKE OK — боевое состояние живо."
  exit 0
fi
echo "SMOKE: провалов — $fails"
exit 1
