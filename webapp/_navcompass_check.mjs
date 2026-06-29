// Проверка формулы интерактивного компаса-песочницы (navtasks.html → tvmdcCompass).
// Логика ДОЛЖНА совпадать с боевыми задачами (nav_tasks.py): вниз T→C West +, East −.
// Слайдер: значение>0 = West (+), значение<0 = East (−) → просто прибавляем к курсу.

// ── копия логики из navtasks.html (window.tvmdcNorm / window.tvmdcCompass) ──
const tvmdcNorm = v => ((Math.round(v) % 360) + 360) % 360;
function tvmdcCompass(trueCourse, varSigned, devSigned){
  const magnetic = tvmdcNorm(trueCourse + varSigned);
  const compass  = tvmdcNorm(magnetic + devSigned);
  return { magnetic, compass };
}
// перевод «градусы + сторона» в знак слайдера (West +, East −)
const signed = (deg, dir) => dir === "W" ? deg : -deg;

let fail = 0;
function check(name, cond){
  console.log((cond ? "  ✓ " : "  ✗ ") + name);
  if (!cond) fail++;
}

// 1) нормализация 0..359
check("norm(360) = 0", tvmdcNorm(360) === 0);
check("norm(-1) = 359", tvmdcNorm(-1) === 359);
check("norm(450) = 90", tvmdcNorm(450) === 90);
check("norm(0) = 0", tvmdcNorm(0) === 0);
check("norm(719) = 359", tvmdcNorm(719) === 359);

// 2) формула T→M→C против эталона (совпадает с nav_tasks.py)
//    [True, varDeg, varDir, devDeg, devDir, ожид. Magnetic, ожид. Compass]
const cases = [
  [50, 3, "W", 5, "W", 53, 58],   // West прибавляет: 50+3=53, 53+5=58
  [50, 3, "E", 5, "E", 47, 42],   // East вычитает: 50-3=47, 47-5=42
  [100, 6, "E", 0, "E", 94, 94],  // как nt-01: True 100, Var 6E → Mag 94
  [90, 10, "W", 0, "E", 100, 100],
  [0, 5, "E", 5, "W", 355, 0],    // переход через 0: 0-5=355, 355+5=360→0
  [358, 0, "E", 5, "W", 358, 3],  // переход через 360: 358+5=363→3
  [10, 0, "E", 15, "E", 10, 355], // 10-15=-5→355
];
for (const [t, vd, vdir, dd, ddir, expM, expC] of cases){
  const r = tvmdcCompass(t, signed(vd, vdir), signed(dd, ddir));
  check(`True ${t}, Var ${vd}${vdir}, Dev ${dd}${ddir} → Mag ${expM}, Comp ${expC}`,
        r.magnetic === expM && r.compass === expC);
}

// 3) результат всегда в диапазоне 0..359 на широком прогоне
let rangeOk = true;
for (let t = 0; t < 360; t += 13)
  for (let v = -20; v <= 20; v += 7)
    for (let d = -20; d <= 20; d += 7){
      const r = tvmdcCompass(t, v, d);
      if (r.magnetic < 0 || r.magnetic > 359 || r.compass < 0 || r.compass > 359){ rangeOk = false; }
    }
check("Mag и Compass всегда в [0,359] на широком прогоне", rangeOk);

if (fail){ console.log(`\nNAV COMPASS CHECK: ${fail} провал(ов)`); process.exit(1); }
console.log("NAV COMPASS CHECK OK");
