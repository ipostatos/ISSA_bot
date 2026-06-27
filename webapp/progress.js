// ===========================================================================
// PROGRESS — мотивация: дневная цель, бережный streak, готовность к экзамену.
//
// Зачем: видимая цель и прогресс возвращают пользователя. Считаем честно из
// реальной активности (SRS), без выдуманных цифр. Всё на localStorage.
//
// Хранилище issa_progress_v1:
//   { goal: N, days: { "YYYY-MM-DD": count }, streak, best, lastDay, frozenUsed }
//
// Streak «бережный»: пропуск РОВНО одного дня не рвёт серию (одна заморозка
// подряд). Два и более пропущенных дня — серия сбрасывается. Это держит
// мотивацию, а не наказывает за один пропуск.
//
// Готовность к экзамену: доля «закреплённых» вопросов (по коробкам SRS),
// взвешенно по темам — чтобы слабая тема тянула общий процент вниз.
//
// API (window.Progress):
//   dayKey(date?)                  — "YYYY-MM-DD" (локальная дата);
//   getGoal() / setGoal(n)         — дневная цель (по умолчанию 15);
//   recordAnswer(today?)           — +1 к сегодняшнему счётчику, обновляет streak;
//   todayCount(today?)             — сколько отвечено сегодня;
//   streakInfo()                   — {streak, best};
//   readiness(srsStats, byTopic)   — {percent, verdict, topics:[{topic,pct}]};
//   bumpStreakOnOpen(today?)       — пересчитать streak при заходе (на случай пропусков).
// Чистое ядро nextStreak() — без хранилища, для тестов.
// ===========================================================================
(function (global) {
  "use strict";

  var KEY = "issa_progress_v1";
  var DEFAULT_GOAL = 15;
  var DAY_MS = 24 * 60 * 60 * 1000;

  function load() {
    try { return JSON.parse(global.localStorage.getItem(KEY)) || {}; }
    catch (e) { return {}; }
  }
  function save(s) {
    try { global.localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {}
  }

  function dayKey(date) {
    var d = date || new Date();
    var m = String(d.getMonth() + 1).padStart(2, "0");
    var day = String(d.getDate()).padStart(2, "0");
    return d.getFullYear() + "-" + m + "-" + day;
  }

  // Разница в днях между двумя ключами YYYY-MM-DD (b - a).
  function dayDiff(a, b) {
    if (!a || !b) return Infinity;
    var pa = a.split("-").map(Number), pb = b.split("-").map(Number);
    var da = Date.UTC(pa[0], pa[1] - 1, pa[2]);
    var db = Date.UTC(pb[0], pb[1] - 1, pb[2]);
    return Math.round((db - da) / DAY_MS);
  }

  // Чистое ядро: как меняется streak при активности в день `today`.
  // prev: {streak,best,lastDay,frozenUsed}. Возвращает новое состояние.
  function nextStreak(prev, today) {
    var streak = prev.streak || 0, best = prev.best || 0;
    var last = prev.lastDay, frozenUsed = prev.frozenUsed || false;
    if (last === today) {
      // уже активничал сегодня — серия не меняется
    } else {
      var gap = dayDiff(last, today);
      if (last == null || gap === 1) {
        streak = streak + 1; frozenUsed = false;          // подряд
      } else if (gap === 2) {
        streak = streak + 1; frozenUsed = true;           // пропущен 1 день — заморозка
      } else {
        streak = 1; frozenUsed = false;                   // разрыв — начинаем заново
      }
    }
    best = Math.max(best, streak);
    return { streak: streak, best: best, lastDay: today, frozenUsed: frozenUsed };
  }

  var Progress = {
    dayKey: dayKey,
    nextStreak: nextStreak,

    getGoal: function () { return load().goal || DEFAULT_GOAL; },
    setGoal: function (n) {
      var s = load(); s.goal = Math.max(5, Math.min(100, n | 0)); save(s); return s.goal;
    },

    todayCount: function (today) {
      var s = load(); var k = today || dayKey();
      return (s.days && s.days[k]) || 0;
    },

    // карта активности по дням { "YYYY-MM-DD": count } — для heatmap
    days: function () { return load().days || {}; },

    recordAnswer: function (today) {
      var s = load(); var k = today || dayKey();
      s.days = s.days || {};
      var firstToday = !s.days[k];
      s.days[k] = (s.days[k] || 0) + 1;
      if (firstToday) {                       // первый ответ за день → обновить серию
        var ns = nextStreak(s, k);
        s.streak = ns.streak; s.best = ns.best; s.lastDay = ns.lastDay; s.frozenUsed = ns.frozenUsed;
      }
      // компактность: храним только последние ~60 дней
      var keys = Object.keys(s.days).sort();
      while (keys.length > 60) { delete s.days[keys.shift()]; }
      save(s);
      return s.days[k];
    },

    // Пересчёт серии при заходе: если последняя активность была >2 дней назад —
    // серия фактически прервана, показываем 0 (но best не теряем).
    streakInfo: function (today) {
      var s = load(); var k = today || dayKey();
      var streak = s.streak || 0, best = s.best || 0;
      if (s.lastDay && dayDiff(s.lastDay, k) > 2) streak = 0;
      return { streak: streak, best: best, lastDay: s.lastDay || null };
    },

    // Готовность к экзамену из статистики SRS по темам.
    // srsStateMap: window.SRS не передаём — считаем по box каждого вопроса через
    // переданный список {id, topic, box|null}. Чтобы не дублировать SRS, принимаем
    // готовую функцию boxOf(id) и список вопросов.
    readiness: function (questions, boxOf) {
      // группируем по теме, считаем долю «закреплённых» (box>=4) с частичным
      // зачётом для средних коробок — так процент растёт плавно, мотивируя.
      var byTopic = {};
      questions.forEach(function (q) {
        var t = byTopic[q.topic] || (byTopic[q.topic] = { sum: 0, n: 0 });
        var box = boxOf(q.id);                 // 0..5 или null (не начат)
        var w = box == null ? 0 : Math.min(box, 5) / 5;   // вклад 0..1
        t.sum += w; t.n += 1;
      });
      var topics = Object.keys(byTopic).map(function (name) {
        var t = byTopic[name];
        return { topic: name, pct: Math.round(t.sum / t.n * 100), n: t.n };
      }).sort(function (a, b) { return a.pct - b.pct; });   // слабые сверху
      // общий процент — среднее по вопросам (не по темам), чтобы крупные темы весили честно
      var totSum = 0, totN = 0;
      questions.forEach(function (q) {
        var box = boxOf(q.id);
        totSum += (box == null ? 0 : Math.min(box, 5) / 5); totN += 1;
      });
      var percent = totN ? Math.round(totSum / totN * 100) : 0;
      var verdict = percent >= 80 ? "Готов к экзамену"
                  : percent >= 60 ? "Почти готов"
                  : percent >= 30 ? "В процессе"
                  : "В начале пути";
      return { percent: percent, verdict: verdict, topics: topics };
    },

    reset: function () { save({}); },
  };

  global.Progress = Progress;
  if (typeof module !== "undefined" && module.exports) module.exports = Progress;
})(typeof window !== "undefined" ? window : globalThis);
