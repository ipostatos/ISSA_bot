// ===========================================================================
// MISTAKES — «журнал ошибок»: автоматическая тетрадь трудных вопросов.
//
// Зачем: вопросы, где ошибся не раз, — главный резерв баллов. Журнал собирает
// их сам и даёт прогнать одним нажатием (retrieval practice по слабым местам).
//
// Правила (простые и честные):
//   • вопрос ПОПАДАЕТ в журнал после 2-й ошибки (единичная ошибка — шум);
//   • вопрос ПОКИДАЕТ журнал после 2 ПОДРЯД верных ответов (закрепил — свободен).
//
// Хранилище issa_mistakes_v1: { [qid]: {n, ok} }
//   n  — всего ошибок по вопросу;
//   ok — верных ответов ПОДРЯД с момента последней ошибки.
// Ключ НЕ синхронизируется между устройствами: sync-merge (sync.js/merge.py)
// переносит только srs/progress/pl_progress, и расширять его ради журнала не
// стоит — журнал ценен и локально, а паритет JS/Python merge хрупок.
//
// API (window.Mistakes):
//   record(qid, correct) — вызвать после каждого ответа в тренировке;
//   list()               — id вопросов, находящихся в журнале сейчас;
//   count()              — размер журнала (для кнопки);
//   wrongCount(qid)      — сколько всего ошибок по вопросу;
//   reset()              — очистить (для тестов).
// ===========================================================================
(function (global) {
  "use strict";

  var KEY = "issa_mistakes_v1";
  var ENTER_AT = 2;   // ошибок до попадания в журнал
  var EXIT_AT = 2;    // верных подряд до выхода из журнала

  function load() {
    try { return JSON.parse(global.localStorage.getItem(KEY)) || {}; }
    catch (e) { return {}; }
  }
  function save(s) {
    try { global.localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {}
  }
  function inJournal(rec) {
    return !!rec && rec.n >= ENTER_AT && rec.ok < EXIT_AT;
  }

  var Mistakes = {
    record: function (qid, correct) {
      var s = load();
      var r = s[qid] || { n: 0, ok: 0 };
      if (correct) {
        r.ok += 1;
        // вопрос без ошибок не храним вовсе — журнал не пухнет от верных ответов
        if (r.n === 0) { delete s[qid]; save(s); return; }
      } else {
        r.n += 1; r.ok = 0;
      }
      s[qid] = r;
      save(s);
    },

    list: function () {
      var s = load();
      return Object.keys(s).filter(function (qid) { return inJournal(s[qid]); });
    },

    count: function () { return Mistakes.list().length; },

    wrongCount: function (qid) {
      var r = load()[qid];
      return r ? r.n : 0;
    },

    reset: function () { save({}); },
  };

  global.Mistakes = Mistakes;
  if (typeof module !== "undefined" && module.exports) module.exports = Mistakes;
})(typeof window !== "undefined" ? window : globalThis);
