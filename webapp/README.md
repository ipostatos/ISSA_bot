# Mini Apps (Telegram WebApp)

Самодостаточные статические страницы. Бэкенд/сборка не нужны (никакого
npm/vite/dist) — нужен только **HTTPS-хостинг** (Telegram открывает WebApp
строго по https).

| Файл | Что это | На сервере отдаётся как |
|------|---------|--------------------------|
| `home.html` | 🏠 Стартовый экран: выбор «Тесты» / «Калькулятор» | `/` (index.html) |
| `quiz.html` | 🎓 Тесты: тренировка и экзамен (100 вопросов, таймер, разбор) | `/quiz.html` |
| `index.html` | 🧮 Калькулятор: вкладки «Поправки (TVMDC)» и «Скорость·время·ETA» | `/calc.html` |
| `konspekt.html` | 📖 Конспект: 10 тем со схемами и полнотекстовым поиском | `/konspekt.html` |

## Развёрнуто (текущий сервер)

Хостинг — Caddy на том же VPS, домен **sslip.io** (HTTPS из коробки):

- Стартовый экран: `https://issa-46-224-220-94.sslip.io`
- Тесты: `https://issa-46-224-220-94.sslip.io/quiz.html`
- Калькулятор: `https://issa-46-224-220-94.sslip.io/calc.html`

**Публикация / обновление** (на сервере, заменяет заглушку):

```bash
sudo bash /opt/issa-bot/deploy/update_webapp.sh
```

**BotFather** → /mybots → бот → Bot Settings → Menu Button → Configure menu
button → URL: `https://issa-46-224-220-94.sslip.io` (стартовый экран).

**Кнопки внутри бота** (опционально, чтобы запускать приложения из чата) — в
`.env`:

```bash
WEBAPP_URL=https://issa-46-224-220-94.sslip.io/calc.html
WEBAPP_QUIZ_URL=https://issa-46-224-220-94.sslip.io/quiz.html
```

Вопросы для `quiz.html` лежат в `quiz_data.js` — он **генерируется** из
`questions.json`:

```bash
python webapp/build_quiz_data.py     # после любого изменения банка вопросов
```

`quiz.html` по завершении теста отправляет компактный итог обратно в бота
через `WebApp.sendData` (≈1.4 КБ на экзамен из 100 — в лимит 4 КБ влезает),
бот пишет результат в прогресс пользователя (статистика + работа над ошибками).
Поэтому кнопку запуска тестов даём через **reply-клавиатуру** (только она
умеет `sendData`); калькулятор — обычной inline/WebApp-кнопкой.

Вся арифметика калькулятора повторяет `calc.py` / `nav_tasks.py` (кросс-тест
`_solver_check.mjs` — ответы совпадают с Python-эталоном). Данные тестов
проверяются `_quiz_check.mjs`.

## Вариант A. Тот же VPS + nginx (рекомендуется)

1. Скопировать страницу в каталог веб-сервера:

   ```bash
   sudo mkdir -p /var/www/issa-webapp
   sudo cp /opt/issa-bot/webapp/index.html /var/www/issa-webapp/
   ```

2. Нужен домен или поддомен с TLS-сертификатом (Let's Encrypt). Пример nginx:

   ```nginx
   server {
       listen 443 ssl;
       server_name calc.example.com;
       root /var/www/issa-webapp;
       index index.html;

       ssl_certificate     /etc/letsencrypt/live/calc.example.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/calc.example.com/privkey.pem;
   }
   ```

   Сертификат: `sudo certbot --nginx -d calc.example.com`.

3. Указать боту URL и перезапустить — в `.env` рядом с ботом:

   ```bash
   # обе страницы лежат в одном каталоге /var/www/issa-webapp
   echo 'WEBAPP_URL=https://calc.example.com/index.html'     >> /opt/issa-bot/.env
   echo 'WEBAPP_QUIZ_URL=https://calc.example.com/quiz.html' >> /opt/issa-bot/.env
   systemctl restart issa-bot
   ```

После этого:
- в меню калькулятора — кнопка **«📱 Открыть приложение-калькулятор»**;
- на `/start` и `/tests` снизу — reply-кнопка **«🎓 Тесты (приложение)»**.

Не забудь скопировать обе страницы и данные тестов:

```bash
sudo cp /opt/issa-bot/webapp/index.html /opt/issa-bot/webapp/quiz.html \
        /opt/issa-bot/webapp/quiz_data.js /var/www/issa-webapp/
```

## Вариант B. Бесплатный статик-хостинг

Залить каталог `webapp/` на GitHub Pages / Netlify / Cloudflare Pages (любой
даёт HTTPS) и прописать полученные URL в `WEBAPP_URL` / `WEBAPP_QUIZ_URL`.
Для GitHub Pages адрес будет вида `https://<user>.github.io/ISSA_bot/quiz.html`.

## Если URL не заданы

Ничего не ломается: кнопок приложений просто нет. Калькулятор работает как
диалог в чате, тесты — через `/menu` («🎯 Случайный вопрос», «📝 Экзамен»).

## Проверки

```bash
node webapp/_solver_check.mjs    # калькулятор: "JS MATH OK"
node webapp/_quiz_check.mjs      # тесты: "QUIZ DATA OK"
python webapp/build_quiz_data.py # перегенерировать quiz_data.js из банка
```
