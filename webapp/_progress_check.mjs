// Проверка модуля мотивации: streak с заморозкой, дневной счётчик, готовность.
// Запуск: node webapp/_progress_check.mjs
import { readFileSync } from "fs";

const src = readFileSync(new URL("./progress.js", import.meta.url), "utf8");
const store = {};
const fakeWindow = {
  localStorage: {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: k => { delete store[k]; },
  },
};
const mod = { exports: {} };
new Function("window", "module", "globalThis", src)(fakeWindow, mod, fakeWindow);
const P = fakeWindow.Progress;

let fails = 0;
const eq = (got, exp, msg) => {
  const g = JSON.stringify(got), e = JSON.stringify(exp);
  if (g !== e) { console.log(`  ✗ ${msg}: ожидали ${e}, получили ${g}`); fails++; }
  else console.log(`  ✓ ${msg}`);
};

// ── чистое ядро nextStreak ──
const base = { streak: 5, best: 7, lastDay: "2026-06-10", frozenUsed: false };
eq(P.nextStreak(base, "2026-06-10").streak, 5, "тот же день — серия без изменений");
eq(P.nextStreak(base, "2026-06-11").streak, 6, "следующий день — серия +1");
eq(P.nextStreak(base, "2026-06-12"), { streak: 6, best: 7, lastDay: "2026-06-12", frozenUsed: true }, "пропуск 1 дня — заморозка, серия растёт");
eq(P.nextStreak(base, "2026-06-13").streak, 1, "пропуск 2+ дней — серия сброшена в 1");
eq(P.nextStreak({ streak: 0, best: 0, lastDay: null }, "2026-06-13").streak, 1, "первый день — серия = 1");
eq(P.nextStreak(base, "2026-06-11").best, 7, "best не уменьшается");

// ── дневной счётчик + recordAnswer ──
P.reset();
P.recordAnswer("2026-06-20");
P.recordAnswer("2026-06-20");
eq(P.todayCount("2026-06-20"), 2, "todayCount считает ответы за день");
eq(P.streakInfo("2026-06-20").streak, 1, "после первого дня — streak 1");
P.recordAnswer("2026-06-21");
eq(P.streakInfo("2026-06-21").streak, 2, "второй день подряд — streak 2");

// ── streakInfo обнуляет при долгом пропуске ──
eq(P.streakInfo("2026-06-25").streak, 0, "при заходе через 4 дня — текущая серия 0");
eq(P.streakInfo("2026-06-25").best >= 2, true, "best сохранён");

// ── goal ──
eq(P.getGoal(), 15, "цель по умолчанию 15");
P.setGoal(20); eq(P.getGoal(), 20, "setGoal работает");
P.setGoal(2);  eq(P.getGoal(), 5, "цель не ниже 5");

// ── readiness ──
const qs = [
  { id: "a", topic: "Нав" }, { id: "b", topic: "Нав" },
  { id: "c", topic: "VHF" }, { id: "d", topic: "VHF" },
];
const boxes = { a: 5, b: 5, c: 0, d: null };   // Нав закреплена, VHF слабая
const r = P.readiness(qs, id => boxes[id] === undefined ? null : boxes[id]);
eq(r.topics[0].topic, "VHF", "слабая тема (VHF) сверху");
eq(r.topics.find(t => t.topic === "Нав").pct, 100, "Нав закреплена = 100%");
// общий: (1+1+0+0)/4 = 50%
eq(r.percent, 50, "общий процент готовности = 50");

if (fails) { console.log(`\nPROGRESS CHECK: ${fails} провал(ов)`); process.exit(1); }
console.log("\nPROGRESS CHECK OK");
