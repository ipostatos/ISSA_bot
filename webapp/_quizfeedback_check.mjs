// Проверка обратной связи и навигации в квизе.
// Запуск: node webapp/_quizfeedback_check.mjs
//
// ВАЖНО: логика (buildFeedback/normFeedback) не переписывается здесь копией, а
// ИЗВЛЕКАЕТСЯ из webapp/quiz.html между маркерами __QUIZ_FEEDBACK_HELPERS_*__ и
// исполняется как есть. Иначе чек зеленел бы, даже если страница разъехалась
// с ним (болезнь _solver_check/_marine_check, см. аудит).
import { readFileSync } from "fs";

const quiz = readFileSync(new URL("./quiz.html", import.meta.url), "utf8");
const examPl = readFileSync(new URL("./exam_pl.html", import.meta.url), "utf8");
const dictSrc = readFileSync(new URL("./i18n.dict.js", import.meta.url), "utf8");

let fails = 0;
const ok = (cond, msg) => {
  if (cond) console.log(`  ✓ ${msg}`);
  else { console.log(`  ✗ ${msg}`); fails++; }
};

// ── достаём реальные помощники из страницы ──
const m = quiz.match(/__QUIZ_FEEDBACK_HELPERS_START__[\s\S]*?\*\/([\s\S]*?)\/\*\s*__QUIZ_FEEDBACK_HELPERS_END__/);
if (!m) {
  console.log("  ✗ маркеры __QUIZ_FEEDBACK_HELPERS_*__ не найдены в quiz.html");
  process.exit(1);
}
const { buildFeedback, normFeedback } =
  new Function(m[1] + "\nreturn { buildFeedback, normFeedback };")();

// ── a) expl на месте: в карточке верного варианта разбора нет, он ниже ──
const qWithExpl = {
  answer: 1,
  expl: "Правило 8 требует решительных и своевременных действий.",
  why: ["Нет: это про обгон.", "Верно: Правило 8 требует решительных и своевременных действий.", "Нет: это про огни."]
};
let fb = buildFeedback(qWithExpl, 1);
ok(fb.ok === true, "a) верный ответ распознан");
ok(fb.detail === qWithExpl.expl, "a) подробный разбор берётся из expl");
ok(fb.card === "", "a) в карточке верного варианта разбор НЕ дублируется");

// ── b) expl пуст → фолбэк на why[правильный] ──
const qNoExpl = { answer: 0, expl: "", why: ["Верно: якорь держит за счёт горизонтальной тяги.", "Нет."] };
fb = buildFeedback(qNoExpl, 0);
ok(fb.detail === "Верно: якорь держит за счёт горизонтальной тяги.",
   "b) при пустом expl разбор берётся из why[правильный]");
ok(buildFeedback({ answer: 0, why: ["Только why."] }, 0).detail === "Только why.",
   "b) expl вовсе отсутствует — фолбэк тоже работает");
ok(buildFeedback({ answer: 0 }, 0).detail === "",
   "b) нет ни expl, ни why — пустая строка, без падения");

// ── c) неверный ответ: в карточке why именно выбранного варианта ──
fb = buildFeedback(qWithExpl, 0);
ok(fb.ok === false, "c) неверный ответ распознан");
ok(fb.card === "Нет: это про обгон.", "c) в карточке — why выбранного неверного варианта");
ok(fb.detail === qWithExpl.expl, "c) ниже по-прежнему полный разбор из expl");

// дубль не показываем дважды даже при разном регистре/пунктуации/префиксе
const qDup = {
  answer: 1,
  expl: "MAYDAY — сигнал бедствия при угрозе жизни.",
  why: ["Верно: mayday  —  сигнал бедствия при угрозе жизни!", "ок"]
};
ok(buildFeedback(qDup, 0).card === "",
   "c) совпадающий по смыслу текст не печатается дважды");
ok(normFeedback("Верно: Один и тот же текст.") === normFeedback("один и тот же текст"),
   "c) нормализация снимает префикс «Верно:», регистр и пунктуацию");
ok(buildFeedback({ answer: 1, expl: "Разное.", why: ["Совсем другое пояснение.", "x"] }, 0).card
     === "Совсем другое пояснение.",
   "c) РАЗНЫЙ текст в карточке сохраняется (не съедаем полезное)");

// ── d) CTA стоит выше длинного разбора, на последнем вопросе — «Завершить» ──
const posNext = quiz.indexOf('id="nextBtn"');
const posSkip = quiz.indexOf('id="trainSkip"');
const posExpl = quiz.indexOf('id="expl"');
const posSrc = quiz.indexOf('id="src"');
const posOpts = quiz.indexOf('id="opts"');
ok(posOpts < posSkip && posSkip < posExpl, "d) quiz: «Пропустить» между вариантами и разбором");
ok(posNext < posExpl && posNext < posSrc, "d) quiz: «Далее/Завершить» выше разбора и источника");
ok(/nb\.textContent\s*=\s*last\s*\?\s*I18N\.t\("quizFinishShort"\)/.test(quiz),
   "d) quiz: на последнем вопросе кнопка становится «Завершить»");
// комментарии вырезаем: в них слово sticky упомянуто намеренно (объяснение, почему его нет)
const ctaZone = quiz.slice(posOpts, posExpl).replace(/<!--[\s\S]*?-->/g, "");
ok(!/position:\s*sticky/.test(ctaZone),
   "d) quiz: CTA в обычном потоке (без sticky — safe-area в Telegram iOS)");
const plOpts = examPl.indexOf('id="opts"');
const plCtl = examPl.indexOf('id="controls"');
const plLamp = examPl.indexOf('id="lamp"');
ok(plOpts < plCtl && plCtl < plLamp, "d) exam_pl: навигация между вариантами и «лампочкой»");
ok(/last\s*\?\s*I18N\.t\("quizFinishShort"\)/.test(examPl),
   "d) exam_pl: на последнем вопросе тренировки — «Завершить» (паритет с quiz)");

// ── e) счётчик верных локализован во всех языках и не захардкожен ──
const langs = ["ru", "pl", "ua", "en"];
// строку словаря берём целиком (внутри значений есть «{n}», по «}» резать нельзя)
const keyLine = dictSrc.split("\n").find(l => /quizLiveCorrect\s*:/.test(l));
ok(!!keyLine, "e) ключ quizLiveCorrect есть в словаре");
if (keyLine) {
  langs.forEach(l => {
    const v = keyLine.match(new RegExp(l + '\\s*:\\s*"([^"]*)"'));
    ok(!!v && v[1].includes("{n}"), `e) ${l}: перевод есть и содержит подстановку {n}`);
  });
}
ok(/I18N\.t\("quizLiveCorrect"/.test(quiz), "e) страница берёт подпись из словаря");
// ни одна строка кода, пишущая в счётчик, не содержит кириллицы напрямую
const liveLines = quiz.split("\n").filter(l => /liveScore/.test(l) && !/^\s*(\/\/|<!--|\*)/.test(l));
ok(liveLines.length > 0 && liveLines.every(l => !/[А-Яа-яЁё]/.test(l)),
   "e) русский текст счётчика не захардкожен (подпись только через словарь)");

// ── общая гигиена: варианты кликаются во всю ширину и видимы как кнопки ──
ok(/\.opt\{[^}]*width:100%/.test(quiz.replace(/\s/g, "").replace(/\{/g, "{")) ||
   /\.opt\{[^}]*display:block[^}]*width:100%/.test(quiz.replace(/\n/g, "")),
   "варианты в quiz.html — во всю ширину");
ok(/\.opt:focus-visible/.test(quiz) && /\.opt:focus-visible/.test(examPl),
   "фокус с клавиатуры виден на обеих страницах");
ok(/\.opt:not\(\[disabled\]\):active/.test(quiz) && /\.opt:not\(\.lock\):active/.test(examPl),
   "нажатое состояние есть на обеих страницах");
ok(/role="button"/.test(examPl) && /keydown/.test(examPl),
   "exam_pl: вариант объявлен кнопкой и отвечает на Enter/Space");

if (fails) { console.log(`\nQUIZ FEEDBACK CHECK: ${fails} провал(ов)`); process.exit(1); }
console.log("\nQUIZ FEEDBACK CHECK OK");
