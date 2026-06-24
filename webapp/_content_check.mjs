// Проверка данных Mini App «Шпаргалки» и «Задачи T-V-M-D-C».
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const window = {};
new Function("window", readFileSync(join(here, "content_data.js"), "utf8"))(window);
const D = window.CONTENT_DATA;

let fail = 0;
const check = (c, m) => { if (!c){ console.log("FAIL:", m); fail++; } };

check(D && Array.isArray(D.sheets), "sheets есть");
check(D.sheets.length >= 9, "минимум 9 шпаргалок");
check(Array.isArray(D.navTasks) && D.navTasks.length >= 50, "минимум 50 задач T-V-M-D-C");

// шпаргалка узлов содержит карточки с шагами-фото
const kn = D.sheets.find(s => s.key === "knots");
check(kn && Array.isArray(kn.knots) && kn.knots.length >= 5, "узлы: >=5 карточек");
check(kn.knots.every(k => k.steps.length >= 3), "узлы: у каждого >=3 шага");

// задачи валидны + есть со звёздочкой
let bad = 0;
for (const t of D.navTasks){
  if (!t.id || !t.text || typeof t.answer !== "number" || !t.solution) bad++;
}
check(bad === 0, `задачи валидны (нарушений: ${bad})`);
check(D.navTasks.some(t => t.starred), "есть задачи со звёздочкой");

console.log(`sheets=${D.sheets.length} navTasks=${D.navTasks.length} knots=${kn?kn.knots.length:0} sizeKB=${Math.round(readFileSync(join(here,"content_data.js")).length/1024)}`);
console.log(fail === 0 ? "CONTENT DATA OK" : `CONTENT DATA PROBLEM (${fail})`);
process.exit(fail === 0 ? 0 : 1);
