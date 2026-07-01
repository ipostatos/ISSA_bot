// Прогресс польских лицензий (Żeglarz / Sternik). Отдельно от ISSA-SRS:
// у польских банков нет интервального повторения, поэтому «готовность» —
// это доля вопросов банка, отвеченных ВЕРНО хотя бы раз (честно, из реальной
// активности, без выдуманных цифр). Всё на localStorage, без бэкенда.
//
// Активность (heatmap/серия на главной) пишем в общий Progress.recordAnswer(),
// чтобы польские ответы тоже попадали в календарь активности.
//
// API:
//   PLProgress.record(license, qid, correct)   — отметить ответ (license: "zeglarz"|"sternik")
//   PLProgress.readiness(license, total)        — {solved,total,percent,verdict}
//   PLProgress.solvedCount(license)             — число уникально верных
//   PLProgress.bestExam(license)                — {correct,total} лучшего экзамена или null
//   PLProgress.recordExam(license, correct, total)
(function (global) {
  "use strict";

  var KEY = "issa_pl_progress_v1";

  function load() {
    try { return JSON.parse(global.localStorage.getItem(KEY)) || {}; }
    catch (e) { return {}; }
  }
  function save(s) {
    try { global.localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {}
  }
  function lic(s, license) {
    s[license] = s[license] || { solved: {}, bestCorrect: null, bestTotal: null };
    return s[license];
  }

  function verdictFor(percent) {
    return percent >= 80 ? "Готов к экзамену"
         : percent >= 60 ? "Почти готов"
         : percent >= 30 ? "В процессе"
         : "В начале пути";
  }

  var PLProgress = {
    // Отметить ответ. Верный вопрос попадает в множество solved (уникально).
    // Активность за день пишем в общий Progress (если он есть).
    record: function (license, qid, correct) {
      if (correct) {
        var s = load();
        var L = lic(s, license);
        L.solved[qid] = 1;
        save(s);
      }
      if (global.Progress && typeof global.Progress.recordAnswer === "function") {
        global.Progress.recordAnswer();
      }
    },

    solvedCount: function (license) {
      var L = load()[license];
      return L && L.solved ? Object.keys(L.solved).length : 0;
    },

    // Готовность = solved / total банка. verdict — та же лестница, что у ISSA.
    readiness: function (license, total) {
      var solved = this.solvedCount(license);
      var percent = total ? Math.round(solved / total * 100) : 0;
      return { solved: solved, total: total, percent: percent, verdict: verdictFor(percent) };
    },

    recordExam: function (license, correct, total) {
      var s = load();
      var L = lic(s, license);
      if (L.bestCorrect == null || correct > L.bestCorrect) {
        L.bestCorrect = correct; L.bestTotal = total;
      }
      save(s);
    },

    bestExam: function (license) {
      var L = load()[license];
      if (!L || L.bestCorrect == null) return null;
      return { correct: L.bestCorrect, total: L.bestTotal };
    },

    reset: function () { save({}); },
  };

  global.PLProgress = PLProgress;
})(typeof window !== "undefined" ? window : globalThis);
