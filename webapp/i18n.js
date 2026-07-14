// ===========================================================================
// I18N — движок локализации ISSA (RU / PL / UA / EN). Переводы — в i18n.dict.js
// (подключать ПЕРЕД этим файлом). На первом запуске показывает выбор языка;
// выбор в localStorage issa_lang.
//   I18N.t("key", {vars})            → строка на текущем языке
//   data-i18n="key" + I18N.hydrate() → авто-подстановка по атрибуту
//   I18N.picker(true)                → открыть выбор языка повторно
// ===========================================================================
(function (global) {
  "use strict";

  var LANGS = global.ISSA_I18N.LANGS;
  var D = global.ISSA_I18N.DICT;
  var CODES = LANGS.map(function (l) { return l.code; });

  function detectDefault() {
    try {
      var tg = window.Telegram && Telegram.WebApp &&
        Telegram.WebApp.initDataUnsafe && Telegram.WebApp.initDataUnsafe.user &&
        Telegram.WebApp.initDataUnsafe.user.language_code;
      var c = (tg || navigator.language || "ru").slice(0, 2).toLowerCase();
      if (c === "uk") c = "ua";
      return CODES.indexOf(c) >= 0 ? c : "ru";
    } catch (e) { return "ru"; }
  }
  var lang = localStorage.getItem("issa_lang");
  var firstRun = !lang || CODES.indexOf(lang) < 0;
  if (firstRun) lang = detectDefault();

  function t(key, vars) {
    var row = D[key];
    var s = row ? (row[lang] || row.ru) : key;
    if (vars) for (var k in vars) s = s.split("{" + k + "}").join(vars[k]);
    return s;
  }

  function esc(s) {
    return s.replace(/[&<>]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]; });
  }

  function hydrate(root) {
    (root || document).querySelectorAll("[data-i18n]").forEach(function (el) {
      var s = t(el.getAttribute("data-i18n"));
      if (s.indexOf("\n") >= 0) el.innerHTML = s.split("\n").map(esc).join("<br>");
      else el.textContent = s;
    });
    document.documentElement.lang = lang === "ua" ? "uk" : lang;
  }

  /* ── экран выбора языка ── */
  function picker(force) {
    if (!force && !firstRun) return;
    if (document.querySelector(".lang-overlay")) return;
    var ov = document.createElement("div");
    ov.className = "lang-overlay";
    ov.innerHTML =
      '<div class="lang-box card">' +
      '<div class="h2" style="text-align:center;margin:0 0 12px">Please select your language</div>' +
      '<div class="lang-list">' +
      LANGS.map(function (l) {
        return '<button class="btn' + (l.code === lang ? "" : " ghost") +
          '" data-lang="' + l.code + '">' + l.flag + " " + l.label + "</button>";
      }).join("") +
      "</div></div>";
    document.body.appendChild(ov);
    ov.querySelectorAll("[data-lang]").forEach(function (b) {
      b.onclick = function () {
        localStorage.setItem("issa_lang", b.dataset.lang);
        if (typeof haptic === "function") haptic("select");
        location.reload();   // перечитать: все динамические списки перерисуются
      };
    });
  }

  global.I18N = {
    t: t, hydrate: hydrate, picker: picker, LANGS: LANGS,
    get lang() { return lang; }
  };

  document.addEventListener("DOMContentLoaded", function () {
    hydrate();
    if (firstRun) picker();
  });
})(window);
