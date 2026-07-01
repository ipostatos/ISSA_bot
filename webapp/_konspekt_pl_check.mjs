// Проверка польского конспекта (Żeglarz + Sternik): целостность konspekt_pl_data.js,
// покрытие банков через q2topic («лампочка-источник»), сбалансированность тегов,
// свежесть данных относительно банков.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));

function load(file, global) {
  const src = readFileSync(join(here, file), "utf8");
  const window = {};
  new Function("window", src)(window);
  return window[global];
}

let fail = 0;
const check = (cond, msg) => { if (!cond) { console.log("  FAIL:", msg); fail++; } };

const K = load("konspekt_pl_data.js", "KONSPEKT_PL_DATA");
const ZJ = load("zeglarz_data.js", "ZEGLARZ_DATA");
const ST = load("sternik_data.js", "STERNIK_DATA");

console.log("— konspekt_pl_data.js —");
check(K && Array.isArray(K.topics), "есть .topics");
check(K && K.q2topic && typeof K.q2topic === "object", "есть .q2topic");

// 7 тем в фиксированном порядке
const ORDER = ["budowa", "teoria", "manewry", "locja", "ratownictwo", "meteo", "przepisy"];
const keys = (K.topics || []).map(t => t.key);
check(keys.length === 7, `тем 7 (факт ${keys.length})`);
for (const k of ORDER) check(keys.includes(k), `тема «${k}» на месте`);

// каждая тема нетривиальна: заголовок, непустой html/text, сбалансированные <b>
for (const t of (K.topics || [])) {
  check(typeof t.title === "string" && t.title.length > 3, `тема ${t.key}: есть title`);
  check(typeof t.html === "string" && t.html.length > 300, `тема ${t.key}: html нетривиален`);
  check(typeof t.text === "string" && t.text.length > 200, `тема ${t.key}: text для поиска`);
  const ob = (t.html.match(/<b>/g) || []).length;
  const cb = (t.html.match(/<\/b>/g) || []).length;
  check(ob === cb, `тема ${t.key}: теги <b> сбалансированы (${ob}/${cb})`);
}

// q2topic: все id существуют в банках, все значения — валидные ключи тем
const bankIds = new Set([
  ...(ZJ?.questions || []).map(q => q.id),
  ...(ST?.questions || []).map(q => q.id),
]);
const keySet = new Set(keys);
let badId = 0, badKey = 0;
for (const [qid, tkey] of Object.entries(K.q2topic || {})) {
  if (!bankIds.has(qid)) { badId++; if (badId <= 5) console.log("    q2topic: неизвестный id", qid); }
  if (!keySet.has(tkey)) { badKey++; if (badKey <= 5) console.log("    q2topic: неизвестная тема", tkey); }
}
check(badId === 0, `все id из q2topic есть в банках (лишних: ${badId})`);
check(badKey === 0, `все темы из q2topic валидны (неизвестных: ${badKey})`);

// покрытие: каждый вопрос обоих банков должен иметь разбор (лампочку)
const covered = new Set(Object.keys(K.q2topic || {}));
const uncovered = [...bankIds].filter(id => !covered.has(id));
check(uncovered.length === 0,
  `все вопросы покрыты конспектом (без разбора: ${uncovered.length}${uncovered.length ? " → " + uncovered.slice(0, 8).join(",") : ""})`);

if (fail) { console.log(`\nKONSPEKT_PL CHECK: ${fail} провал(ов)`); process.exit(1); }
console.log(`\nKONSPEKT_PL CHECK OK — 7 тем, ${Object.keys(K.q2topic).length} вопросов с разбором`);
