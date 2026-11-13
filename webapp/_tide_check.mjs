// Кросс-проверка правила двенадцатых (index.html) против tides.py.
// Исполняется НАСТОЯЩАЯ heightAfterLw из index.html, а не копия.
import { pageCode } from "./_page_code.mjs";
const { heightAfterLw } = pageCode("index.html", ["TWELFTHS", "heightAfterLw"]);
let fail = 0;
const near = (g,e,m) => { if (Math.abs(g-e) > 1e-9){ console.log(`FAIL ${m}: ${g} != ${e}`); fail++; } };

// пример с доски 8/2
const exp = {1:2.5,2:3.5,3:5.0,4:6.5,5:7.5,6:8.0};
for (const [h,v] of Object.entries(exp)) near(heightAfterLw(8,2,+h), v, `8/2 h=${h}`);
near(heightAfterLw(8,2,3.5), 5.75, "fraction 3.5");
near(heightAfterLw(8,2,0), 2, "at LW");
near(heightAfterLw(8,2,10), 8, "clamp 6");
near(heightAfterLw(2,8,1), 7.5, "ebb");

console.log(fail===0 ? "TIDE JS OK" : `TIDE JS PROBLEM (${fail})`);
process.exit(fail===0 ? 0 : 1);
