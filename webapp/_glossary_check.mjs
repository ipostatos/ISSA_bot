// Проверка данных Mini App «Словарь».
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const window = {};
new Function("window", readFileSync(join(here, "glossary_data.js"), "utf8"))(window);
const D = window.GLOSSARY_DATA;

let fail = 0;
const check = (c, m) => { if (!c){ console.log("FAIL:", m); fail++; } };

check(D && Array.isArray(D.categories), "GLOSSARY_DATA.categories есть");
check(D.categories.length >= 10, "минимум 10 категорий");
const total = D.categories.reduce((s,c)=>s+c.terms.length, 0);
check(total === D.total, `total совпадает (${total} == ${D.total})`);
check(total >= 150, `минимум 150 терминов (${total})`);

let bad = 0;
for (const c of D.categories){
  if (!c.key || !c.title || !Array.isArray(c.terms)) bad++;
  for (const t of c.terms){
    if (!t.term || !t.definition) bad++;
    if (!Array.isArray(t.aliases)) bad++;
  }
}
check(bad === 0, `все термины валидны (нарушений: ${bad})`);

// поиск по английскому синониму работает (например deck)
const hasDeck = D.categories.some(c => c.terms.some(t =>
  (t.aliases||[]).some(a => a.toLowerCase()==="deck")));
check(hasDeck, "есть английский синоним deck");

console.log(`terms=${total} cats=${D.categories.length} sizeKB=${Math.round(readFileSync(join(here,"glossary_data.js")).length/1024)}`);
console.log(fail === 0 ? "GLOSSARY DATA OK" : `GLOSSARY DATA PROBLEM (${fail})`);
process.exit(fail === 0 ? 0 : 1);
