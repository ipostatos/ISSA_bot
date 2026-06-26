// ===========================================================================
// SRS — интервальное повторение (Leitner) для тестов ISSA.
//
// Зачем: теория забывается. SRS возвращает вопрос на повтор ровно тогда, когда
// он вот-вот забудется — это доказанный способ удержать знание в памяти.
//
// Где хранится: localStorage (на устройстве; синхрон между устройствами — это
// Фаза 4 с бэкендом). Ключ issa_srs_v1: { [qid]: {box, due} }.
//   box  — номер «коробки» 0..5 (чем выше — тем реже спрашиваем);
//   due  — timestamp (мс), когда вопрос снова «созреет» для повтора.
//
// Поведение: верный ответ → box+1 и due отодвигается по INTERVALS; ошибка →
// box сбрасывается в 0 и due = сейчас (повторим скоро). Невиданный вопрос
// считается «к повтору» (его пора выучить).
//
// API (window.SRS):
//   grade(qid, correct)      — записать результат ответа;
//   state(qid)               — {box, due} или null;
//   isDue(qid, now?)         — пора ли повторять (или ещё не виден);
//   dueCount(allIds, now?)   — сколько из allIds пора повторить;
//   pickDue(allIds, n, now?) — выбрать до n вопросов к повтору (сначала
//                              просроченные сильнее / низкие коробки);
//   stats(allIds)            — сводка по коробкам (для прогресса).
// Функции чистые там, где можно (принимают now) — это позволяет тестировать.
// ===========================================================================
(function (global) {
  "use strict";

  var KEY = "issa_srs_v1";
  // интервалы по коробкам, мс. box 0 — повторить почти сразу.
  var MIN = 60 * 1000, HOUR = 60 * MIN, DAY = 24 * HOUR;
  var INTERVALS = [10 * MIN, 4 * HOUR, 1 * DAY, 3 * DAY, 7 * DAY, 21 * DAY];
  var MAX_BOX = INTERVALS.length - 1;

  function load() {
    try { return JSON.parse(global.localStorage.getItem(KEY)) || {}; }
    catch (e) { return {}; }
  }
  function save(map) {
    try { global.localStorage.setItem(KEY, JSON.stringify(map)); } catch (e) {}
  }

  // Чистое ядро перехода — без хранилища, удобно тестировать.
  // prev: {box,due} | undefined ; возвращает новое {box,due}.
  function nextState(prev, correct, now) {
    var box = prev ? prev.box : 0;
    if (correct) box = Math.min(box + 1, MAX_BOX);
    else box = 0;
    var due = now + INTERVALS[box];
    return { box: box, due: due };
  }

  var SRS = {
    INTERVALS: INTERVALS,
    nextState: nextState,           // экспортируем чистое ядро для тестов

    grade: function (qid, correct, now) {
      now = now || Date.now();
      var map = load();
      map[qid] = nextState(map[qid], correct, now);
      save(map);
      return map[qid];
    },

    state: function (qid) {
      var map = load();
      return map[qid] || null;
    },

    // «Пора» = есть запись и due прошёл; невиданный вопрос тоже считаем «к изучению».
    isDue: function (qid, now) {
      now = now || Date.now();
      var map = load();
      var s = map[qid];
      if (!s) return true;            // ещё не учили — пора
      return s.due <= now;
    },

    dueCount: function (allIds, now) {
      now = now || Date.now();
      var map = load(), n = 0;
      for (var i = 0; i < allIds.length; i++) {
        var s = map[allIds[i]];
        if (!s || s.due <= now) n++;
      }
      return n;
    },

    // Выбрать до n вопросов к повтору. Приоритет: сильнее просроченные и низкие
    // коробки идут первыми; невиданные — в конце (их и так много, не топим повтор).
    pickDue: function (allIds, n, now) {
      now = now || Date.now();
      var map = load();
      var seen = [], fresh = [];
      for (var i = 0; i < allIds.length; i++) {
        var id = allIds[i], s = map[id];
        if (s) { if (s.due <= now) seen.push({ id: id, box: s.box, over: now - s.due }); }
        else fresh.push(id);
      }
      // просроченные: ниже коробка и больше просрочка — раньше
      seen.sort(function (a, b) { return (a.box - b.box) || (b.over - a.over); });
      var ids = seen.map(function (x) { return x.id; }).concat(fresh);
      return n ? ids.slice(0, n) : ids;
    },

    // Сводка по коробкам — для индикаторов прогресса.
    stats: function (allIds) {
      var map = load();
      var boxes = [0, 0, 0, 0, 0, 0], learned = 0, started = 0;
      for (var i = 0; i < allIds.length; i++) {
        var s = map[allIds[i]];
        if (!s) continue;
        started++;
        boxes[s.box]++;
        if (s.box >= 4) learned++;      // box 4-5 ≈ «закреплено»
      }
      return { total: allIds.length, started: started, learned: learned, boxes: boxes };
    },

    reset: function () { save({}); },
  };

  global.SRS = SRS;
  if (typeof module !== "undefined" && module.exports) module.exports = SRS;
})(typeof window !== "undefined" ? window : globalThis);
