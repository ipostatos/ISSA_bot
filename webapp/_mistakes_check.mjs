// Проверка журнала ошибок (mistakes.js): пороги входа/выхода, сброс серии.
// Запуск: node webapp/_mistakes_check.mjs
import { readFileSync } from "fs";

const src = readFileSync(new URL("./mistakes.js", import.meta.url), "utf8");
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
const M = fakeWindow.Mistakes;

let fails = 0;
const eq = (got, exp, msg) => {
  const g = JSON.stringify(got), e = JSON.stringify(exp);
  if (g !== e) { console.log(`  ✗ ${msg}: ожидали ${e}, получили ${g}`); fails++; }
  else console.log(`  ✓ ${msg}`);
};

M.reset();
M.record("q1", false);
eq(M.list(), [], "одна ошибка — ещё не в журнале (шум)");
M.record("q1", false);
eq(M.list(), ["q1"], "вторая ошибка — вопрос в журнале");
eq(M.wrongCount("q1"), 2, "счётчик ошибок ведётся");

M.record("q1", true);
eq(M.list(), ["q1"], "один верный — ещё в журнале");
M.record("q1", true);
eq(M.list(), [], "два верных ПОДРЯД — вопрос закреплён и покинул журнал");

M.record("q2", false);
M.record("q2", false);
M.record("q2", true);
M.record("q2", false);   // ошибка сбрасывает серию верных
M.record("q2", true);
eq(M.list(), ["q2"], "ошибка сбрасывает серию верных — вопрос остаётся");

M.record("q3", true);
M.record("q3", true);
eq(M.wrongCount("q3"), 0, "верные ответы без ошибок журнал не раздувают");
eq(M.count(), 1, "count() считает только текущий журнал");

if (fails) { console.log(`\nMISTAKES CHECK: ${fails} провал(ов)`); process.exit(1); }
console.log("\nMISTAKES CHECK OK");
