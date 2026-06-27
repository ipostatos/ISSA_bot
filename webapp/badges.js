// ===========================================================================
// BADGES — морские достижения на основе реальных данных (SRS + Progress).
//
// Никаких выдуманных счётчиков: каждое условие считается из того, что у нас уже
// есть на устройстве. Поэтому бейджи честные и не требуют сервера.
//
// Источник прогресса (метрики):
//   answered  — всего ответов (сумма Progress.days)
//   streak    — текущая серия дней (Progress.streakInfo().streak)
//   best      — рекорд серии
//   learned   — закреплено вопросов (box>=4)  (SRS.stats)
//   topicsDone— тем закреплено на 100% (по readiness topics, pct>=80)
//   ready     — общая готовность %
//   examPass  — сдан ли пробный экзамен (Progress.flag)
//
// API (window.Badges):
//   list(metrics)         → [{id, icon, tier, title, desc, unlocked, progress}]
//   unlockedCount(metrics)→ число открытых
//   computeMetrics()      → собрать метрики из SRS/Progress/QUIZ_DATA
//   checkNew(metrics)     → вернуть НОВЫЕ открытые с прошлой проверки (для тоста)
// tier: bronze | silver | gold — для рамки медальона.
// ===========================================================================
(function (global) {
  "use strict";

  var SEEN_KEY = "issa_badges_seen_v1";   // какие бейджи уже показаны (для тостов)

  // Определения. cond(m) → true если открыт. prog(m) → 0..1 к следующей цели.
  var DEFS = [
    { id: "first_steps", icon: "⚓", tier: "bronze", title: "Юнга",
      desc: "Первый ответ в тренировке",
      cond: function (m) { return m.answered >= 1; },
      prog: function (m) { return Math.min(m.answered / 1, 1); } },

    { id: "answered_100", icon: "🧭", tier: "bronze", title: "Матрос",
      desc: "100 ответов",
      cond: function (m) { return m.answered >= 100; },
      prog: function (m) { return Math.min(m.answered / 100, 1); } },

    { id: "answered_500", icon: "🚢", tier: "silver", title: "Боцман",
      desc: "500 ответов",
      cond: function (m) { return m.answered >= 500; },
      prog: function (m) { return Math.min(m.answered / 500, 1); } },

    { id: "streak_7", icon: "🔥", tier: "bronze", title: "Попутный ветер",
      desc: "Серия 7 дней",
      cond: function (m) { return m.best >= 7; },
      prog: function (m) { return Math.min(m.best / 7, 1); } },

    { id: "streak_30", icon: "🌊", tier: "gold", title: "Морской волк",
      desc: "Серия 30 дней",
      cond: function (m) { return m.best >= 30; },
      prog: function (m) { return Math.min(m.best / 30, 1); } },

    { id: "learned_50", icon: "💡", tier: "silver", title: "Штурман",
      desc: "50 вопросов закреплено",
      cond: function (m) { return m.learned >= 50; },
      prog: function (m) { return Math.min(m.learned / 50, 1); } },

    { id: "topic_master", icon: "📍", tier: "silver", title: "Знаток темы",
      desc: "Тема закреплена на 80%+",
      cond: function (m) { return m.topicsDone >= 1; },
      prog: function (m) { return m.topicsDone >= 1 ? 1 : 0; } },

    { id: "all_topics", icon: "🗺️", tier: "gold", title: "Лоцман",
      desc: "Все темы закреплены на 80%+",
      cond: function (m) { return m.topicsTotal > 0 && m.topicsDone >= m.topicsTotal; },
      prog: function (m) { return m.topicsTotal ? m.topicsDone / m.topicsTotal : 0; } },

    { id: "ready_80", icon: "🎖️", tier: "gold", title: "Готов к экзамену",
      desc: "Готовность 80%+",
      cond: function (m) { return m.ready >= 80; },
      prog: function (m) { return Math.min(m.ready / 80, 1); } },

    { id: "exam_pass", icon: "🧑‍✈️", tier: "gold", title: "Шкипер",
      desc: "Сдан пробный экзамен (≥75%)",
      cond: function (m) { return !!m.examPass; },
      prog: function (m) { return m.examPass ? 1 : 0; } },

    { id: "flawless", icon: "⭐", tier: "gold", title: "Без единой ошибки",
      desc: "Экзамен на 100%",
      cond: function (m) { return !!m.flawless; },
      prog: function (m) { return m.flawless ? 1 : 0; } },

    { id: "anchor_watch", icon: "🌙", tier: "silver", title: "Якорная вахта",
      desc: "Повторял 14 дней подряд",
      cond: function (m) { return m.best >= 14; },
      prog: function (m) { return Math.min(m.best / 14, 1); } },
  ];

  function lsGet(k) { try { return JSON.parse(global.localStorage.getItem(k)) || {}; } catch (e) { return {}; } }
  function lsSet(k, v) { try { global.localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }

  var Badges = {
    DEFS: DEFS,

    list: function (m) {
      return DEFS.map(function (d) {
        return {
          id: d.id, icon: d.icon, tier: d.tier, title: d.title, desc: d.desc,
          unlocked: !!d.cond(m),
          progress: Math.max(0, Math.min(1, d.prog(m))),
        };
      });
    },

    unlockedCount: function (m) {
      return DEFS.reduce(function (n, d) { return n + (d.cond(m) ? 1 : 0); }, 0);
    },

    // Собираем метрики из доступных модулей (вызывать в браузере).
    computeMetrics: function () {
      var D = global.QUIZ_DATA;
      var ids = (D && D.questions) ? D.questions.map(function (q) { return q.id; }) : [];
      var m = { answered: 0, streak: 0, best: 0, learned: 0,
                topicsDone: 0, topicsTotal: 0, ready: 0, examPass: false, flawless: false };

      if (global.Progress) {
        var days = global.Progress.days();
        m.answered = Object.keys(days).reduce(function (s, k) { return s + (parseInt(days[k], 10) || 0); }, 0);
        var si = global.Progress.streakInfo();
        m.streak = si.streak; m.best = si.best;
        var fl = global.Progress.flags ? global.Progress.flags() : {};
        m.examPass = !!fl.examPass; m.flawless = !!fl.flawless;
      }
      if (global.SRS && ids.length) {
        m.learned = global.SRS.stats(ids).learned;
      }
      if (global.Progress && ids.length && D) {
        var boxOf = function (id) { var s = global.SRS && global.SRS.state(id); return s ? s.box : null; };
        var r = global.Progress.readiness(D.questions, boxOf);
        m.ready = r.percent;
        m.topicsTotal = r.topics.length;
        m.topicsDone = r.topics.filter(function (t) { return t.pct >= 80; }).length;
      }
      return m;
    },

    // Новые открытые бейджи с прошлой проверки (для всплывашки).
    checkNew: function (m) {
      var seen = lsGet(SEEN_KEY);
      var fresh = [];
      DEFS.forEach(function (d) {
        if (d.cond(m) && !seen[d.id]) { fresh.push(d); seen[d.id] = 1; }
      });
      if (fresh.length) lsSet(SEEN_KEY, seen);
      return fresh.map(function (d) { return { id: d.id, icon: d.icon, title: d.title }; });
    },
  };

  global.Badges = Badges;
  if (typeof module !== "undefined" && module.exports) module.exports = Badges;
})(typeof window !== "undefined" ? window : globalThis);
