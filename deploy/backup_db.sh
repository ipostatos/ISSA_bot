#!/usr/bin/env bash
# Резервная копия базы синхронизации (api/state.db).
#
# Использует `sqlite3 .backup` — безопасный онлайн-бэкап: корректно работает с
# WAL-режимом и не мешает живому API (в отличие от простого cp файла .db).
#
# Запускать ОТ ПОЛЬЗОВАТЕЛЯ issa (не через sudo): каталог бэкапов принадлежит issa,
# и смешивать владельцев файлов в нём нельзя — иначе ротация от другой учётки упрётся
# в права.
#
# Запуск вручную:        sudo -u issa bash /opt/issa-bot/deploy/backup_db.sh
# По расписанию (cron):  crontab -u issa -e →  0 4 * * *  bash /opt/issa-bot/deploy/backup_db.sh
#
# Каталог назначения — ВНЕ рабочего дерева git (иначе один `git add -A` опубликует
# базу всех пользователей). Переопределяется переменной ISSA_BACKUP_DIR.
# Каталог должен существовать и принадлежать issa — создаётся один раз от root:
#   sudo install -d -o issa -g issa -m 700 /var/backups/issa
#
# Хранит последние KEEP копий, старые удаляет. Не печатает секретов.
set -euo pipefail

APP_DIR=/opt/issa-bot
DB="${ISSA_API_DB:-$APP_DIR/api/state.db}"
BACKUP_DIR="${ISSA_BACKUP_DIR:-/var/backups/issa}"
KEEP=14                          # сколько копий держим (≈2 недели при ежедневном)

# Снимки БД содержат PII → создаём их сразу без прав для группы и остальных.
umask 077

if [ ! -f "$DB" ]; then
  echo "backup_db: БД не найдена: $DB (ещё не создавалась?) — нечего бэкапить."
  exit 0
fi

# Каталог не создаём «молча через sudo»: от учётки issa mkdir в /var/backups упрётся
# в права, и цепочка бэкапов тихо оборвётся. Лучше внятно упасть с инструкцией.
if [ ! -d "$BACKUP_DIR" ]; then
  if ! mkdir -p "$BACKUP_DIR" 2>/dev/null; then
    echo "backup_db: каталог бэкапов не существует и создать его нельзя: $BACKUP_DIR" >&2
    echo "backup_db: создайте его один раз от root:" >&2
    echo "           sudo install -d -o issa -g issa -m 700 $BACKUP_DIR" >&2
    exit 1
  fi
fi
if [ ! -w "$BACKUP_DIR" ]; then
  echo "backup_db: нет прав на запись в $BACKUP_DIR (запущено от $(id -un))." >&2
  echo "backup_db: каталог должен принадлежать issa:" >&2
  echo "           sudo install -d -o issa -g issa -m 700 $BACKUP_DIR" >&2
  exit 1
fi
# 700 на каталог: содержимое видно только владельцу. Не фатально, если chmod не наш.
chmod 700 "$BACKUP_DIR" 2>/dev/null || true
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
# 600 на снимок: в нём Telegram user_id и весь прогресс пользователей.
chmod 600 "$OUT"
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
