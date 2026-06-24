"""
Экспорт шпаргалок, узлов и задач T-V-M-D-C в статический JS для Mini App.

content.py (CHEATSHEETS/CHEATSHEET_IMAGES/KNOTS) + nav_tasks.TASKS
    ->  webapp/content_data.js

Перегенерация:
    python webapp/build_content_data.py
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "content_data.js"

import sys
sys.path.insert(0, str(BASE))
import content     # noqa: E402
import nav_tasks   # noqa: E402


def main() -> None:
    # Шпаргалки: ключ -> {title, html, images}. Узлы вынесены отдельно.
    sheets = []
    for key, (title, html) in content.CHEATSHEETS.items():
        item = {
            "key": key,
            "title": content.CHEATSHEET_BTN.get(key, title),
            "html": html,
            "images": content.CHEATSHEET_IMAGES.get(key, []),
        }
        if key == "knots":
            # к узлам прикрепляем пошаговые карточки с фото
            item["knots"] = [
                {"title": kt[0], "html": kt[1], "steps": kt[2]}
                for kt in content.KNOTS.values()
            ]
        sheets.append(item)

    # Задачи T-V-M-D-C (поправки компаса).
    nav = [
        {"id": t.id, "text": t.text, "answer": t.answer,
         "solution": t.solution, "starred": bool(t.starred)}
        for t in nav_tasks.TASKS
    ]

    payload = {"version": 1, "sheets": sheets, "navTasks": nav}
    js = (
        "// АВТОГЕНЕРАЦИЯ — не редактировать вручную.\n"
        "// Источник: content.py + nav_tasks.py. "
        "Перегенерация: python webapp/build_content_data.py\n"
        "window.CONTENT_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    OUT.write_text(js, encoding="utf-8")
    print(f"OK: {len(sheets)} шпаргалок, {len(nav)} задач T-V-M-D-C -> "
          f"{OUT.name} ({OUT.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    main()
