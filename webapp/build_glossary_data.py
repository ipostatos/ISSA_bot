"""
Экспорт словаря яхтсмена в статический JS для Mini App «Словарь».

glossary.py (YACHTING_GLOSSARY/CATEGORY_*)  ->  webapp/glossary_data.js

Перегенерация после изменения словаря:
    python webapp/build_glossary_data.py

Структура: categories[{key, title, icon, terms:[{term, aliases, definition,
example}]}]. Поиск в приложении — по term/aliases/definition.
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "glossary_data.js"

import sys
sys.path.insert(0, str(BASE))
import glossary  # noqa: E402


def main() -> None:
    cats = []
    for cat in glossary.CATEGORY_ORDER:
        terms = []
        for it in glossary.YACHTING_GLOSSARY[cat]:
            terms.append({
                "term": it["term"],
                "aliases": it.get("aliases", []),
                "definition": it.get("definition", ""),
                "example": it.get("example", ""),
            })
        cats.append({
            "key": glossary.CATEGORY_KEY[cat],
            "title": glossary.CATEGORY_BTN.get(cat, cat),
            "full": cat,
            "icon": glossary.CATEGORY_ICONS.get(cat, "📚"),
            "terms": terms,
        })
    total = sum(len(c["terms"]) for c in cats)
    payload = {"version": 1, "total": total, "categories": cats}
    js = (
        "// АВТОГЕНЕРАЦИЯ — не редактировать вручную.\n"
        "// Источник: glossary.py. Перегенерация: python webapp/build_glossary_data.py\n"
        "window.GLOSSARY_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    OUT.write_text(js, encoding="utf-8")
    print(f"OK: {total} терминов, {len(cats)} категорий -> {OUT.name} "
          f"({OUT.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    main()
