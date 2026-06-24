// Кросс-проверка JS-математики Mini App против эталона.
// Логика идентична <script> в index.html.
const POINTS = ["T","M","C"];
const NAME = {T:"True", M:"Magnetic", C:"Compass"};
const norm360 = x => ((x % 360) + 360) % 360;

function step(a,b,cur,val,dir,down){
  let s; if(down) s=(dir==="E")?-1:+1; else s=(dir==="E")?+1:-1;
  return { result: norm360(cur + s*val) };
}
function solve(src,dst,course,vr,vrDir,dv,dvDir){
  const i=POINTS.indexOf(src), j=POINTS.indexOf(dst), down=j>i;
  let cur=norm360(course); const order=[];
  if(down) for(let k=i;k<j;k++) order.push([POINTS[k],POINTS[k+1]]);
  else     for(let k=i;k>j;k--) order.push([POINTS[k],POINTS[k-1]]);
  for(const [a,b] of order){
    const isVar=(a+b).includes("T");
    const val=isVar?vr:dv, dir=isVar?vrDir:dvDir;
    cur=step(a,b,cur,val,dir,down).result;
  }
  return Math.round(cur);
}

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
