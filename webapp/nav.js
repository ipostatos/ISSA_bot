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

  if (!tg) return;
  try { tg.ready(); tg.expand(); } catch (e) {}

  var script = document.currentScript;
  var isHome = script && script.getAttribute("data-home") === "true";

  var bb = tg.BackButton;
  if (!bb) return;

  function goBack() {
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
