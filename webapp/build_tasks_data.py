"""
Экспорт практических задач в статический JS для Mini App «Задачки».

marine.TASKS (S-D-T, ETA) + tides.TASKS (правило 12)  ->  webapp/tasks_data.js

Перегенерация после изменения банков:
    python webapp/build_tasks_data.py

У задачи: id, text (условие), answer, unit, tol (допуск), solution.
Проверка ответа в приложении — то же сравнение с допуском, что в Python.
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "tasks_data.js"

import sys
sys.path.insert(0, str(BASE))
import marine   # noqa: E402
import tides    # noqa: E402


def main() -> None:
    tasks = []
    for t in marine.TASKS:
        tasks.append({"id": t.id, "text": t.text, "answer": t.answer,
                      "unit": t.unit, "tol": t.tol, "solution": t.solution,
                      "cat": "nav"})
    for t in tides.TASKS:
        tasks.append({"id": t.id, "text": t.text, "answer": t.answer,
                      "unit": "м", "tol": t.tol, "solution": t.solution,
                      "cat": "tide"})
    payload = {"version": 1, "tasks": tasks}
    js = (
        "// АВТОГЕНЕРАЦИЯ — не редактировать вручную.\n"
        "// Источник: marine.TASKS + tides.TASKS. "
        "Перегенерация: python webapp/build_tasks_data.py\n"
        "window.TASKS_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    OUT.write_text(js, encoding="utf-8")
    print(f"OK: {len(tasks)} задач -> {OUT.name} ({OUT.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    main()
