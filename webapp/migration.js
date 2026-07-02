// ===========================================================================
// MIGRATION — версионирование схемы localStorage.
//
// Проблема: ключи прогресса (issa_progress_v1, issa_srs_v1, ...) не несут
// версии ВНУТРИ данных, поэтому при смене формата старые сохранённые объекты
// на устройстве пользователя молча ломались бы (undefined/NaN в новых полях).
//
// Решение: отдельный САЙДКАР-реестр версий issa_schema_v = { store: version }.
// Данные НЕ трогаем структурно (никакого __v внутри — часть хранилищ это
// словари по qid/лицензии/бейджу, где лишний ключ выглядел бы как данные).
// При загрузке страницы Migration.run() для каждого стора смотрит текущую
// версию и прогоняет цепочку миграторов store[from..target-1], затем ставит
// новую версию в реестр.
//
// СОВМЕСТИМОСТЬ: если стор уже есть в localStorage, но реестра нет — это
// «нулевая» версия (v0, прод-данные _v1). Мигрируем с 0. Пустой стор
// (пользователь ещё ничего не сохранял) сразу помечаем целевой версией —
// мигрировать нечего.
//
// РАСШИРЕНИЕ: когда реально меняется формат стора, поднять его число в
// TARGET и дописать функцию в MIGRATORS[store] с индексом (версия-источник).
// Мигратор чистый: (data) -> data. Сейчас цепочки пустые (инфраструктура
// готова, миграций ещё нет) — run() лишь проставляет версии.
//
// Подключать ПЕРВЫМ, до srs.js/progress.js/pl_progress.js/badges.js:
//   <script src="migration.js"></script>
//   <script src="srs.js"></script> ...
// ===========================================================================
(function (global) {
  "use strict";

  var REG_KEY = "issa_schema_v";

  // Целевая версия каждого стора. Ключ реестра = имя стора (короткое), не
  // localStorage-ключ. Поднимать при смене формата соответствующего стора.
  var TARGET = {
    srs: 1,
    progress: 1,
    pl_progress: 1,
    badges_seen: 1,
  };

  // localStorage-ключ каждого стора.
  var STORE_KEY = {
    srs: "issa_srs_v1",
    progress: "issa_progress_v1",
    pl_progress: "issa_pl_progress_v1",
    badges_seen: "issa_badges_seen_v1",
  };

  // MIGRATORS[store][i] превращает данные версии i в версию i+1. Чистая
  // функция (data) -> data. Пока миграций нет — все цепочки пустые.
  // Пример на будущее (НЕ активен):
  //   srs: [ function v0_to_v1(map){ /* ... */ return map; } ]
  var MIGRATORS = {
    srs: [],
    progress: [],
    pl_progress: [],
    badges_seen: [],
  };

  function lsGetRaw(k) {
    try { return global.localStorage.getItem(k); } catch (e) { return null; }
  }
  function lsSet(k, v) {
    try { global.localStorage.setItem(k, JSON.stringify(v)); } catch (e) {}
  }

  function loadRegistry() {
    try { return JSON.parse(lsGetRaw(REG_KEY)) || {}; }
    catch (e) { return {}; }
  }
  function saveRegistry(reg) { lsSet(REG_KEY, reg); }

  // Прогнать один стор до целевой версии. Возвращает true, если что-то
  // изменили (данные или запись версии), иначе false.
  function migrateStore(reg, store) {
    var target = TARGET[store] || 0;
    var key = STORE_KEY[store];
    var raw = lsGetRaw(key);

    // Стора нет в localStorage — мигрировать нечего, версию не пишем: новые
    // сохранения и так пойдут в целевом формате. run() отметит версию, когда
    // стор появится.
    if (raw === null) return false;

    // Версия-источник: из реестра; если стор есть, а записи нет — это v0.
    var from = (typeof reg[store] === "number") ? reg[store] : 0;
    if (from >= target) {
      // Уже свежий: убедимся, что версия зафиксирована.
      if (reg[store] !== target) { reg[store] = target; return true; }
      return false;
    }

    var data;
    try { data = JSON.parse(raw); } catch (e) { data = null; }
    // Битые данные не мигрируем — пусть модульный load() отдаст дефолт.
    if (data === null) { reg[store] = target; return true; }

    var chain = MIGRATORS[store] || [];
    for (var v = from; v < target; v++) {
      var fn = chain[v];
      if (typeof fn === "function") {
        try { data = fn(data); } catch (e) { /* мигратор упал — оставляем как есть */ }
      }
    }
    lsSet(key, data);
    reg[store] = target;
    return true;
  }

  var Migration = {
    REG_KEY: REG_KEY,
    // Прогнать все сторы. Идемпотентно: повторный вызов ничего не меняет.
    run: function () {
      var reg = loadRegistry();
      var changed = false;
      Object.keys(TARGET).forEach(function (store) {
        if (migrateStore(reg, store)) changed = true;
      });
      if (changed) saveRegistry(reg);
      return reg;
    },
    // для тестов
    _target: TARGET,
    _storeKey: STORE_KEY,
    _migrators: MIGRATORS,
  };

  global.Migration = Migration;
  // Прогоняем сразу при загрузке скрипта — до того, как модули прочитают стор.
  Migration.run();

  if (typeof module !== "undefined" && module.exports) {
    module.exports = Migration;
  }
})(typeof window !== "undefined" ? window : globalThis);
