// Проверка данных Mini App «Конспект».
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const window = {};
new Function("window", readFileSync(join(here, "konspekt_data.js"), "utf8"))(window);
const D = window.KONSPEKT_DATA;

let fail = 0;
const check = (c, m) => { if (!c){ console.log("FAIL:", m); fail++; } };

check(D && Array.isArray(D.topics), "KONSPEKT_DATA.topics есть");
check(D.topics.length >= 10, "минимум 10 тем");
let bad = 0;
for (const t of D.topics){
  if (!t.key || !t.title || !t.html || !t.text) bad++;
  if (!Array.isArray(t.images)) bad++;
  // text должен быть без HTML-тегов
  if (/<[a-z]/i.test(t.text)) bad++;
}
check(bad === 0, `все темы валидны (нарушений: ${bad})`);

// поиск находит характерное слово
const hasMast = D.topics.some(t => t.text.toLowerCase().includes("мачт"));
check(hasMast, "поиск: слово «мачт» встречается");

console.log(`topics=${D.topics.length} sizeKB=${Math.round(readFileSync(join(here,"konspekt_data.js")).length/1024)}`);
console.log(fail === 0 ? "KONSPEKT DATA OK" : `KONSPEKT DATA PROBLEM (${fail})`);
process.exit(fail === 0 ? 0 : 1);
