# Mini App: калькулятор TVMDC

`index.html` — самодостаточное Telegram Mini App (WebApp): выбор направления
пересчёта, ввод курса и поправок, мгновенный результат с пошаговым решением.
Вся арифметика повторяет `calc.py` / `nav_tasks.py` (проверено кросс-тестом
`_solver_check.mjs` — ответы совпадают с Python-эталоном).

Бэкенд не нужен — это статическая страница. Нужен только **HTTPS-хостинг**
(Telegram открывает WebApp строго по https).

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
   echo 'WEBAPP_URL=https://calc.example.com/index.html' >> /opt/issa-bot/.env
   systemctl restart issa-bot
   ```

После этого в меню калькулятора появляется кнопка
**«📱 Открыть приложение-калькулятор»**.

## Вариант B. Бесплатный статик-хостинг

Залить `index.html` на GitHub Pages / Netlify / Cloudflare Pages (любой даёт
HTTPS) и прописать полученный URL в `WEBAPP_URL`. Пример для GitHub Pages:
включить Pages для каталога `webapp/` — адрес будет вида
`https://<user>.github.io/ISSA_bot/index.html`.

## Если WEBAPP_URL не задан

Ничего не ломается: кнопки приложения просто нет, калькулятор работает как
обычный диалог в чате (выбор направления + ввод значений строкой).

## Проверка математики

```bash
node webapp/_solver_check.mjs   # должно вывести "JS MATH OK"
```
