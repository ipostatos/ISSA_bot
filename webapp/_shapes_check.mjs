// Проверка данных тренажёра «Фигуры и флаги» (webapp/shapes_data.js).
// Фигуры: только известные примитивы, COLREG-инварианты (якорь=1 шар,
// на мели=3 шара, RAM=шар-ромб-шар). Флаги: известные kind'ы, валидные цвета,
// уникальные ключи. Запуск: node webapp/_shapes_check.mjs
import { readFileSync } from "node:fs";

const src = readFileSync(new URL("./shapes_data.js", import.meta.url), "utf8");
const win = {};
new Function("window", src)(win);
const D = win.SHAPES_DATA;

let fail = 0;
const err = m => { console.log("FAIL " + m); fail++; };

if (!D || !Array.isArray(D.dayshapes) || !Array.isArray(D.flags)){
  err("SHAPES_DATA не определён"); process.exit(1);
}

const FIGS = new Set(["ball", "diamond", "cone-up", "cone-down", "cones-apex", "cylinder"]);
const KINDS = new Set(["solid", "vsplit", "hstripes", "vstripes", "checker", "diag",
  "center-rect", "saltire", "nested", "nc"]);
const SHAPE_OUTLINES = new Set(["rect", "swallowtail", "double"]);
const COLOR_RE = /^#[0-9a-f]{6}$/i;

// — дневные фигуры —
const dsKeys = new Set();
for (const s of D.dayshapes){
  if (!s.key || dsKeys.has(s.key)) err(`dayshape: пустой/повторный key ${s.key}`);
  dsKeys.add(s.key);
  if (!s.title || !s.meaning) err(`${s.key}: нет title/meaning`);
  if (!Array.isArray(s.figures) || !s.figures.length) err(`${s.key}: нет figures`);
  for (const f of s.figures || []) if (!FIGS.has(f)) err(`${s.key}: неизвестная фигура ${f}`);
}
// COLREG-инварианты
const fig = k => (D.dayshapes.find(s => s.key === k) || {}).figures || [];
if (fig("anchor").join() !== "ball") err("якорь — один шар (правило 30)");
if (fig("aground").join() !== "ball,ball,ball") err("на мели — три шара (правило 30(d))");
if (fig("ram").join() !== "ball,diamond,ball") err("RAM — шар-ромб-шар (правило 27(b))");
if (fig("nuc").join() !== "ball,ball") err("NUC — два шара (правило 27(a))");
if (fig("motorsailing").join() !== "cone-down") err("парус+мотор — конус вершиной ВНИЗ (25(e))");
if (fig("fishing").join() !== "cones-apex") err("лов рыбы — конусы вершинами вместе (26)");
if (fig("cbd").join() !== "cylinder") err("стеснённое осадкой — цилиндр (28)");

// — флаги —
const flKeys = new Set();
for (const f of D.flags){
  if (!f.key || flKeys.has(f.key)) err(`flag: пустой/повторный key ${f.key}`);
  flKeys.add(f.key);
  if (!f.meaning) err(`флаг ${f.key}: нет meaning`);
  if (!f.draw || !SHAPE_OUTLINES.has(f.draw.shape)) err(`флаг ${f.key}: неизвестный контур ${f.draw && f.draw.shape}`);
  if (!KINDS.has(f.draw.kind)) err(`флаг ${f.key}: неизвестный kind ${f.draw.kind}`);
  for (const c of f.draw.colors || []) if (!COLOR_RE.test(c)) err(`флаг ${f.key}: битый цвет ${c}`);
}
// «N над C» ссылается на N и C — они обязаны существовать
if (flKeys.has("NC") && (!flKeys.has("N") || !flKeys.has("C"))) err("NC требует флагов N и C");
// смысловые инварианты экзаменационного минимума
const mean = k => ((D.flags.find(f => f.key === k) || {}).meaning || "").toLowerCase();
if (!mean("A").includes("водолаз")) err("A — водолаз");
if (!mean("O").includes("за бортом")) err("O — человек за бортом");
if (!mean("B").includes("опасн")) err("B — опасный груз");

if (fail) process.exit(1);
console.log(`SHAPES DATA OK (${D.dayshapes.length} фигур, ${D.flags.length} флагов)`);
