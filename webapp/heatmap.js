// ===========================================================================
// HEATMAP — сетка активности «как на GitHub» для дашборда.
//
// Рисует последние N недель: каждый день — клетка, цвет по числу ответов.
// Данные берём из Progress.days() ({ "YYYY-MM-DD": count }). Цвета — через
// токены темы (var(--accent)), поэтому работает и в тёмной, и в светлой теме.
//
// Использование:
//   Heatmap.render(container, { weeks: 18 });   // container — DOM-элемент
// ===========================================================================
(function (global) {
  "use strict";

  var DAY_MS = 24 * 60 * 60 * 1000;

  function fmt(d) {
    var m = String(d.getMonth() + 1).padStart(2, "0");
    var day = String(d.getDate()).padStart(2, "0");
    return d.getFullYear() + "-" + m + "-" + day;
  }

  // уровень интенсивности 0..4 по числу ответов за день
  function level(n) {
    if (!n) return 0;
    if (n < 5) return 1;
    if (n < 10) return 2;
    if (n < 20) return 3;
    return 4;
  }

  var STYLE_ID = "heatmap-style";
  function ensureStyle() {
    if (global.document.getElementById(STYLE_ID)) return;
    var st = global.document.createElement("style");
    st.id = STYLE_ID;
    st.textContent =
      ".hm{display:flex; gap:3px; overflow-x:auto; -webkit-overflow-scrolling:touch; padding-bottom:2px}" +
      ".hm-col{display:flex; flex-direction:column; gap:3px}" +
      ".hm-c{width:13px; height:13px; border-radius:3px; background:var(--border)}" +
      // уровни — прозрачность акцента, чтобы попадать в любую тему
      ".hm-c.l1{background:color-mix(in srgb, var(--accent) 30%, var(--border))}" +
      ".hm-c.l2{background:color-mix(in srgb, var(--accent) 55%, var(--border))}" +
      ".hm-c.l3{background:color-mix(in srgb, var(--accent) 80%, var(--border))}" +
      ".hm-c.l4{background:var(--accent)}" +
      ".hm-legend{display:flex; align-items:center; gap:6px; justify-content:flex-end;" +
        "margin-top:8px; font-size:11px; color:var(--hint)}" +
      ".hm-legend .hm-c{width:11px; height:11px}";
    global.document.head.appendChild(st);
  }

  var Heatmap = {
    render: function (container, opts) {
      if (!container || !global.Progress) return;
      ensureStyle();
      opts = opts || {};
      var weeks = opts.weeks || 18;
      var days = global.Progress.days();

      // конец — сегодня; начало — понедельник недели (weeks-1) назад
      var today = new Date();
      today.setHours(0, 0, 0, 0);
      var end = new Date(today);
      // выровняем по неделям: идём от сегодня назад weeks*7 дней
      var total = weeks * 7;
      var start = new Date(end.getTime() - (total - 1) * DAY_MS);

      // строим по колонкам-неделям (7 клеток в колонке, пн..вс)
      var html = '<div class="hm">';
      var cur = new Date(start);
      // сдвинем start на начало недели (понедельник), чтобы строки были ровными
      var dow = (cur.getDay() + 6) % 7;            // 0=пн
      cur = new Date(cur.getTime() - dow * DAY_MS);

      while (cur <= end) {
        html += '<div class="hm-col">';
        for (var r = 0; r < 7; r++) {
          var inRange = cur >= start && cur <= end;
          if (inRange) {
            var key = fmt(cur);
            var lv = level(days[key] || 0);
            var t = days[key] ? (key + ": " + days[key]) : key;
            html += '<div class="hm-c' + (lv ? " l" + lv : "") + '" title="' + t + '"></div>';
          } else {
            html += '<div class="hm-c" style="visibility:hidden"></div>';
          }
          cur = new Date(cur.getTime() + DAY_MS);
        }
        html += "</div>";
      }
      html += "</div>";
      html += '<div class="hm-legend">меньше'
        + '<span class="hm-c"></span><span class="hm-c l1"></span>'
        + '<span class="hm-c l2"></span><span class="hm-c l3"></span>'
        + '<span class="hm-c l4"></span>больше</div>';

      container.innerHTML = html;
      // прокрутить к свежим дням (вправо)
      var grid = container.querySelector(".hm");
      if (grid) grid.scrollLeft = grid.scrollWidth;
    },
  };

  global.Heatmap = Heatmap;
})(typeof window !== "undefined" ? window : globalThis);
