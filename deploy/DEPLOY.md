# Деплой бота на VPS (24/7) через Git

Бот работает на **long-polling** — нужен постоянно запущенный процесс.
Подходит любой дешёвый Linux-VPS (Ubuntu/Debian). Ниже — пошагово.

> Репозиторий: `https://github.com/ipostatos/ISSA_bot`
> `.env` (токен) и `progress/` в репозиторий НЕ входят — токен задаётся на сервере.

---

## 1. Подключиться к серверу

```bash
ssh root@ВАШ_IP
```

## 2. Установить Python и git (один раз)

```bash
apt update && apt install -y python3 python3-venv python3-pip git
```

## 3. Создать отдельного пользователя (безопасность)

```bash
adduser --system --group --home /opt/issa-bot issa
```

## 4. Склонировать репозиторий

```bash
cd /opt
git clone https://github.com/ipostatos/ISSA_bot.git issa-bot
chown -R issa:issa /opt/issa-bot
```

## 5. Виртуальное окружение и зависимости

Venv создаём и наполняем **от пользователя issa** — от него же работает бот.
Если сделать это от root, в `.venv` останутся файлы `root:root`, и дальше
любой запуск от issa (деплой, pip, сам бот) упрётся в права.

```bash
cd /opt/issa-bot
sudo -u issa python3 -m venv .venv
sudo -u issa /opt/issa-bot/.venv/bin/pip install -r requirements.txt
# проверка: должно вывести 0
sudo find /opt/issa-bot/.venv ! -user issa | wc -l
```

> В `requirements.txt` есть `edge-tts` — он нужен только билд-скрипту озвучки
> (`webapp/build_audio_tts.py`), сам бот его не импортирует. Ставится один раз
> здесь; деплой-скрипты его больше не доустанавливают.

## 6. Задать токен бота

Создайте файл `.env` в `/opt/issa-bot/`:

```bash
echo 'BOT_TOKEN=ВАШ_ТОКЕН_ОТ_BotFather' > /opt/issa-bot/.env
chown issa:issa /opt/issa-bot/.env
chmod 600 /opt/issa-bot/.env
```

## 7. Проверить, что бот стартует вручную

```bash
sudo -u issa /opt/issa-bot/.venv/bin/python /opt/issa-bot/bot.py
```

Должно появиться `Бот запущен: @... | вопросов в банке: 500`.
Остановить — `Ctrl+C`.

## 8. Автозапуск через systemd

```bash
cp /opt/issa-bot/deploy/issa-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now issa-bot
```

Проверить статус и логи:

```bash
systemctl status issa-bot
journalctl -u issa-bot -f      # живой лог (Ctrl+C для выхода)
```

Теперь бот работает 24/7 и сам перезапускается при сбое/перезагрузке сервера.

> **Sandbox-ограничения.** Unit-файлы захардены (`ProtectSystem=strict`,
> `ReadWritePaths`, `SystemCallFilter=@system-service` и т.д.). Бот пишет только
> в `progress/`, API — только в `api/`. Если меняли пути/`WorkingDirectory` —
> поправьте `ReadWritePaths` в `.service`. После правки юнита:
> `sudo cp deploy/issa-*.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart issa-bot issa-api`.
> Если сервис не стартует — `journalctl -u issa-api -n 50` покажет, какой
> системный вызов/путь заблокирован.

---

## Обновление бота (после изменений в коде)

На сервере:

```bash
cd /opt/issa-bot
sudo -u issa git pull
sudo -u issa /opt/issa-bot/.venv/bin/pip install -r requirements.txt -r api/requirements.txt
systemctl restart issa-bot issa-api                                   # единственный шаг от root
```

> Правило: всё, что пишет в `/opt/issa-bot` (git, pip, генерация данных), —
> от `issa`; root оставляем только для `systemctl` и копирования в системные
> каталоги раздачи. Разовых `pip install <пакет>` в деплое быть не должно:
> версии фиксируются в `requirements.txt`.

Или одной строкой — `sudo bash /opt/issa-bot/deploy/update.sh`: те же шаги для
бота и API плюс смоук в конце. Если скрипт на сервере старше этой версии
(без обёртки `main()`), сначала сделайте `sudo -u issa git pull` вручную:
старый скрипт подменяет сам себя посреди выполнения.

---

## Частые проблемы

| Симптом | Причина / решение |
|---|---|
| `ModuleNotFoundError: aiogram` | не активировано venv — запускайте `.venv/bin/python`, не системный python |
| `Не задан BOT_TOKEN` | нет файла `.env` в WorkingDirectory или пустой токен |
| Бот не отвечает, в логах `Conflict` | запущено **два** экземпляра (локально + на сервере). Оставьте один |
| `Permission denied` к progress/ | `chown -R issa:issa /opt/issa-bot` |

## Прогресс пользователей

Хранится в `/opt/issa-bot/progress/*.json` — переживает перезапуски.
Ежедневный бэкап `deploy/backup_db.sh` архивирует эту папку вместе с базой
синхронизации; восстановление — `deploy/DEPLOY_API.md`, «Восстановление».

## ⚠️ Безопасность токена

Репозиторий **публичный**. Токена в нём нет (защищён `.gitignore`), но если
токен когда-либо попадал в коммит/чат — перевыпустите его у @BotFather
(`/revoke` → новый токен → обновите `.env` на сервере → `systemctl restart issa-bot`).
