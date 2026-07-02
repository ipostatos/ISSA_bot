// Проверка JS-merge в sync.js — должен совпадать с серверным api/merge.py.
// Запуск: node webapp/_sync_check.mjs
import { readFileSync } from "fs";

const src = readFileSync(new URL("./sync.js", import.meta.url), "utf8");
const fake = { Telegram: { WebApp: { initData: "" } }, fetch: undefined,
  localStorage: { getItem: () => null, setItem: () => {} },
  addEventListener: () => {}, document: {} };
const mod = { exports: {} };
new Function("window", "module", "globalThis", src)(fake, mod, fake);
const { mergeSrs, mergeProgress, mergePlProgress } = mod.exports;

let fails = 0;
const eq = (got, exp, msg) => {
  const g = JSON.stringify(got), e = JSON.stringify(exp);
  if (g !== e) { console.log(`  ✗ ${msg}\n     ожидали ${e}\n     получили ${g}`); fails++; }
  else console.log(`  ✓ ${msg}`);
};

// те же кейсы, что в api/test_api.py
const mSrs = mergeSrs(
  { a: { box: 3, due: 100 }, b: { box: 1, due: 50 } },
  { a: { box: 2, due: 999 }, c: { box: 0, due: 10 } }
);
eq(mSrs.a.box, 3, "SRS: выше box побеждает");
eq(mSrs.b.box, 1, "SRS: server-only сохранён");
eq(mSrs.c.box, 0, "SRS: incoming-only добавлен");
eq(mergeSrs({ x: { box: 2, due: 100 } }, { x: { box: 2, due: 200 } }).x.due, 200, "SRS: равный box → больший due");
eq(mergeSrs({ x: { box: 9, due: 1 } }, { x: { box: 4, due: 5 } }).x.box, 4, "SRS: невалидный box>5 отброшен");

const mProg = mergeProgress(
  { streak: 5, best: 7, days: { "2026-06-20": 3 }, lastDay: "2026-06-20", goal: 15 },
  { streak: 3, best: 4, days: { "2026-06-20": 5, "2026-06-21": 2 }, lastDay: "2026-06-21", goal: 20 }
);
eq(mProg.streak, 5, "progress: streak = max");
eq(mProg.best, 7, "progress: best = max");
eq([mProg.days["2026-06-20"], mProg.days["2026-06-21"]], [5, 2], "progress: days union, max по дню");
eq(mProg.lastDay, "2026-06-21", "progress: lastDay = более поздний");
eq(mProg.goal, 20, "progress: goal из incoming");
eq(mergeProgress(null, null).streak, 0, "progress: None → дефолт");

// флаги-достижения: OR из обоих источников (sync не должен стирать бейджи)
const mFlags = mergeProgress(
  { flags: { examPass: true } },
  { flags: { flawless: true } }
);
eq([!!mFlags.flags.examPass, !!mFlags.flags.flawless], [true, true],
   "progress: flags объединяются (бейджи не теряются)");
eq(!!mergeProgress({ flags: { examPass: true } }, {}).flags.examPass, true,
   "progress: flag из server сохранён при пустом incoming");

// польский прогресс: union solved, max bestCorrect, bestTotal следует за лучшим
const mPL = mergePlProgress(
  { zeglarz: { solved: { "zj-1": 1, "zj-2": 1 }, bestCorrect: 40, bestTotal: 50 },
    sternik: { solved: { "st-1": 1 }, bestCorrect: 20, bestTotal: 50 } },
  { zeglarz: { solved: { "zj-2": 1, "zj-3": 1 }, bestCorrect: 35, bestTotal: 45 } }
);
eq(Object.keys(mPL.zeglarz.solved).sort(), ["zj-1", "zj-2", "zj-3"], "pl: solved union");
eq([mPL.zeglarz.bestCorrect, mPL.zeglarz.bestTotal], [40, 50], "pl: лучший best со своим total");
eq([mPL.sternik.bestCorrect, mPL.sternik.solved["st-1"]], [20, 1], "pl: server-only лицензия сохранена");
eq(mergePlProgress(null, null), {}, "pl: None → {}");
eq(mergePlProgress({ zeglarz: { solved: { a: 1 } } }, {}).zeglarz.bestCorrect, null,
   "pl: solved без экзамена → bestCorrect null");
// incoming с бОльшим best забирает и свой total (не max по total)
eq([mergePlProgress(
     { zeglarz: { bestCorrect: 30, bestTotal: 50 } },
     { zeglarz: { bestCorrect: 44, bestTotal: 45 } }
   ).zeglarz.bestCorrect,
   mergePlProgress(
     { zeglarz: { bestCorrect: 30, bestTotal: 50 } },
     { zeglarz: { bestCorrect: 44, bestTotal: 45 } }
   ).zeglarz.bestTotal], [44, 45], "pl: total идёт за лучшим correct, а не max");

if (fails) { console.log(`\nSYNC CHECK: ${fails} провал(ов)`); process.exit(1); }
console.log("\nSYNC CHECK OK (JS-merge совпадает с серверным)");
