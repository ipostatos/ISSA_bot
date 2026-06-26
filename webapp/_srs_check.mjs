// Проверка логики SRS (Leitner): переходы коробок и due, dueCount/pickDue.
// Запуск: node webapp/_srs_check.mjs
import { readFileSync } from "fs";

// загружаем srs.js в подменённое окружение с фейковым localStorage
const src = readFileSync(new URL("./srs.js", import.meta.url), "utf8");
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
const SRS = fakeWindow.SRS;

let fails = 0;
const eq = (got, exp, msg) => {
  const g = JSON.stringify(got), e = JSON.stringify(exp);
  if (g !== e) { console.log(`  ✗ ${msg}: ожидали ${e}, получили ${g}`); fails++; }
  else console.log(`  ✓ ${msg}`);
};

const T0 = 1_000_000_000_000;        // фиксированное «сейчас» для детерминизма
const I = SRS.INTERVALS;

// 1. чистое ядро: верный ответ поднимает коробку
eq(SRS.nextState(undefined, true, T0), { box: 1, due: T0 + I[1] }, "новый+верно → box1");
eq(SRS.nextState({ box: 1, due: 0 }, true, T0), { box: 2, due: T0 + I[2] }, "box1+верно → box2");
// 2. ошибка сбрасывает в box0
eq(SRS.nextState({ box: 4, due: 0 }, false, T0), { box: 0, due: T0 + I[0] }, "box4+ошибка → box0");
// 3. потолок коробки
eq(SRS.nextState({ box: 5, due: 0 }, true, T0), { box: 5, due: T0 + I[5] }, "box5+верно → остаётся box5");

// 4. grade пишет в хранилище и читается обратно
SRS.reset();
SRS.grade("q1", true, T0);
eq(SRS.state("q1"), { box: 1, due: T0 + I[1] }, "grade сохраняет состояние");

// 5. isDue: невиданный — пора; свежеотвеченный — нет; просроченный — пора
eq(SRS.isDue("new-q", T0), true, "невиданный вопрос → пора");
eq(SRS.isDue("q1", T0), false, "только что отвеченный → не пора");
eq(SRS.isDue("q1", T0 + I[1] + 1), true, "после интервала → снова пора");

// 6. dueCount: из [q1(не пора), q2(невиданный), q3(невиданный)] пора 2
eq(SRS.dueCount(["q1", "q2", "q3"], T0), 2, "dueCount считает невиданные + просроченные");

// 7. pickDue: просроченный с низкой коробкой раньше невиданных
SRS.reset();
SRS.grade("a", false, T0 - I[0] - 1000);   // box0, просрочен
SRS.grade("b", true,  T0 - I[1] - 1000);   // box1, просрочен (выше коробка)
const order = SRS.pickDue(["a", "b", "c"], 3, T0);
eq(order[0], "a", "pickDue: низкая коробка (a) первой");
eq(order.includes("c"), true, "pickDue: невиданный (c) включён");
eq(order[order.length - 1], "c", "pickDue: невиданный в конце");

// 8. stats
SRS.reset();
SRS.grade("x", true, T0); SRS.grade("x", true, T0); // box2
SRS.grade("y", true, T0);                            // box1
const st = SRS.stats(["x", "y", "z"]);
eq(st.started, 2, "stats.started = 2 (z не начат)");
eq(st.total, 3, "stats.total = 3");

if (fails) { console.log(`\nSRS CHECK: ${fails} провал(ов)`); process.exit(1); }
console.log("\nSRS CHECK OK");
