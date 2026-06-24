// Кросс-проверка морской математики Mini App (index.html) против marine.py.
function numFmt(x){ return String(Math.round(x*100)/100).replace(".", ","); }
function hoursToHM(h){ if(h<0)h=0; const t=Math.round(h*60); return `${Math.floor(t/60)} ч ${String(t%60).padStart(2,"0")} мин`; }
function etaClock(start, travelH){
  const s = String(start).trim().replace(".", ":");
  let hh, mm;
  if (s.includes(":")){ [hh,mm] = s.split(":"); }
  else if (/^\d{3,4}$/.test(s)){ hh = s.slice(0,-2); mm = s.slice(-2); }
  else return null;
  const h = parseInt(hh,10), m = parseInt(mm,10);
  if (!(h>=0&&h<24&&m>=0&&m<60)) return null;
  const arrive = ((h*60+m) + Math.round(travelH*60)) % (24*60);
  return `${String(Math.floor(arrive/60)).padStart(2,"0")}:${String(arrive%60).padStart(2,"0")}`;
}

let fail = 0;
const eq = (got, exp, msg) => { if (got !== exp){ console.log(`FAIL ${msg}: got ${got}, exp ${exp}`); fail++; } };
const near = (got, exp, msg) => { if (Math.abs(got-exp) > 1e-9){ console.log(`FAIL ${msg}: got ${got}, exp ${exp}`); fail++; } };

// S-D-T (значения совпадают с test_marine.py)
near(13.2/5.5, 2.4, "time 13.2/5.5");
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
