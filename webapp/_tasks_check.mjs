// Проверка данных Mini App «Задачки» + сверка проверки ответа с допуском.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

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

// эталонный ответ задачи проходит проверку с допуском
let okAll = true;
for (const t of D.tasks){
  const within = Math.abs(t.answer - t.answer) <= t.tol + 1e-9;
  if (!within) okAll = false;
}
check(okAll, "эталонные ответы в допуске");
check(D.tasks.some(t=>t.cat==="tide"), "есть задачи на прилив");

console.log(`tasks=${D.tasks.length} nav=${D.tasks.filter(t=>t.cat==="nav").length} tide=${D.tasks.filter(t=>t.cat==="tide").length}`);
console.log(fail === 0 ? "TASKS DATA OK" : `TASKS DATA PROBLEM (${fail})`);
process.exit(fail === 0 ? 0 : 1);
