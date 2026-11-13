// Помощник для JS-сторожей: достаёт НАСТОЯЩИЕ объявления из inline-скриптов
// страницы и исполняет их, вместо того чтобы тест держал свою копию логики.
//
// Зачем: до волны E (13.11.2026) _solver/_marine/_tide/_navcompass проверяли
// собственные копии функций. Сломай формулу в index.html — сторожа остались бы
// зелёными, потому что проверяли не её. Теперь копий нет: тест падает ровно
// тогда, когда ломается код, который видит пользователь.
//
// pageCode(file, names, globals) → объект { name: значение } из страницы.
//   names — имена объявлений: `function name(`, `const name =`, `let name =`,
//           `window.name = function` (берётся целиком, до парной скобки/`;`).
//   globals — что подложить в область видимости (заглушки I18N, window и т.п.).
import { readFileSync } from "fs";

const dir = new URL("./", import.meta.url);

function inlineScripts(html) {
  return [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)]
    .map((m) => m[1]).join("\n");
}

// С позиции start (на «{» или «(»-несущем выражении) идём до конца объявления:
// баланс скобок с учётом строк и шаблонов, затем до ближайшего «;» или
// перевода строки на нулевой глубине.
function declarationEnd(src, start) {
  let depth = 0, i = start, quote = null;
  for (; i < src.length; i++) {
    const c = src[i];
    if (quote) {
      if (c === "\\") { i++; continue; }
      if (c === quote) quote = null;
      continue;
    }
    if (c === '"' || c === "'" || c === "`") { quote = c; continue; }
    if (c === "/" && src[i + 1] === "/") { i = src.indexOf("\n", i); if (i < 0) return src.length; continue; }
    if (c === "{" || c === "(" || c === "[") depth++;
    else if (c === "}" || c === ")" || c === "]") {
      depth--;
      if (depth === 0 && c === "}" && /^function\b/.test(src.slice(start))) return i + 1;
    } else if (depth === 0 && (c === ";" || c === "\n") && i > start) {
      const head = src.slice(start, i);
      if (/[=]/.test(head)) return i + 1;
    }
  }
  return i;
}

export function pageCode(file, names, globals = {}) {
  const src = inlineScripts(readFileSync(new URL(file, dir), "utf8"));
  const parts = [];
  for (const name of names) {
    const re = new RegExp(
      `(^|\\n)\\s*(function\\s+${name}\\s*\\(|(?:const|let|var)\\s+${name}\\s*=|window\\.${name}\\s*=)`);
    const m = re.exec(src);
    if (!m) throw new Error(`${file}: объявление «${name}» не найдено`);
    const from = src.indexOf(m[2], m.index);
    parts.push(src.slice(from, declarationEnd(src, from)));
  }
  const keys = Object.keys(globals);
  const ret = names.map((n) => `${JSON.stringify(n)}: (typeof ${n} !== "undefined" ? ${n} : window.${n})`).join(", ");
  // Исполняется код самой страницы из репозитория (не внешний ввод) — в этом
  // и смысл сторожа: проверить именно то, что уедет пользователю.
  const fn = new Function(...keys, `${parts.join("\n")}\nreturn { ${ret} };`);
  return fn(...keys.map((k) => globals[k]));
}
