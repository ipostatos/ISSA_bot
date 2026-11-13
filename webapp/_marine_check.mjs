// Кросс-проверка морской математики Mini App (index.html) против marine.py.
// Исполняются НАСТОЯЩИЕ numFmt/hoursToHM/etaClock из index.html, а не копия.
// hoursToHM форматирует через I18N — подкладываем движок с боевым словарём (ru).
import { createRequire } from "module";
import { pageCode } from "./_page_code.mjs";
const DICT = createRequire(import.meta.url)("./i18n.dict.js").DICT;
const I18N = { t: (k, v = {}) => Object.entries(v).reduce((s, [n, x]) => s.split(`{${n}}`).join(x), DICT[k].ru) };
const { numFmt, hoursToHM, etaClock } = pageCode("index.html", ["numFmt", "hoursToHM", "etaClock"], { I18N });

let fail = 0;
const eq = (got, exp, msg) => { if (got !== exp){ console.log(`FAIL ${msg}: got ${got}, exp ${exp}`); fail++; } };
const near = (got, exp, msg) => { if (Math.abs(got-exp) > 1e-9){ console.log(`FAIL ${msg}: got ${got}, exp ${exp}`); fail++; } };

// S-D-T (значения совпадают с test_marine.py)
near(13.2/5.5, 2.4, "time 13.2/5.5");
eq(numFmt(2.4), "2,4", "numFmt запятая");
near(6*2.5, 15, "dist 6*2.5");
near(15/3, 5, "speed 15/3");

// hours_to_hm
eq(hoursToHM(0.5), "0 ч 30 мин", "hm 0.5");
eq(hoursToHM(2.25), "2 ч 15 мин", "hm 2.25");

// ETA clock (как в marine.py)
eq(etaClock("09:00", 2.5), "11:30", "eta 09:00+2.5");
eq(etaClock("22:30", 2.0), "00:30", "eta wrap midnight");
eq(etaClock("0700", 1.5), "08:30", "eta 0700 format");
eq(etaClock("25:00", 1), null, "eta invalid");

// plan_eta(18,5,20,"09:00") -> 4.32 ч, ETA 13:19
const base=18/5, withR=base*1.2;
near(withR, 4.32, "eta reserve travel");
eq(etaClock("09:00", withR), "13:19", "eta reserve clock");

console.log(fail === 0 ? "MARINE JS OK" : `MARINE JS PROBLEM (${fail})`);
process.exit(fail === 0 ? 0 : 1);
