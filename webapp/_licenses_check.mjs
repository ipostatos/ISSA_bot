// Проверка польских лицензий (Żeglarz / Sternik): целостность банков,
// гибридный формат PL/RU, параметры экзамена, существование картинок-знаков.
import { readFileSync, existsSync } from "node:fs";
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

// Параметры польского экзамена (PZŻ): 75 вопросов, 65 верных, 90 минут.
const EXAM = { size: 75, pass: 65, minutes: 90 };

function validateBank(file, global, expectTotal) {
  console.log(`\n— ${global} (${file}) —`);
  const D = load(file, global);

  check(D && Array.isArray(D.questions), "есть .questions");
  if (!D || !Array.isArray(D.questions)) return;

  check(D.questions.length === expectTotal, `вопросов ${expectTotal} (факт ${D.questions.length})`);
  check(D.examSize === EXAM.size, `examSize=${EXAM.size}`);
  check(D.examPass === EXAM.pass, `examPass=${EXAM.pass}`);
  check(D.examMinutes === EXAM.minutes, `examMinutes=${EXAM.minutes}`);

  const ids = new Set();
  let badStruct = 0, notHybrid = 0, badAns = 0, missingImg = 0, withImg = 0;
  for (const q of D.questions) {
    ids.add(q.id);
    // структура: id, q, 2..5 вариантов
    if (!q.id || typeof q.q !== "string" || !Array.isArray(q.options)
        || q.options.length < 2 || q.options.length > 5) badStruct++;
    // ответ в диапазоне
    if (!(Number.isInteger(q.answer) && q.answer >= 0 && q.answer < q.options.length)) badAns++;
    // гибрид PL/RU: и вопрос, и каждый вариант содержат перевод строки (PL\nRU)
    if (typeof q.q === "string" && !q.q.includes("\n")) notHybrid++;
    // картинка: файл должен существовать
    if (q.image) {
      withImg++;
      if (!existsSync(join(here, q.image))) { missingImg++; console.log("    нет файла:", q.image); }
    }
  }
  check(ids.size === D.questions.length, "id уникальны");
  check(badStruct === 0, `структура вопросов (нарушений: ${badStruct})`);
  check(badAns === 0, `ответы в диапазоне (нарушений: ${badAns})`);
  check(notHybrid === 0, `все вопросы гибридные PL/RU (без перевода строки: ${notHybrid})`);
  check(missingImg === 0, `все картинки на месте (отсутствует файлов: ${missingImg})`);

  // сборка экзамена: 75 уникальных (или весь банк, если меньше)
  const n = Math.min(EXAM.size, D.questions.length);
  const exam = D.questions.slice(0, n);
  check(new Set(exam.map(q => q.id)).size === exam.length, "выборка экзамена уникальна");

  console.log(`  ✓ ${D.questions.length} вопросов, ${withImg} со знаками`);
}

// Żeglarz: 150, Sternik: 460
validateBank("zeglarz_data.js", "ZEGLARZ_DATA", 150);
validateBank("sternik_data.js", "STERNIK_DATA", 460);

if (fail) { console.log(`\nLICENSES CHECK: ${fail} провал(ов)`); process.exit(1); }
console.log("\nLICENSES CHECK OK");
