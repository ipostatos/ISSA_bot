// Проверка данных Mini App «Задачки» + сверка проверки ответа с допуском.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { pageCode } from "./_page_code.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const window = {};
new Function("window", readFileSync(join(here, "tasks_data.js"), "utf8"))(window);
const D = window.TASKS_DATA;

let fail = 0;
const check = (c, m) => { if (!c){ console.log("FAIL:", m); fail++; } };

check(D && Array.isArray(D.tasks), "TASKS_DATA.tasks есть");
check(D.tasks.length >= 20, "минимум 20 задач");
let bad = 0;
for (const t of D.tasks){
  if (!t.id || !t.text || !t.solution) bad++;
  if (typeof t.answer !== "number" || typeof t.tol !== "number") bad++;
  if (!["nav","tide"].includes(t.cat)) bad++;
}
check(bad === 0, `все задачи валидны (нарушений: ${bad})`);

// Проверка ответа — НАСТОЯЩИЕ parseAnswer/answerOk/fmt из tasks.html (до волны E
// здесь стояло Math.abs(t.answer - t.answer) — тавтология, всегда 0).
// Человек вводит то, что видит в разборе: ответ в формате страницы (запятая).
const page = pageCode("tasks.html", ["fmt", "parseAnswer", "answerOk"]);
let typedOk = 0, typedBad = [], outsideBad = [];
for (const t of D.tasks){
  const typed = page.parseAnswer(page.fmt(t.answer));
  if (page.answerOk(typed, t)) typedOk++; else typedBad.push(t.id);
  // ответ за пределами допуска обязан не засчитываться
  const off = t.answer + t.tol + Math.max(0.5, t.tol);
  if (page.answerOk(off, t)) outsideBad.push(t.id);
}
check(typedBad.length === 0, `эталонный ответ, введённый как показан («${page.fmt(1.5)}»), засчитывается (не прошли: ${typedBad.join(",")})`);
check(outsideBad.length === 0, `ответ вне допуска не засчитывается (прошли: ${outsideBad.join(",")})`);
check(page.parseAnswer("2,5 ч") === 2.5 && page.parseAnswer("12 м") === 12 && Number.isNaN(page.parseAnswer("abc")),
      "разбор ввода: запятая, единицы «ч»/«м», мусор → NaN");
check(D.tasks.some(t=>t.cat==="tide"), "есть задачи на прилив");

console.log(`tasks=${D.tasks.length} nav=${D.tasks.filter(t=>t.cat==="nav").length} tide=${D.tasks.filter(t=>t.cat==="tide").length}`);
console.log(fail === 0 ? "TASKS DATA OK" : `TASKS DATA PROBLEM (${fail})`);
process.exit(fail === 0 ? 0 : 1);
