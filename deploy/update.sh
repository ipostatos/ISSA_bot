#!/usr/bin/env bash
# Обновление бота на сервере: подтянуть код из git и перезапустить.
# Запуск:  sudo bash /opt/issa-bot/deploy/update.sh
#
# ПРАВИЛО ВЛАДЕНИЯ (волна 0, находка H2). Всё, что пишет в /opt/issa-bot —
# git pull, pip, генерация данных — выполняется ОТ ПОЛЬЗОВАТЕЛЯ issa.
# Root оставлен ровно для одного шага: systemctl.
# Причина: pip от root оставляет в .venv файлы root:root, после чего запуск
# от issa (а бот работает именно от issa) упирается в права, а компрометация
# кода в репозитории даёт root в обход всей systemd-песочницы.
# Проверка на сервере после деплоя:
#   sudo find /opt/issa-bot/.venv ! -user issa | wc -l     # должно быть 0
set -euo pipefail

# Всё тело — в функции: скрипт обновляет сам себя через git pull, а bash
# дочитывает файл по ходу выполнения. Без обёртки после pull исполняется смесь
# старой и новой версий (так 2026-07-15 сломался update_webapp.sh).
main() {

APP_DIR=/opt/issa-bot
SERVICE=issa-bot

cd "$APP_DIR"
echo "→ git pull (от issa)"
# Без фолбэка на root: если pull от issa не прошёл — это и есть проблема,
# и чинить её надо правами, а не выполнением того же самого от root.
sudo -u issa git -C "$APP_DIR" pull --ff-only

echo "→ обновление зависимостей (от issa, строго из requirements.txt)"
# Только -r requirements.txt: разовых `pip install <пакет>` в деплое быть не
# должно, иначе версия на проде меняется молча (см. историю с edge-tts).
sudo -u issa "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "→ перезапуск сервиса (единственный шаг, которому нужен root)"
systemctl restart "$SERVICE"
sleep 2
systemctl --no-pager status "$SERVICE" | head -5

echo "→ смоук (health, auth API)"
# Деплой без проверки = деплой вслепую. Код выхода смоука — код выхода скрипта.
bash "$APP_DIR/deploy/smoke.sh"
echo "✅ готово"

}
main "$@"
