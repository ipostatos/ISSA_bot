// Сторож клиентских грабель Telegram WebView. Основное — нативные диалоги
// (ниже), в конце файла — родственный класс: событие, повешенное не на тот
// объект (pagehide на document не срабатывает никогда).
//
// Нативные диалоги: в iOS-клиенте Telegram (WKWebView) confirm/alert/
// prompt подавляются. confirm() при этом НЕ падает, а мгновенно возвращает
// false — кнопка «Завершить»/«Выйти» просто молчит, и отличить «отмена» от
// «диалога не было» невозможно. Так дважды ломался выход из экзамена.
//
// Правило: в страницах и модулях Mini App нельзя вызывать нативные диалоги
// напрямую — только askConfirm()/showNote() из nav.js (они уходят в
// Telegram.WebApp.showConfirm/showAlert, а в обычном браузере падают на
// нативный диалог). Единственное исключение — сам nav.js, где фолбэк и живёт.
//
// Запуск: node webapp/_dialogs_check.mjs
import { readdirSync, readFileSync } from "fs";

const dir = new URL("./", import.meta.url);
let fails = 0;
const ok = (cond, msg) => {
  if (cond) console.log(`  ✓ ${msg}`);
  else { console.log(`  ✗ ${msg}`); fails++; }
};

// Комментарии вырезаем: слово confirm в пояснении — не вызов. Нужны все три
// вида: HTML-комментарий, блочный и строчный (последний — с флагом m, иначе
// `^` совпадёт только с началом файла).
function stripComments(src) {
  return src
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .replace(/^\s*\/\/[^\n]*/gm, " ")
    .replace(/([^:"'`\\])\/\/[^\n]*/g, "$1 ");
}

// Аргументы вызова с учётом вложенных скобок: наивный /\([^)]*\)/ обрывается
// на первой закрывающей и не видит второй аргумент.
function callArgs(src, fname) {
  const out = [];
  let from = 0;
  for (;;) {
    const at = src.indexOf(fname + "(", from);
    if (at < 0) break;
    let i = at + fname.length, depth = 0;
    for (; i < src.length; i++) {
      if (src[i] === "(") depth++;
      else if (src[i] === ")") { depth--; if (!depth) break; }
    }
    out.push(src.slice(at, i + 1));
    from = i + 1;
  }
  return out;
}

const files = readdirSync(dir)
  .filter((f) => (f.endsWith(".html") || f.endsWith(".js")) && !f.startsWith("_"))
  .filter((f) => f !== "nav.js")                 // здесь фолбэк разрешён
  .filter((f) => !f.endsWith("_data.js") && f !== "i18n.dict.js");

const CALL = /(^|[^.\w$])(confirm|alert|prompt)\s*\(/;
const offenders = [];
for (const f of files) {
  const src = stripComments(readFileSync(new URL(f, dir), "utf8"));
  src.split("\n").forEach((line, i) => {
    if (CALL.test(line)) offenders.push(`${f}:${i + 1}: ${line.trim().slice(0, 90)}`);
  });
}
ok(offenders.length === 0,
   `нативных confirm/alert/prompt нет ни в одной странице (проверено файлов: ${files.length})`);
if (offenders.length) offenders.forEach((o) => console.log(`      ${o}`));

// nav.js обязан предоставлять обёртки — иначе вызовы выше просто упадут
const nav = readFileSync(new URL("nav.js", dir), "utf8");
ok(/window\.askConfirm\s*=/.test(nav), "nav.js определяет window.askConfirm");
ok(/window\.showNote\s*=/.test(nav), "nav.js определяет window.showNote");
// обёртки должны быть ДО раннего выхода `if (!tg) return`, иначе вне Telegram
// (обычный браузер, тесты) их не существует
// Ищем именно ВЕРХНЕУРОВНЕВЫЙ `if (!tg) return;` (отступ ровно 2 пробела) —
// такая же строка есть внутри setBusy, и по ней сравнивать нельзя.
const navStripped = stripComments(nav);
const earlyReturn = navStripped.search(/\n {2}if \(!tg\) return;/);
ok(earlyReturn > 0 && navStripped.indexOf("window.askConfirm") < earlyReturn,
   "askConfirm объявлен до раннего return (работает и без Telegram)");
ok(/tg\.showConfirm/.test(nav) && /tg\.showAlert/.test(nav),
   "обёртки используют диалоги Telegram, а не только нативные");

// ── поведение askConfirm в четырёх средах (исполняем настоящий nav.js) ──
// Эмулируем окружение так же, как _sw_check.mjs эмулирует service worker.
function runNav(webApp) {
  const win = { Telegram: webApp ? { WebApp: webApp } : undefined,
                confirm: () => { win._nativeConfirmCalled = true; return true; },
                alert: () => { win._nativeAlertCalled = true; } };
  const doc = { querySelector: () => null, createElement: () => ({}),
                head: { appendChild() {} }, currentScript: null, addEventListener() {} };
  new Function("window", "document", "navigator", nav)(win, doc, {});
  return win;
}

// 1) современный клиент Telegram: спрашиваем через его диалог
{
  let asked = null;
  const win = runNav({
    isVersionAtLeast: (v) => parseFloat(v) <= 7.0,
    showConfirm: (msg, cb) => { asked = msg; cb(true); },
    showAlert: () => {},
  });
  const got = await win.askConfirm("выйти?");
  ok(asked === "выйти?" && got === true, "Telegram 7.0: вопрос уходит в showConfirm, ответ возвращается");
  ok(!win._nativeConfirmCalled, "Telegram 7.0: нативный confirm не вызывается");
}
// 2) старый клиент (6.0): метод в объекте ЕСТЬ, но не поддержан — на нём
//    ловился «Method showPopup is not supported in version 6.0»
{
  let called = false;
  const win = runNav({
    isVersionAtLeast: (v) => parseFloat(v) <= 6.0,
    showConfirm: () => { called = true; throw new Error("Method showPopup is not supported in version 6.0"); },
  });
  const out = await win.askConfirm("выйти?", { fallback: true });
  ok(out === true && !called,
     "Telegram 6.0: showConfirm даже не вызывается, fallback:true выпускает пользователя");
  ok(await win.askConfirm("удалить?") === false,
     "Telegram 6.0 без fallback: считаем за «нет» (ничего не ломаем молча)");
}
// 3) клиент вообще без showConfirm
{
  const win = runNav({ isVersionAtLeast: () => true });
  ok(await win.askConfirm("выйти?", { fallback: true }) === true,
     "клиент без showConfirm: fallback:true выпускает пользователя");
}
// 4) обычный браузер (Telegram нет) — нативный confirm работает и им пользуемся
{
  const win = runNav(null);
  ok(await win.askConfirm("выйти?") === true && win._nativeConfirmCalled === true,
     "браузер без Telegram: используется нативный confirm");
  win.showNote("привет");
  ok(win._nativeAlertCalled === true, "браузер без Telegram: showNote падает на alert");
}

// Места, где отказ диалога запирает пользователя, обязаны просить fallback:true
for (const [file, what] of [["exam_pl.html", "выход из польского экзамена"],
                            ["quiz.html", "завершение теста"]]) {
  const src = readFileSync(new URL(file, dir), "utf8");
  const calls = callArgs(stripComments(src), "askConfirm");
  ok(calls.length > 0 && calls.every((c) => /fallback\s*:\s*true/.test(c)),
     `${file}: ${what} не запирает пользователя (fallback:true во всех askConfirm)`);
}

// ── вторая грабля того же класса: событие повешено не на тот объект ──
// pagehide приходит на window. Повешенный на document обработчик не сработает
// НИКОГДА и не сообщит об этом: в cams.html из-за этого HLS-поток (~1,5 ГБ/ч)
// продолжал качаться после сворачивания приложения.
const badPagehide = [];
for (const f of files) {
  const src = stripComments(readFileSync(new URL(f, dir), "utf8"));
  if (/document\.addEventListener\(\s*["']pagehide/.test(src)) badPagehide.push(f);
}
ok(badPagehide.length === 0, "pagehide нигде не повешен на document (он приходит на window)");
if (badPagehide.length) badPagehide.forEach((f) => console.log(`      ${f}`));

// Страницы с тяжёлым медиа обязаны глушить его при уходе — и по pagehide,
// и по visibilitychange (при сворачивании Telegram pagehide может не прийти).
const cams = stripComments(readFileSync(new URL("cams.html", dir), "utf8"));
ok(/window\.addEventListener\(\s*["']pagehide/.test(cams),
   "cams.html: поток глушится по window pagehide");
ok(/addEventListener\(\s*["']visibilitychange/.test(cams) && /visibilityState\s*===\s*["']hidden/.test(cams),
   "cams.html: поток глушится и при сворачивании (visibilitychange)");

if (fails) { console.log(`\nDIALOGS CHECK: ${fails} провал(ов)`); process.exit(1); }
console.log("\nDIALOGS CHECK OK");
