// Кросс-проверка JS-математики Mini App против эталона calc.py / nav_tasks.py.
// Исполняются НАСТОЯЩИЕ solve/step/norm360 из index.html (через _page_code.mjs),
// а не копия: до волны E тест держал свою копию и не видел правок страницы.
import { pageCode } from "./_page_code.mjs";
const page = pageCode("index.html", ["POINTS", "NAME", "norm360", "step", "solve"]);
const solve = (...args) => page.solve(...args).answer;

// Эталонные ответы должны совпасть с calc.py / nav_tasks.py
const cases = [
  ["T","M",100,6,"E",0,"E",94],
  ["T","M",80,5,"W",0,"E",85],
  ["M","C",120,0,"E",4,"E",116],
  ["M","C",120,0,"E",4,"W",124],
  ["M","C",200,0,"E",3,"W",203],
  ["T","C",45,3,"W",2,"E",46],
  ["C","T",46,3,"W",2,"E",45],
  ["T","C",357,6,"W",3,"W",6],
  ["T","C",3,5,"E",4,"E",354],
  ["M","C",359,0,"E",4,"W",3],
];
let bad=0;
for(const [s,d,c,v,vd,dv,dd,exp] of cases){
  const got=solve(s,d,c,v,vd,dv,dd);
  const ok=got===exp;
  if(!ok) bad++;
  console.log(`${ok?"OK ":"FAIL"} ${s}->${d} ${c} = ${got} (want ${exp})`);
}
// round-trip по всем углам
let rt=0;
for(let T=0;T<360;T+=3){
  for(const [v,vd,dv,dd] of [[6,"E",3,"W"],[5,"W",4,"E"],[10,"E",7,"E"]]){
    const c=solve("T","C",T,v,vd,dv,dd);
    const back=solve("C","T",c,v,vd,dv,dd);
    let diff=Math.abs(back-T); diff=Math.min(diff,360-diff);
    if(diff>1) rt++;
  }
}
console.log("round-trip mismatches:", rt);
console.log(bad===0 && rt===0 ? "JS MATH OK" : "JS MATH PROBLEM");
process.exit(bad===0 && rt===0 ? 0 : 1);
