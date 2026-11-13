// Сторож шва «Библиотека»: каталог book.html → читалка reader.html → деплой.
//
// С 02.07 по 13.11.2026 не открывалась ни одна книга: читалка пускала только
// "books/<имя>.pdf", а каталог передавал "book.pdf". Каждая половина по
// отдельности была «правильной», ломался именно шов — и смоук, проверявший
// только отдачу PDF, был зелёным. Здесь проверяется весь путь:
//   1) каждый file из каталога проходит белый список читалки (safeBookPath,
//      исполняется настоящая функция из reader.html, а не её копия);
//   2) белый список по-прежнему режет чужие и обходные пути;
//   3) деплой копирует каждую книгу каталога туда, откуда её запросит читалка.
//
// Запуск: node webapp/_library_check.mjs
import { readFileSync } from "fs";

const dir = new URL("./", import.meta.url);
const read = (rel) => readFileSync(new URL(rel, dir), "utf8");
let fails = 0;
const ok = (cond, msg) => {
  if (cond) console.log(`  ✓ ${msg}`);
  else { console.log(`  ✗ ${msg}`); fails++; }
};

const catalog = [...read("book.html").matchAll(/file:\s*"([^"]+)"/g)].map((m) => m[1]);
ok(catalog.length > 0, `каталог книг не пуст (${catalog.join(", ")})`);

const reader = read("reader.html");
const m = reader.match(/function safeBookPath\(f\)\{[\s\S]*?\n\}/);
ok(!!m, "в reader.html есть safeBookPath");
const safeBookPath = m ? new Function(`${m[0]}; return safeBookPath;`)() : () => "";

for (const f of catalog) {
  ok(safeBookPath(f) === f, `читалка принимает книгу каталога «${f}»`);
}

for (const bad of ["https://evil.example/x.pdf", "//evil.example/x.pdf", "../x.pdf",
                   "books/../x.pdf", "x.pdf?y=1", "javascript:x.pdf", "книга.pdf", ""]) {
  ok(safeBookPath(bad) === "", `белый список режет «${bad}»`);
}

// Деплой: книга должна лечь в каталог раздачи под тем же путём, что в каталоге.
const deploy = read("../deploy/update_webapp.sh");
const loop = deploy.match(/for f in ([^;]+); do\s*\n\s*if \[ -f "\$BOOKS_SRC\/\$f" \]/);
ok(!!loop, "в update_webapp.sh есть цикл копирования книг");
const deployed = loop ? loop[1].trim().split(/\s+/) : [];
ok(/cp -f "\$BOOKS_SRC\/\$f" "\$DST\/\$f"/.test(deploy), "книги копируются в корень раздачи ($DST/<имя>)");
for (const f of catalog) {
  ok(!f.includes("/") && deployed.includes(f), `деплой публикует «${f}» туда, где её ищет читалка`);
}

// pdf.js 3.11.174 уязвим к CVE-2024-4367 (исправлено в 4.2.67): вредоносный
// шрифт в PDF приводил к eval произвольного JS в origin Mini App. Смягчение —
// isEvalSupported:false в КАЖДОМ вызове getDocument. Пока версия ниже 4.2.67,
// пропажа флага — провал (обновление pdf.js на 4.x — отдельная работа: другая
// сборка, ES-модули).
const pdfVer = (read("vendor/pdfjs/pdf.min.js").match(/version="(\d+)\.(\d+)\.(\d+)"/) || []).slice(1).map(Number);
ok(pdfVer.length === 3, `версия pdf.js определяется (${pdfVer.join(".")})`);
const patched = pdfVer[0] > 4 || (pdfVer[0] === 4 && (pdfVer[1] > 2 || (pdfVer[1] === 2 && pdfVer[2] >= 67)));
const calls = [...reader.matchAll(/getDocument\(\{([\s\S]*?)\}\)/g)].map((x) => x[1]);
ok(calls.length > 0, "в reader.html есть вызов getDocument");
if (!patched) {
  ok(calls.every((c) => /isEvalSupported\s*:\s*false/.test(c)),
     "pdf.js < 4.2.67: каждый getDocument с isEvalSupported:false (CVE-2024-4367)");
}

if (fails) {
  console.log(`\n✗ library: ${fails} провал(ов)`);
  process.exit(1);
}
console.log("\n✓ library OK");
