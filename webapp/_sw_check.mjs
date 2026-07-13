// Проверка PWA/offline (Этап 4): service worker, манифест, регистрация в nav.js
// и ПОЛНОТА деплой-списка (update_webapp.sh — явный whitelist: забытый файл =
// 404 на проде, как случилось с audio/shapes до этого чека).
// Запуск: node webapp/_sw_check.mjs
import { readFileSync, readdirSync, existsSync } from "fs";

const here = (p) => new URL("./" + p, import.meta.url);

let fails = 0;
const ok = (cond, msg) => {
  if (!cond) { console.log(`  ✗ ${msg}`); fails++; }
  else console.log(`  ✓ ${msg}`);
};

// --- 1. sw.js: синтаксис и обязательные свойства ---------------------------
const sw = readFileSync(here("sw.js"), "utf8");
try {
  new Function(sw); // классический скрипт: должен парситься
  ok(true, "sw.js парсится");
} catch (e) {
  ok(false, `sw.js не парсится: ${e.message}`);
}
for (const evt of ["install", "activate", "fetch"]) {
  ok(sw.includes(`addEventListener("${evt}"`), `sw.js обрабатывает ${evt}`);
}
ok(/\/api\//.test(sw), "sw.js исключает /api/ из кэша (живой прогресс)");
ok(sw.includes('".pdf"'), "sw.js исключает PDF-книги из кэша (объём)");
ok(sw.includes('headers.has("range")'), "sw.js пропускает range-запросы (pdf.js)");
ok(/var CACHE = "issa-static-v\d+"/.test(sw), "имя кэша версионировано (issa-static-vN)");

// --- 2. nav.js: регистрация SW + манифест на каждой странице ----------------
const nav = readFileSync(here("nav.js"), "utf8");
ok(nav.includes('serviceWorker.register("sw.js")'), "nav.js регистрирует sw.js");
ok(nav.includes("manifest.webmanifest"), "nav.js подключает манифест");

// --- 3. манифест и иконка ----------------------------------------------------
try {
  const mf = JSON.parse(readFileSync(here("manifest.webmanifest"), "utf8"));
  ok(!!(mf.name && mf.start_url && mf.icons && mf.icons.length), "манифест: name/start_url/icons");
  for (const i of mf.icons) ok(existsSync(here(i.src)), `иконка манифеста существует: ${i.src}`);
} catch (e) {
  ok(false, `manifest.webmanifest не читается/не JSON: ${e.message}`);
}

// --- 4. полнота деплой-списка ------------------------------------------------
// Каждый публикуемый файл верхнего уровня webapp/ обязан быть упомянут в
// update_webapp.sh. Исключения: чеки (_*.mjs), генераторы (build_*.py),
// README и robots (robots.txt копируется, но проверим и его заодно).
const deploySh = readFileSync(new URL("../deploy/update_webapp.sh", import.meta.url), "utf8");
const deployable = readdirSync(new URL(".", import.meta.url)).filter((f) =>
  /\.(html|js|css|svg|webmanifest|txt)$/.test(f) &&
  !f.startsWith("_") && !f.startsWith("build_") && f !== "README.md"
);
for (const f of deployable) {
  ok(deploySh.includes(f), `деплой публикует ${f}`);
}

// --- 5. функциональная проверка стратегий (эмуляция SW-окружения) -----------
const ORIGIN = "https://app.test";
const listeners = {};
const fakeSelf = {
  addEventListener: (n, fn) => { listeners[n] = fn; },
  skipWaiting: () => {},
  clients: { claim: () => Promise.resolve() },
  location: { origin: ORIGIN },
};
const keyOf = (x) => {
  const u = typeof x === "string" ? new URL(x, ORIGIN + "/") : new URL(x.url);
  return u.origin + u.pathname;
};
const stores = new Map();
const cacheFor = (name) => {
  if (!stores.has(name)) stores.set(name, new Map());
  const m = stores.get(name);
  return {
    put: (req, res) => { m.set(keyOf(req), res); return Promise.resolve(); },
    match: (req) => Promise.resolve(m.get(keyOf(req))),
  };
};
const fakeCaches = {
  open: (n) => Promise.resolve(cacheFor(n)),
  keys: () => Promise.resolve([...stores.keys()]),
  delete: (n) => Promise.resolve(stores.delete(n)),
  match: (req) => {
    for (const m of stores.values()) if (m.has(keyOf(req))) return Promise.resolve(m.get(keyOf(req)));
    return Promise.resolve(undefined);
  },
};
let net = { online: true, tag: "net" }; // переключатель «сети» для тестов
const fakeFetch = () => net.online
  ? Promise.resolve({ status: 200, type: "basic", tag: net.tag, clone() { return this; } })
  : Promise.reject(new TypeError("offline"));

new Function("self", "caches", "fetch", sw)(fakeSelf, fakeCaches, fakeFetch);

const req = (url, { mode = "no-cors", range = false } = {}) => ({
  url, method: "GET", mode,
  headers: { has: (h) => (h === "range" ? range : false) },
});
async function dispatch(r) {
  let handled;
  listeners.fetch({ request: r, respondWith: (p) => { handled = p; } });
  return handled ? await handled : undefined;
}

listeners.install();
let activated;
listeners.activate({ waitUntil: (p) => { activated = p; } });
await activated;

// не перехватываем: API, PDF, range, чужие домены (кроме telegram-web-app)
ok(await dispatch(req(ORIGIN + "/api/state")) === undefined, "поведение: /api/ идёт мимо SW");
ok(await dispatch(req(ORIGIN + "/book.pdf")) === undefined, "поведение: PDF идёт мимо SW");
ok(await dispatch(req(ORIGIN + "/quiz.html", { range: true })) === undefined, "поведение: range-запрос идёт мимо SW");
ok(await dispatch(req("https://basemaps.cartocdn.com/tile.png")) === undefined, "поведение: внешние тайлы мимо SW");
ok((await dispatch(req("https://telegram.org/js/telegram-web-app.js"))) !== undefined, "поведение: telegram-web-app.js кэшируется");

// network-first: онлайн отдаёт сеть и наполняет кэш; офлайн отдаёт кэш
net = { online: true, tag: "fresh" };
const online = await dispatch(req(ORIGIN + "/quiz.html", { mode: "navigate" }));
ok(online && online.tag === "fresh", "поведение: онлайн страница берётся из сети");
await dispatch(req(ORIGIN + "/index.html", { mode: "navigate" })); // прогрели главную
net = { online: false };
const offline = await dispatch(req(ORIGIN + "/quiz.html", { mode: "navigate" }));
ok(offline && offline.tag === "fresh", "поведение: офлайн страница отдаётся из кэша");
const fallback = await dispatch(req(ORIGIN + "/audio.html", { mode: "navigate" }));
ok(fallback && fallback.tag === "fresh", "поведение: офлайн незнакомая навигация падает на index.html");

// stale-while-revalidate: картинка отдаётся из кэша мгновенно
net = { online: true, tag: "img-v1" };
await dispatch(req(ORIGIN + "/images/knots/k1.jpg"));
net = { online: true, tag: "img-v2" };
const img = await dispatch(req(ORIGIN + "/images/knots/k1.jpg"));
ok(img && img.tag === "img-v1", "поведение: картинка отдаётся из кэша (SWR), обновление в фоне");

if (fails) { console.log(`\nSW/PWA CHECK: ${fails} провал(ов)`); process.exit(1); }
console.log("\nSW/PWA CHECK OK");
