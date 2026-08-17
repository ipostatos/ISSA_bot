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
  var PL_PROG_KEY = "issa_pl_progress_v1";  // прогресс польских лицензий
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

  // ── merge-логика, зеркало серверной (api/merge.py) ──
  // ВАЖНО: правила слияния совпадают с сервером один в один (это сверяет
  // _sync_check.mjs). НЕ совпадают потолки состояния (MAX_SRS_KEYS, MAX_FLAGS,
  // MAX_PL_*): они живут только на сервере — клиенту резать своё состояние
  // незачем, а серверный ответ мы больше не применяем поверх локального
  // вслепую (см. push).
  var DAY_RE = /^\d{4}-\d{2}-\d{2}$/;
  var MAX_DAY_COUNT = 100000;
  var MAX_TS_MS = 4102444800000;   // 2100-01-01

  function num(v) {   // число или null; bool и NaN/Infinity — не числа
    return (typeof v === "number" && isFinite(v)) ? v : null;
  }
  function validSrs(s) {
    return !!s && num(s.box) !== null && num(s.due) !== null && s.box >= 0 && s.box <= 5;
  }
  function normSrs(s) {
    var out = { box: s.box, due: s.due };
    var ts = num(s.ts);
    if (ts !== null && ts > 0 && ts <= MAX_TS_MS) out.ts = ts;
    return out;
  }
  // Свежее ли y, чем x. Раньше побеждало «более выученное» (выше box) — из-за
  // этого сброс коробки после ошибки откатывался при синке с устройством,
  // которое об ошибке не знает. Теперь побеждает более поздний ts; записи без
  // ts (старый клиент) уступают записям с ts. Подробности — в merge.py.
  function srsNewer(x, y) {
    var tx = x.ts, ty = y.ts;
    if (tx !== undefined && ty !== undefined) {
      return ty > tx || (ty === tx && y.box > x.box);
    }
    if (ty !== undefined) return true;
    if (tx !== undefined) return false;
    return y.box > x.box || (y.box === x.box && y.due > x.due);
  }
  function mergeSrs(a, b) {
    a = a || {}; b = b || {};
    var out = {}, ids = {};
    Object.keys(a).forEach(function (k) { ids[k] = 1; });
    Object.keys(b).forEach(function (k) { ids[k] = 1; });
    Object.keys(ids).forEach(function (qid) {
      var x = validSrs(a[qid]) ? normSrs(a[qid]) : null;
      var y = validSrs(b[qid]) ? normSrs(b[qid]) : null;
      if (!x && y) out[qid] = y;
      else if (x && !y) out[qid] = x;
      else if (x && y) out[qid] = srsNewer(x, y) ? y : x;
    });
    return out;
  }
  function mergeProgress(a, b) {
    a = a || {}; b = b || {};
    // ключ дня обязан быть датой YYYY-MM-DD (иначе длина ключа ничем не
    // ограничена — см. DAY_RE в merge.py); счётчик клампим сверху
    var days = {};
    [a.days || {}, b.days || {}].forEach(function (src) {
      Object.keys(src).forEach(function (d) {
        if (!DAY_RE.test(d)) return;
        var n = parseInt(src[d], 10); if (isNaN(n)) return;
        n = Math.max(0, Math.min(MAX_DAY_COUNT, n));
        days[d] = Math.max(days[d] || 0, n);
      });
    });
    var ks = Object.keys(days).sort();
    while (ks.length > MAX_HEATMAP_DAYS) { delete days[ks.shift()]; }
    var num = function (o, k) { var n = parseInt(o[k], 10); return isNaN(n) ? 0 : n; };
    var streak = Math.max(num(a, "streak"), num(b, "streak"));
    var best = Math.max(num(a, "best"), num(b, "best"), streak);
    var goal = num(b, "goal") || num(a, "goal") || 15;
    var dayOrEmpty = function (v) { return (typeof v === "string" && DAY_RE.test(v)) ? v : ""; };
    var lastA = dayOrEmpty(a.lastDay), lastB = dayOrEmpty(b.lastDay);
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
  // Польский прогресс: { lic: {solved:{qid:1}, bestCorrect, bestTotal} }.
  // solved — объединение; bestCorrect — max; bestTotal берём У источника с
  // лучшим bestCorrect (иначе total разъедется). Идентично merge_pl_progress.
  function mergePlProgress(a, b) {
    a = a || {}; b = b || {};
    var out = {}, lics = {};
    Object.keys(a).forEach(function (k) { lics[k] = 1; });
    Object.keys(b).forEach(function (k) { lics[k] = 1; });
    Object.keys(lics).forEach(function (lic) {
      var x = (a[lic] && typeof a[lic] === "object") ? a[lic] : {};
      var y = (b[lic] && typeof b[lic] === "object") ? b[lic] : {};
      var solved = {};
      [x.solved || {}, y.solved || {}].forEach(function (src) {
        if (src && typeof src === "object") {
          Object.keys(src).forEach(function (qid) { solved[qid] = 1; });
        }
      });
      var bestPair = function (d) {
        var c = parseInt(d.bestCorrect, 10);
        if (isNaN(c)) return null;
        var t = parseInt(d.bestTotal, 10);
        return { c: c, t: isNaN(t) ? null : t };
      };
      var bx = bestPair(x), by = bestPair(y), best = null;
      if (bx && by) best = (by.c > bx.c) ? by : bx;
      else best = bx || by;
      if (Object.keys(solved).length || best) {
        out[lic] = {
          solved: solved,
          bestCorrect: best ? best.c : null,
          bestTotal: best ? best.t : null,
        };
      }
    });
    return out;
  }

  function localState() {
    return { srs: lsGet(SRS_KEY), progress: lsGet(PROG_KEY), pl_progress: lsGet(PL_PROG_KEY) };
  }
  function applyMerged(state) {
    if (state.srs) lsSet(SRS_KEY, state.srs);
    if (state.progress) lsSet(PROG_KEY, state.progress);
    if (state.pl_progress) lsSet(PL_PROG_KEY, state.pl_progress);
  }
  // Ответ сервера ВСЕГДА применяем через слияние с текущим локальным состоянием,
  // а не перезаписью. Причины две:
  //   1) пока запрос летел, пользователь мог ответить ещё на вопрос — снапшот,
  //      отправленный на сервер, уже устарел, и перезапись стирала бы этот ответ;
  //   2) сервер режет входящее по потолкам (MAX_SRS_KEYS и т.п.) и возвращает
  //      состояние без отброшенных ключей — перезапись удаляла бы их у клиента
  //      навсегда, хотя потолок задуман как «не приму», а не «сотри у себя».
  function mergeIntoLocal(state) {
    var loc = localState();
    applyMerged({
      srs: mergeSrs(loc.srs, state.srs),
      progress: mergeProgress(loc.progress, state.progress),
      pl_progress: mergePlProgress(loc.pl_progress, state.pl_progress),
    });
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
          mergeIntoLocal(j.state);
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
        // финальный push при сворачивании Mini App должен пережить выгрузку
        // страницы (иначе последние ответы не доедут до сервера)
        keepalive: true,
      })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) { if (j && j.state) mergeIntoLocal(j.state); return !!j; })
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
    module.exports = { mergeSrs: mergeSrs, mergeProgress: mergeProgress,
                       mergePlProgress: mergePlProgress };
  }
})(typeof window !== "undefined" ? window : globalThis);
