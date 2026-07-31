#!/usr/bin/env bash
# Сторож документации: README не должен снова разъехаться с LICENSE и с
# руководствами по развёртыванию.
#
# Появился не «на всякий случай», а по факту двух реальных расхождений:
#   • README обещал MIT, тогда как LICENSE — all rights reserved. Читатель мог
#     обоснованно счесть код пригодным для коммерческого использования.
#   • README содержал краткий сниппет установки, создававший .venv от root
#     в /opt. В deploy/DEPLOY.md порядок исправили, а копию в README забыли —
#     и она продолжала воспроизводить уже закрытую проблему безопасности.
#
# Запуск:  bash scripts/check_readme.sh
# Код выхода ≠0, если хоть одна проверка не прошла.
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

bad=0
fail() { echo "::error::$*"; bad=1; }

# Интерпретатор для разбора Markdown-блоков. На Linux/CI это python3; на Windows
# `python3` — заглушка из Microsoft Store, которая молча ничего не выполняет,
# поэтому проверяем работоспособность, а не наличие имени.
PY=""
for c in python3 python py; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "pass" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  fail "не найден рабочий Python — проверку сниппетов выполнить нечем"
fi

# ── a) Заявка на MIT ────────────────────────────────────────────────────────
# Ищем именно утверждение о лицензировании, а не любое упоминание слова MIT
# (в тексте может встретиться, например, ссылка на стороннюю библиотеку под MIT).
if grep -nEi '(лицензия|лицензией|под|licen[sc]ed?( under)?)[[:space:]]*\[?MIT' README.md; then
  fail "README заявляет лицензию MIT, тогда как LICENSE — all rights reserved"
fi
if grep -nEi 'open[- ]source' README.md; then
  fail "README называет проект open source, что противоречит LICENSE"
fi

# ── b) Опасный серверный сниппет ────────────────────────────────────────────
# Смотрим на fenced-блок ЦЕЛИКОМ, а не построчно: в исходной ошибке `cd /opt`
# и `python3 -m venv` стояли на РАЗНЫХ строках, и построчный фильтр такую пару
# пропускал (поймано негативным прогоном, а не рассуждением).
# Локальный quick start разработчика правилом не задевается: там нет ни /opt,
# ни systemctl.
[ -n "$PY" ] && { "$PY" - <<'PY' || bad=1
import re, sys

src = open("README.md", encoding="utf-8").read()
blocks = re.findall(r"```[^\n]*\n(.*?)```", src, re.S)
bad = False
for b in blocks:
    server = ("/opt" in b) or ("systemctl" in b)
    installs = re.search(r"(python3? -m venv|\.venv/bin/pip|pip install)", b)
    if server and installs and "sudo -u issa" not in b:
        print("::error::блок README ставит окружение на сервере не от issa "
              "(venv/pip в /opt без sudo -u issa):")
        for line in b.strip().splitlines()[:6]:
            print("    " + line)
        bad = True
sys.exit(1 if bad else 0)
PY
}

# ── c) Markdown-ссылки за пределы репозитория ───────────────────────────────
# Такие ссылки живы только на машине автора: у всех, кто клонировал проект,
# они ведут в никуда (так было с ../_extracted/sources.txt).
for f in README.md SECURITY.md $(find docs -name '*.md' 2>/dev/null); do
  [ -f "$f" ] || continue
  if grep -nE '\]\(\.\./' "$f"; then
    fail "$f содержит Markdown-ссылку за пределы репозитория (начинается с ../)"
  fi
done

# ── d) Обещанные файлы существуют ───────────────────────────────────────────
for f in LICENSE PRIVACY.md SECURITY.md AI-POLICY.md docs/SOURCES.md \
         deploy/DEPLOY.md deploy/DEPLOY_API.md; do
  [ -f "$f" ] || fail "документация ссылается на $f, а файла нет"
done

if [ "$bad" -ne 0 ]; then
  echo "CHECK README: есть замечания"
  exit 1
fi
echo "OK: README согласован с LICENSE и руководствами по развёртыванию"
