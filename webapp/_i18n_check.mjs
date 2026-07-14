// Проверка целостности словаря интерфейса: каждый ключ имеет все 4 языка.
// Ловит регрессию «добавил ключ, забыл перевод». Запуск: node webapp/_i18n_check.mjs
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const D = require("./i18n.dict.js");

const LANGS = ["ru", "pl", "ua", "en"];
const errors = [];
for (const [key, row] of Object.entries(D.DICT)) {
  if (!row || typeof row !== "object") { errors.push(`${key}: не объект`); continue; }
  for (const l of LANGS) {
    if (typeof row[l] !== "string" || !row[l].trim()) errors.push(`${key}: нет/пусто "${l}"`);
  }
}
if (D.LANGS.map((x) => x.code).join(",") !== LANGS.join(",")) {
  errors.push("LANGS: набор/порядок языков изменился");
}
if (errors.length) {
  console.error("i18n check FAILED:\n  " + errors.join("\n  "));
  process.exit(1);
}
console.log(`i18n OK: ${Object.keys(D.DICT).length} ключей × ${LANGS.length} языка.`);
