#!/usr/bin/env bash
# Резервная копия состояния: база синхронизации (api/state.db) плюс файлы
# бота progress/ (seen/wrong/статистика чата) и sessions/ (активные опросы).
# До волны D (13.11.2026) бэкапилась только база — прогресс в чате при потере
# диска пропал бы целиком. Восстановление: deploy/DEPLOY_API.md, «Восстановление».
#
# Базу снимает `sqlite3 .backup` — безопасный онлайн-бэкап: корректно работает с
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
# Хранит последние KEEP копий каждого вида, старые удаляет. Не печатает секретов.
# Код выхода ≠0, если снимок не создан или не прошёл проверку — cron это увидит.
set -euo pipefail

APP_DIR="${ISSA_APP_DIR:-/opt/issa-bot}"
DB="${ISSA_API_DB:-$APP_DIR/api/state.db}"
BACKUP_DIR="${ISSA_BACKUP_DIR:-/var/backups/issa}"
KEEP=14                          # сколько копий держим (≈2 недели при ежедневном)

# Снимки содержат PII → создаём их сразу без прав для группы и остальных.
umask 077

PY="$APP_DIR/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

# Нет базы на боевой машине — это авария, а не «нечего делать»: exit 0 здесь
# делал бы cron зелёным, пока бэкапы молча не создаются. Для свежей установки,
# где API ещё ни разу не запускался, задайте ISSA_ALLOW_NO_DB=1.
if [ ! -f "$DB" ] && [ "${ISSA_ALLOW_NO_DB:-0}" != "1" ]; then
  echo "backup_db: БД не найдена: $DB — бэкап НЕ создан (свежая установка: ISSA_ALLOW_NO_DB=1)." >&2
  exit 1
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

# ── 1. База синхронизации ──
if [ -f "$DB" ]; then
  OUT="$BACKUP_DIR/state-$STAMP.db"
  # .backup — атомарный снимок согласованного состояния БД.
  # Предпочитаем CLI sqlite3; если его нет — используем Python (он точно есть в venv).
  # Сбой снятия снимка не должен оставлять в каталоге недописанный файл,
  # похожий на настоящий бэкап.
  snapshot_failed() {
    echo "backup_db: снимок базы не создан (исходник повреждён или занят) — $OUT удалён." >&2
    rm -f "$OUT"
    exit 1
  }
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB" ".backup '$OUT'" || snapshot_failed
  else
    "$PY" - "$DB" "$OUT" <<'SNAP' || snapshot_failed
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
SNAP
  fi
  # 600 на снимок: в нём Telegram user_id и весь прогресс пользователей.
  chmod 600 "$OUT"

  # Снимок, который не открывается, хуже отсутствия снимка: узнаём о нём в день
  # восстановления. Проверяем целостность сразу и битый не оставляем.
  CHECK="$("$PY" - "$OUT" <<'CHK'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
try:
    print(c.execute("PRAGMA integrity_check").fetchone()[0])
finally:
    c.close()
CHK
)" || CHECK="ошибка проверки"
  if [ "$CHECK" != "ok" ]; then
    echo "backup_db: снимок $OUT не прошёл integrity_check: $CHECK — удалён." >&2
    rm -f "$OUT"
    exit 1
  fi
  echo "backup_db: создан $OUT ($(du -h "$OUT" | cut -f1)), integrity_check ok"
else
  echo "backup_db: БД нет, ISSA_ALLOW_NO_DB=1 — базу пропускаю."
fi

# ── 2. Файлы бота: progress/ и sessions/ ──
# JSON, бот пишет их через tmp → replace, поэтому tar читает целые файлы.
# Отсутствующий каталог — не ошибка (свежая установка).
FILES=()
for d in progress sessions; do
  if [ -d "$APP_DIR/$d" ]; then FILES+=("$d"); fi
done
if [ "${#FILES[@]}" -gt 0 ]; then
  FOUT="$BACKUP_DIR/files-$STAMP.tgz"
  tar -czf "$FOUT" -C "$APP_DIR" "${FILES[@]}"
  chmod 600 "$FOUT"
  if ! tar -tzf "$FOUT" >/dev/null; then
    echo "backup_db: архив $FOUT не читается — удалён." >&2
    rm -f "$FOUT"
    exit 1
  fi
  echo "backup_db: создан $FOUT ($(du -h "$FOUT" | cut -f1)): ${FILES[*]}"
fi

# ── 3. Ротация: последние KEEP по имени (имена сортируются по времени) ──
rotate() {  # rotate <префикс> <суффикс>
  local all=() count remove f
  mapfile -t all < <(ls -1 "$BACKUP_DIR"/"$1"-*"$2" 2>/dev/null | sort)
  count=${#all[@]}
  if [ "$count" -gt "$KEEP" ]; then
    remove=$(( count - KEEP ))
    for f in "${all[@]:0:$remove}"; do
      rm -f "$f"
      echo "backup_db: удалён старый $f"
    done
  fi
}
rotate state .db
rotate files .tgz

echo "backup_db: всего копий: базы $(ls -1 "$BACKUP_DIR"/state-*.db 2>/dev/null | wc -l)," \
     "файлов бота $(ls -1 "$BACKUP_DIR"/files-*.tgz 2>/dev/null | wc -l)"
