// Единая навигация Mini App: системная кнопка «Назад» Telegram вместо закрытия окна.
//
// Проблема: страницы Mini App связаны обычными <a href>, и для Telegram это ОДНО
// приложение. Системная «назад» закрывает весь webview, а не возвращает на предыдущую
// страницу. Решение — Telegram BackButton: показываем его на под-страницах и сами
// решаем, куда вести (по истории, иначе на home).
//
// Подключение: <script src="nav.js" data-home="false|true"></script>
//   data-home="true"  — это стартовый экран (home.html): BackButton скрыт.
//   по умолчанию       — под-страница: BackButton ведёт назад/на home.
(function () {
  "use strict";
  var tg = window.Telegram && window.Telegram.WebApp;

  // PWA / офлайн (Этап 4): service worker + манифест. Прогрессивное улучшение —
  // в iOS-клиенте Telegram (WKWebView) SW недоступен, там всё работает по сети.
  // Регистрируем здесь, потому что nav.js подключён на каждой странице; манифест
  // добавляем динамически, чтобы не править все HTML по отдельности.
  try {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("sw.js").catch(function () {});
    }
    if (!document.querySelector('link[rel="manifest"]')) {
      var mf = document.createElement("link");
      mf.rel = "manifest";
      mf.href = "manifest.webmanifest";
      document.head.appendChild(mf);
    }
  } catch (e) {}

  // Безопасный тактильный отклик: на старых/альтернативных клиентах HapticFeedback
  // или его методы могут отсутствовать. Любой сбой глушим, чтобы не ронять UI.
  // type: "success" | "warning" | "error" → notificationOccurred,
  //       "light" | "medium" | "rigid" | "heavy" | "soft" → impactOccurred,
  //       "select" → selectionChanged.
  window.haptic = function (type) {
    try {
      var h = tg && tg.HapticFeedback;
      if (!h) return;
      if (type === "success" || type === "warning" || type === "error") {
        h.notificationOccurred && h.notificationOccurred(type);
      } else if (type === "select") {
        h.selectionChanged && h.selectionChanged();
      } else {
        h.impactOccurred && h.impactOccurred(type || "light");
      }
    } catch (e) {}
  };

  // Подтверждение закрытия Mini App: включать, пока идёт тест/тренировка, чтобы
  // случайный свайп-закрытие (или системный жест) не оборвал сессию без спроса.
  // Фичедетект — на старых клиентах методов может не быть. Вызывать
  // setBusy(true) в начале активной сессии и setBusy(false) в конце.
  window.setBusy = function (on) {
    try {
      if (!tg) return;
      if (on) { tg.enableClosingConfirmation && tg.enableClosingConfirmation(); }
      else { tg.disableClosingConfirmation && tg.disableClosingConfirmation(); }
    } catch (e) {}
  };

  if (!tg) return;
  try { tg.ready(); tg.expand(); } catch (e) {}

  var script = document.currentScript;
  var isHome = script && script.getAttribute("data-home") === "true";

  var bb = tg.BackButton;
  if (!bb) return;

  // Гард от двойного срабатывания: мы подписываемся И на bb.onClick, И на
  // tg.onEvent("backButtonClicked") — на части клиентов приходят ОБА за один тап,
  // и без гарда __navBack срабатывал бы дважды (перескок на два экрана назад).
  // Схлопываем повторные вызовы в пределах одного тика.
  var _navBusy = false;
  function goBack() {
    if (_navBusy) return;
    _navBusy = true;
    setTimeout(function () { _navBusy = false; }, 0);
    // Сперва даём странице шанс обработать «назад» у себя (например, конспект из
    // режима чтения вернётся к списку тем). Если страница вернула true — она
    // справилась сама, окно/страницу не трогаем.
    if (typeof window.__navBack === "function") {
      try { if (window.__navBack() === true) return; } catch (e) {}
    }
    // Иначе — всегда на главную. history.back() в webview Telegram ненадёжен
    // (referrer/history.length скачут), поэтому ведём детерминированно на index.
    window.location.replace("index.html"); // home.html публикуется как index.html
  }

  if (isHome) {
    // На главном экране системная кнопка Telegram закрывает Mini App — это норма.
    bb.hide();
  } else {
    // Подписываемся и на BackButton, и на общесистемное событие back (на части
    // клиентов срабатывает именно оно), чтобы кнопка реагировала стабильно.
    bb.show();
    try { bb.offClick && bb.offClick(goBack); } catch (e) {}
    bb.onClick(goBack);
    try { tg.onEvent && tg.onEvent("backButtonClicked", goBack); } catch (e) {}
  }
})();
