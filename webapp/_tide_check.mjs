// Кросс-проверка правила двенадцатых (index.html) против tides.py.
const TWELFTHS = [1,2,3,3,2,1];
function heightAfterLw(hw, lw, hours){
  const rng = hw - lw;
  let h = Math.max(0, Math.min(6, hours));
  const full = Math.floor(h), frac = h - full;
  let water = lw;
  for (let i=0; i<full; i++) water += rng*TWELFTHS[i]/12;
  if (full < 6) water += rng*TWELFTHS[full]/12*frac;
  return water;
}
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
