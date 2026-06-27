// Проверка логики бейджей: открытие по метрикам, прогресс, checkNew.
// Запуск: node webapp/_badges_check.mjs
import { readFileSync } from "fs";

const src = readFileSync(new URL("./badges.js", import.meta.url), "utf8");
const store = {};
const fake = {
  localStorage: {
    getItem: k => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
  },
};
const mod = { exports: {} };
new Function("window", "module", "globalThis", src)(fake, mod, fake);
const B = fake.Badges;

let fails = 0;
const ok = (cond, msg) => { console.log((cond ? "  ✓ " : "  ✗ ") + msg); if (!cond) fails++; };

const zero = { answered: 0, streak: 0, best: 0, learned: 0, topicsDone: 0, topicsTotal: 15, ready: 0, examPass: false, flawless: false };
let l = B.list(zero);
ok(l.every(b => !b.unlocked), "при нулевых метриках ничего не открыто");
ok(B.unlockedCount(zero) === 0, "unlockedCount = 0");

const some = { answered: 120, streak: 8, best: 8, learned: 60, topicsDone: 1, topicsTotal: 15, ready: 40, examPass: false, flawless: false };
const byId = Object.fromEntries(B.list(some).map(b => [b.id, b]));
ok(byId.first_steps.unlocked, "Юнга открыт (answered>=1)");
ok(byId.answered_100.unlocked, "Матрос открыт (answered>=100)");
ok(!byId.answered_500.unlocked, "Боцман закрыт (answered<500)");
ok(byId.streak_7.unlocked, "Попутный ветер открыт (best>=7)");
ok(byId.anchor_watch.unlocked === false, "Якорная вахта закрыта (best<14)");
ok(byId.learned_50.unlocked, "Штурман открыт (learned>=50)");
ok(byId.topic_master.unlocked, "Знаток темы открыт (topicsDone>=1)");
ok(!byId.all_topics.unlocked, "Лоцман закрыт (не все темы)");
ok(Math.abs(byId.answered_500.progress - 120/500) < 1e-9, "прогресс Боцмана = 120/500");

const full = { answered: 600, streak: 31, best: 31, learned: 999, topicsDone: 15, topicsTotal: 15, ready: 95, examPass: true, flawless: true };
ok(B.unlockedCount(full) === B.DEFS.length, "при максимуме открыты все");

// checkNew: первый вызов — новые; второй — пусто
store["issa_badges_seen_v1"] = JSON.stringify({});
const fresh1 = B.checkNew(some);
ok(fresh1.length > 0, "checkNew первый раз возвращает новые");
const fresh2 = B.checkNew(some);
ok(fresh2.length === 0, "checkNew второй раз — пусто (уже показаны)");

if (fails) { console.log(`\nBADGES CHECK: ${fails} провал(ов)`); process.exit(1); }
console.log("\nBADGES CHECK OK");
