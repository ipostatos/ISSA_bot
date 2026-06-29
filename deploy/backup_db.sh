#!/usr/bin/env bash
# Резервная копия базы синхронизации (api/state.db).
#
# Использует `sqlite3 .backup` — безопасный онлайн-бэкап: корректно работает с
# WAL-режимом и не мешает живому API (в отличие от простого cp файла .db).
#
# Запуск вручную:        sudo bash /opt/issa-bot/deploy/backup_db.sh
# По расписанию (cron):  0 4 * * *  bash /opt/issa-bot/deploy/backup_db.sh
#
# Хранит последние KEEP копий, старые удаляет. Не печатает секретов.
set -euo pipefail

APP_DIR=/opt/issa-bot
DB="${ISSA_API_DB:-$APP_DIR/api/state.db}"
BACKUP_DIR="$APP_DIR/api/backups"
KEEP=14                          # сколько копий держим (≈2 недели при ежедневном)

if [ ! -f "$DB" ]; then
  echo "backup_db: БД не найдена: $DB (ещё не создавалась?) — нечего бэкапить."
  exit 0
fi

mkdir -p "$BACKUP_DIR"
# метку времени берём из системы (UTC), без внешних зависимостей
STAMP="$(date -u +%Y%m%d-%H%M%S)"
OUT="$BACKUP_DIR/state-$STAMP.db"

# .backup — атомарный снимок согласованного состояния БД.
# Предпочитаем CLI sqlite3; если его нет — используем Python (он точно есть в venv).
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB" ".backup '$OUT'"
else
  PY="$APP_DIR/.venv/bin/python"
  [ -x "$PY" ] || PY="python3"
  "$PY" - "$DB" "$OUT" <<'PYEOF'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
# ВАЖНО: dst закрываем ЯВНО (не через `with`): `with` коммитит, но не закрывает
# соединение, и файл-копия остаётся неполной до сборки мусора.
s = sqlite3.connect(src)
d = sqlite3.connect(dst)
try:
    s.backup(d)              # онлайн-бэкап средствами sqlite3
finally:
    d.close()
    s.close()
PYEOF
fi
echo "backup_db: создан $OUT ($(du -h "$OUT" | cut -f1))"

# ротация: оставляем последние KEEP по имени (имена сортируются по времени)
mapfile -t all < <(ls -1 "$BACKUP_DIR"/state-*.db 2>/dev/null | sort)
count=${#all[@]}
if [ "$count" -gt "$KEEP" ]; then
  remove=$(( count - KEEP ))
  for f in "${all[@]:0:$remove}"; do
    rm -f "$f"
    echo "backup_db: удалён старый $f"
  done
fi

echo "backup_db: всего копий: $(ls -1 "$BACKUP_DIR"/state-*.db 2>/dev/null | wc -l)"
