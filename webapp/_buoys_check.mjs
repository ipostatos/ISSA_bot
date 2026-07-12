// Проверка данных тренажёра «Буи IALA» (webapp/buoys_data.js).
// Главное — ТОЧНОСТЬ РИТМОВ: сумма pattern (мс) обязана совпадать с периодом
// из официальной записи характеристики ("VQ(3) 5s" → 5000 мс), число
// проблесков — с группой в скобках, LFl ≥ 2 c, у одиночного Fl темнота ≥ 3×
// света, частота VQ = 100–120/мин (IALA R0110 / E-110).
// Запуск: node webapp/_buoys_check.mjs   → "BUOYS DATA OK (N знаков)"
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const dir = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(dir, "buoys_data.js"), "utf8");
const win = {};
new Function("window", src)(win);
const DATA = win.BUOYS_DATA;

let fail = 0;
const err = m => { console.log("FAIL " + m); fail++; };

if (!DATA || !Array.isArray(DATA.buoys)) { err("BUOYS_DATA не определён"); process.exit(1); }

const SHAPES = new Set(["can","cone","pillar","sphere"]);
const TOPMARKS = new Set(["can-red","cone-green","cones-up","cones-down","cones-base",
  "cones-point","balls-two","ball-red","cross-yellow","cross-plus-yellow"]);
const LIGHT_COLORS = new Set(["red","green","yellow","white","blue"]);
const BODY_COLORS = new Set(["red","green","yellow","black","white","blue",
  "black-yellow","yellow-black","black-yellow-black","yellow-black-yellow",
  "black-red-black","red-green-red","red-white","blue-yellow"]);
const VERTICAL = new Set(["red-white","blue-yellow"]);   // полосы только вертикальные
const REQUIRED = ["port","starboard","pref_starboard","north","east","south","west",
  "isolated","safewater","special"];

const catKeys = new Set((DATA.categories||[]).map(c=>c.key));
const ids = new Set();

for (const b of DATA.buoys){
  const id = b.id || "<без id>";
  if (ids.has(id)) err(id+": дубль id");
  ids.add(id);
  if (!catKeys.has(b.cat)) err(id+": неизвестная категория "+b.cat);
  if (!SHAPES.has(b.shape)) err(id+": неизвестная форма "+b.shape);
  if (!BODY_COLORS.has(b.color)) err(id+": неизвестная окраска "+b.color);
  if (b.stripes && (b.stripes!=="v" || !VERTICAL.has(b.color)))
    err(id+": stripes='v' допустим только для "+[...VERTICAL].join("/"));
  if (VERTICAL.has(b.color) && b.stripes!=="v")
    err(id+": окраска "+b.color+" должна быть с stripes:'v'");
  if (!TOPMARKS.has(b.topmark)) err(id+": неизвестная топовая фигура "+b.topmark);
  if (!b.title || !b.answer || !b.hint) err(id+": пустой title/answer/hint");

  // тест
  const q = b.quiz;
  if (!q || !Array.isArray(q.options) || q.options.length < 2) err(id+": quiz.options < 2");
  else if (!(q.correct >= 0 && q.correct < q.options.length)) err(id+": quiz.correct вне диапазона");

  // ── характер огня ──
  const l = b.light;
  if (!l){ err(id+": нет light"); continue; }
  if (!LIGHT_COLORS.has(l.color)) err(id+": неизвестный цвет огня "+l.color);
  if (!l.char) err(id+": нет официальной записи light.char");
  if (!l.rhythm) err(id+": нет расшифровки light.rhythm");
  const p = l.pattern;
  if (!Array.isArray(p) || p.length < 2 || p.length % 2){ err(id+": pattern должен быть чётным списком [вкл,выкл,...]"); continue; }
  if (p.some(x=>!Number.isFinite(x) || x <= 0)) { err(id+": pattern содержит неположительные значения"); continue; }
  const sum = p.reduce((a,x)=>a+x,0);
  const ons  = p.filter((_,i)=>i%2===0);
  const offs = p.filter((_,i)=>i%2===1);
  if (Math.min(...ons)  < 120) err(id+": проблеск короче 120 мс — не будет виден");
  if (Math.min(...offs) < 100) err(id+": пауза короче 100 мс");

  const ch = String(l.char);
  // период из записи "... Ns"
  const mPer = ch.match(/(\d+(?:[.,]\d+)?)\s*s\b/i);
  if (mPer){
    const per = Math.round(parseFloat(mPer[1].replace(",","."))*1000);
    if (sum !== per) err(id+": сумма pattern "+sum+" мс ≠ период из char «"+ch+"» ("+per+" мс)");
  } else if (/^VQ$/i.test(ch.trim())){
    // непрерывный VQ: 100–120 проблесков/мин → период 500–600 мс
    if (sum < 500 || sum > 600) err(id+": VQ непрерывный должен иметь период 500–600 мс, а не "+sum);
  } else {
    err(id+": в char «"+ch+"» не читается период (нужно \"... Ns\" или \"VQ\")");
  }
  // число проблесков в группе: "(n)" или "(n+m)", "+LFl" добавляет ещё один
  let expected = null;
  const mGrp = ch.match(/\((\d+)(?:\+(\d+))?\)/);
  if (mGrp) expected = (+mGrp[1]) + (mGrp[2] ? +mGrp[2] : 0);
  else if (/Al/i.test(ch)) expected = (l.colors||[]).length || null;
  else expected = 1;                       // Fl / LFl / VQ одиночные
  if (expected !== null && /\+\s*LFl/i.test(ch)) expected += 1;
  if (expected !== null && ons.length !== expected)
    err(id+": в char «"+ch+"» "+expected+" проблесков, а в pattern "+ons.length);
  // LFl — длинный проблеск ≥ 2 c
  if (/LFl/i.test(ch) && Math.max(...ons) < 2000)
    err(id+": char содержит LFl, но нет проблеска ≥ 2000 мс");
  // одиночный Fl: темнота ≥ 3× света (определение проблескового огня)
  if (/^Fl\b/i.test(ch) && !mGrp && offs[0] < 3*ons[0])
    err(id+": одиночный Fl — темнота ("+offs[0]+") должна быть ≥ 3× света ("+ons[0]+")");
  // группы VQ: частота внутри группы 100–120/мин (вкл+выкл 500–600 мс)
  if (/^VQ\(/i.test(ch) && p.length >= 4){
    const cycle = p[0]+p[1];
    if (cycle < 500 || cycle > 600) err(id+": частота VQ внутри группы — период "+cycle+" мс вместо 500–600");
  }
  // перемежающиеся огни (Al): нужен список цветов
  if (/Al/i.test(ch)){
    if (!Array.isArray(l.colors) || l.colors.length < 2) err(id+": Al-огонь требует colors из ≥2 цветов");
    else for (const c of l.colors) if (!LIGHT_COLORS.has(c)) err(id+": неизвестный цвет в colors: "+c);
  } else if (l.colors) err(id+": colors допустимы только для перемежающихся (Al) огней");
}

for (const rid of REQUIRED) if (!ids.has(rid)) err("нет обязательного знака "+rid);

console.log(fail === 0
  ? "BUOYS DATA OK ("+DATA.buoys.length+" знаков)"
  : "BUOYS DATA PROBLEM ("+fail+")");
process.exit(fail === 0 ? 0 : 1);
