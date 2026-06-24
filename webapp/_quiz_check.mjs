// Проверка Mini App «Тесты»: данные банка, сборка экзамена, размер payload.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, "quiz_data.js"), "utf8");

// эмулируем window и выполняем сгенерированный файл
const window = {};
new Function("window", src)(window);
const D = window.QUIZ_DATA;

let fail = 0;
const check = (cond, msg) => { if (!cond){ console.log("FAIL:", msg); fail++; } };

check(D && Array.isArray(D.questions), "QUIZ_DATA.questions есть");
check(D.questions.length > 0, "вопросы не пустые");
check(D.examSize === 100, "examSize=100");
check(D.passPercent === 75, "passPercent=75");
check(Array.isArray(D.topics) && D.topics.length > 0, "темы есть");

// каждый вопрос валиден
let badQ = 0;
for (const q of D.questions){
  if (!q.id || !q.q || !Array.isArray(q.options) || q.options.length !== 4) badQ++;
  if (!(Number.isInteger(q.answer) && q.answer >= 0 && q.answer < 4)) badQ++;
}
check(badQ === 0, `все вопросы валидны (нарушений: ${badQ})`);

// сборка экзамена: 100 уникальных
const shuffle = a => { a=a.slice(); for(let i=a.length-1;i>0;i--){const j=(i*7+3)%(i+1);[a[i],a[j]]=[a[j],a[i]];} return a; };
const exam = shuffle(D.questions).slice(0, Math.min(D.examSize, D.questions.length));
check(exam.length === Math.min(100, D.questions.length), "экзамен = 100 (или весь банк)");
check(new Set(exam.map(q=>q.id)).size === exam.length, "вопросы экзамена уникальны");

// симуляция прохождения: ответы (каждый 3-й неверно), payload
const results = exam.map((q,i) => [q.id, (i % 3 === 0) ? 0 : 1]);
const correct = results.filter(([,ok])=>ok).length;
const payload = { t:"quiz", mode:"exam", n:exam.length, ok:correct, results, secs:734 };
const json = JSON.stringify(payload);
check(json.length < 4096, `payload влезает в лимит sendData (${json.length} байт < 4096)`);

// дамп payload для python-теста
process.stdout.write(json.length < 4096 ? "" : "");
console.log(`questions=${D.questions.length} topics=${D.topics.length} examPayload=${json.length}B correct=${correct}/${exam.length}`);
console.log(fail === 0 ? "QUIZ DATA OK" : `QUIZ DATA PROBLEM (${fail})`);
process.exit(fail === 0 ? 0 : 1);
