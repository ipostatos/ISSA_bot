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
#   BASE=https://issa-46-224-220-94.sslip.io bash deploy/smoke.sh
#
# Не печатает BOT_TOKEN / initData. Код выхода ≠0, если хоть одна проверка упала.
set -uo pipefail

# По умолчанию бьёмся в локальный uvicorn (за Caddy) + статику на том же хосте.
API_BASE="${API_BASE:-http://127.0.0.1:4100}"
WEB_BASE="${BASE:-https://issa-46-224-220-94.sslip.io}"

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

echo "== Статика ($WEB_BASE) =="
check "home 200"               200 "$WEB_BASE/"
check "quiz 200"               200 "$WEB_BASE/quiz.html"

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
