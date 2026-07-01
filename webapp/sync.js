// ===========================================================================
// SYNC — синхронизация прогресса между устройствами через /api/state.
//
// Драйвер: SRS и мотивация живут в localStorage (на устройстве). Этот модуль
// подтягивает их с сервера при старте и отправляет при изменении, чтобы один
// и тот же аккаунт Telegram видел свой прогресс на любом устройстве.
//
// Синхронизируем ТОЛЬКО issa_srs_v1 и issa_progress_v1.
// issa_quiz_session_v1 (незавершённый тест) — НЕ синхронизируем (это сессия
// конкретного устройства).
//
// Безопасность: серверу отправляем Telegram initData в заголовке X-Init-Data;
// сервер проверяет подпись (HMAC) и берёт user_id только оттуда.
//
// Полный фолбэк: нет initData / нет сети / ошибка API → молча работаем на
// localStorage как раньше. Sync НИКОГДА не должен ломать офлайн-режим.
//
// Подключать ПОСЛЕ srs.js и progress.js:
//   <script src="srs.js"></script>
//   <script src="progress.js"></script>
//   <script src="sync.js"></script>
// ===========================================================================
(function (global) {
  "use strict";

  var SRS_KEY = "issa_srs_v1";
  var PROG_KEY = "issa_progress_v1";
  var API = "/api/state";                 // тот же домен, путь /api/* за Caddy
  var POST_DEBOUNCE_MS = 4000;
  // Лимит дней heatmap. ОБЯЗАН совпадать с MAX_HEATMAP_DAYS в api/merge.py
  // (_sync_check.mjs сверяет, что JS-merge даёт тот же результат, что Python).
  var MAX_HEATMAP_DAYS = 365;

  var tg = global.Telegram && global.Telegram.WebApp;
  var initData = (tg && tg.initData) || "";

  function lsGet(k) {
    try { return JSON.parse(global.localStorage.getItem(k)) || {}; }
    catch (e) { return {}; }
  }
  function lsSet(k, v) {
    try { global.localStorage.setItem(k, JSON.stringify(v)); } catch (e) {}
  }

  // ── merge-логика, ИДЕНТИЧНАЯ серверной (api/merge.py) ──
  function validSrs(s) {
    return s && typeof s.box === "number" && typeof s.due === "number" && s.box >= 0 && s.box <= 5;
  }
  function mergeSrs(a, b) {
    a = a || {}; b = b || {};
    var out = {}, ids = {};
    Object.keys(a).forEach(function (k) { ids[k] = 1; });
    Object.keys(b).forEach(function (k) { ids[k] = 1; });
    Object.keys(ids).forEach(function (qid) {
      var x = validSrs(a[qid]) ? a[qid] : null;
      var y = validSrs(b[qid]) ? b[qid] : null;
      if (!x && y) out[qid] = { box: y.box, due: y.due };
      else if (x && !y) out[qid] = { box: x.box, due: x.due };
      else if (x && y) {
        out[qid] = (y.box > x.box || (y.box === x.box && y.due > x.due))
          ? { box: y.box, due: y.due } : { box: x.box, due: x.due };
      }
    });
    return out;
  }
  function mergeProgress(a, b) {
    a = a || {}; b = b || {};
    var days = {};
    [a.days || {}, b.days || {}].forEach(function (src) {
      Object.keys(src).forEach(function (d) {
        var n = parseInt(src[d], 10); if (isNaN(n)) return;
        days[d] = Math.max(days[d] || 0, n);
      });
    });
    var ks = Object.keys(days).sort();
    while (ks.length > MAX_HEATMAP_DAYS) { delete days[ks.shift()]; }
    var num = function (o, k) { var n = parseInt(o[k], 10); return isNaN(n) ? 0 : n; };
    var streak = Math.max(num(a, "streak"), num(b, "streak"));
    var best = Math.max(num(a, "best"), num(b, "best"), streak);
    var goal = num(b, "goal") || num(a, "goal") || 15;
    var lastA = a.lastDay || "", lastB = b.lastDay || "";
    var last = (lastA > lastB ? lastA : lastB) || null;
    var out = { goal: Math.max(5, Math.min(100, goal)), days: days, streak: streak, best: best };
    if (last) {
      out.lastDay = last;
      out.frozenUsed = !!((lastB >= lastA ? b : a).frozenUsed);
    }
    // флаги-достижения (examPass/flawless) — объединяем OR, чтобы sync не стирал
    // только что заслуженные бейджи (см. merge.py).
    var flags = {};
    [a.flags || {}, b.flags || {}].forEach(function (src) {
      Object.keys(src).forEach(function (k) { if (src[k]) flags[k] = true; });
    });
    if (Object.keys(flags).length) out.flags = flags;
    return out;
  }

  function localState() {
    return { srs: lsGet(SRS_KEY), progress: lsGet(PROG_KEY) };
  }
  function applyMerged(state) {
    if (state.srs) lsSet(SRS_KEY, state.srs);
    if (state.progress) lsSet(PROG_KEY, state.progress);
  }

  var Sync = {
    enabled: !!(initData && global.fetch),

    // Подтянуть с сервера и слить в локальный стор. Возвращает Promise<boolean>.
    pull: function () {
      if (!Sync.enabled) return Promise.resolve(false);
      return global.fetch(API, { headers: { "X-Init-Data": initData } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) {
          if (!j || !j.state) return false;
          var loc = localState();
          applyMerged({
            srs: mergeSrs(loc.srs, j.state.srs),
            progress: mergeProgress(loc.progress, j.state.progress),
          });
          return true;
        })
        .catch(function () { return false; });   // офлайн — тихо остаёмся на localStorage
    },

    // Отправить локальное состояние; сервер вернёт merged — применяем обратно.
    push: function () {
      if (!Sync.enabled) return Promise.resolve(false);
      return global.fetch(API, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Init-Data": initData },
        body: JSON.stringify(localState()),
      })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) { if (j && j.state) applyMerged(j.state); return !!j; })
        .catch(function () { return false; });
    },

    // Дебаунс-пуш: вызывать после каждого ответа; реальная отправка — раз в N сек.
    _timer: null,
    schedulePush: function () {
      if (!Sync.enabled) return;
      clearTimeout(Sync._timer);
      Sync._timer = setTimeout(function () { Sync.push(); }, POST_DEBOUNCE_MS);
    },

    // Добавить запись в историю прохождений (по завершении теста).
    // a = {ts, mode, total, correct, pct, secs}. Возвращает Promise<массив|false>.
    pushAttempt: function (a) {
      if (!Sync.enabled) return Promise.resolve(false);
      return global.fetch("/api/attempts", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Init-Data": initData },
        body: JSON.stringify(a),
      })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) { return (j && j.attempts) || false; })
        .catch(function () { return false; });
    },

    // Получить историю прохождений.
    getAttempts: function () {
      if (!Sync.enabled) return Promise.resolve([]);
      return global.fetch("/api/attempts", { headers: { "X-Init-Data": initData } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) { return (j && j.attempts) || []; })
        .catch(function () { return []; });
    },
  };

  // отправить накопленное при сворачивании/закрытии Mini App
  global.addEventListener("visibilitychange", function () {
    if (global.document.visibilityState === "hidden") Sync.push();
  });

  global.Sync = Sync;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { mergeSrs: mergeSrs, mergeProgress: mergeProgress };
  }
})(typeof window !== "undefined" ? window : globalThis);
