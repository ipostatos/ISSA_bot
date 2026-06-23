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

```bash
cd /opt/issa-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

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

---

## Обновление бота (после изменений в коде)

На сервере:

```bash
cd /opt/issa-bot
sudo -u issa git pull
.venv/bin/pip install -r requirements.txt   # если менялись зависимости
systemctl restart issa-bot
```

Или одной строкой — скрипт `deploy/update.sh` (см. ниже).

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
Делайте бэкап этой папки, если важна статистика пользователей.

## ⚠️ Безопасность токена

Репозиторий **публичный**. Токена в нём нет (защищён `.gitignore`), но если
токен когда-либо попадал в коммит/чат — перевыпустите его у @BotFather
(`/revoke` → новый токен → обновите `.env` на сервере → `systemctl restart issa-bot`).
