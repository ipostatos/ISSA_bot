// Проверка migration.js — версионирование localStorage-схемы.
// Запуск: node webapp/_migration_check.mjs
import { readFileSync } from "fs";

const src = readFileSync(new URL("./migration.js", import.meta.url), "utf8");

// Фейковый localStorage + среда. Каждый прогон получает свежий store.
function makeEnv(initial) {
  const store = Object.assign({}, initial || {});
  const ls = {
    getItem: (k) => (k in store ? store[k] : null),
    setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; },
  };
  return { window: { localStorage: ls }, store, ls };
}

// Загружаем migration.js в изолированной среде. Возвращает {Migration, store}.
function loadMigration(initial) {
  const env = makeEnv(initial);
  const fake = { localStorage: env.ls };
  const mod = { exports: {} };
  // migration.js вызывает Migration.run() сразу при загрузке.
  new Function("window", "module", "globalThis", src)(fake, mod, fake);
  return { Migration: fake.Migration, store: env.store };
}

let fails = 0;
const eq = (got, exp, msg) => {
  const g = JSON.stringify(got), e = JSON.stringify(exp);
  if (g !== e) { console.log(`  ✗ ${msg}\n     ожидали ${e}\n     получили ${g}`); fails++; }
  else console.log(`  ✓ ${msg}`);
};

// 1) v0-данные (прод _v1, реестра нет) → версия проставлена, данные целы
{
  const srs0 = JSON.stringify({ "q-1": { box: 3, due: 100 } });
  const prog0 = JSON.stringify({ streak: 5, flags: { examPass: true } });
  const { store } = loadMigration({ issa_srs_v1: srs0, issa_progress_v1: prog0 });
  const reg = JSON.parse(store.issa_schema_v);
  eq([reg.srs, reg.progress], [1, 1], "v0: реестр проставлен в target=1");
  eq(store.issa_srs_v1, srs0, "v0: srs-данные не изменены (no-op миграторы)");
  eq(store.issa_progress_v1, prog0, "v0: progress-данные не изменены");
}

// 2) идемпотентность: второй run() ничего не меняет
{
  const { Migration, store } = loadMigration({ issa_srs_v1: JSON.stringify({ a: { box: 1, due: 1 } }) });
  const regBefore = store.issa_schema_v;
  Migration.run();
  eq(store.issa_schema_v, regBefore, "idempotent: повторный run() не меняет реестр");
}

// 3) пустой стор (нет ключа) → в реестре записи нет, без краша
{
  const { store } = loadMigration({});   // localStorage пуст
  const reg = JSON.parse(store.issa_schema_v || "{}");
  eq(reg.srs === undefined && reg.progress === undefined, true,
     "empty: отсутствующие сторы не получают версию");
}

// 4) битые данные не роняют миграцию, версия проставляется
{
  const { store } = loadMigration({ issa_srs_v1: "{битый json" });
  const reg = JSON.parse(store.issa_schema_v);
  eq(reg.srs, 1, "corrupt: версия проставлена несмотря на битые данные");
}

// 5) РАБОЧАЯ цепочка миграции: подсовываем мигратор v0→v1 в progress и
//    проверяем, что он реально выполняется на v0-данных. Делаем на «свежем»
//    экземпляре: грузим модуль, ДОБАВЛЯЕМ мигратор, сбрасываем реестр, run().
{
  const srs0 = JSON.stringify({ "q-1": { box: 2, due: 50 } });
  const prog0 = JSON.stringify({ streak: 3 });
  const { Migration, store } = loadMigration({ issa_srs_v1: srs0, issa_progress_v1: prog0 });
  // симулируем будущую миграцию progress: v1 → v2, добавляющую поле theme
  Migration._target.progress = 2;
  Migration._migrators.progress[1] = function v1_to_v2(data) { data.theme = "sea"; return data; };
  // сбрасываем реестр для progress в 1 (как будто данные уже были v1)
  const reg = { srs: 1, progress: 1 };
  store.issa_schema_v = JSON.stringify(reg);
  Migration.run();
  const prog = JSON.parse(store.issa_progress_v1);
  const reg2 = JSON.parse(store.issa_schema_v);
  eq(prog.theme, "sea", "chain: мигратор v1→v2 реально выполнился");
  eq(prog.streak, 3, "chain: прежние поля сохранены при миграции");
  eq(reg2.progress, 2, "chain: версия поднялась до 2");
  eq(store.issa_srs_v1, srs0, "chain: несвязанный стор (srs) не тронут");
}

if (fails) { console.log(`\nMIGRATION CHECK: ${fails} провал(ов)`); process.exit(1); }
console.log("\nMIGRATION CHECK OK");
