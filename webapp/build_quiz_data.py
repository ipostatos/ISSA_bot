"""
Экспорт банка вопросов в статический JS для Mini App «Тесты».

questions.json  ->  webapp/quiz_data.js  (глобал window.QUIZ_DATA)

Mini App — статическая страница, поэтому вопросы вшиваем в файл. После любого
изменения банка перегенерировать:

    python webapp/build_quiz_data.py

Кладём минимум полей: id, topic, q, options, answer, expl (для мгновенной
подсветки и пояснения прямо в приложении). Никаких «ключей экзамена» —
это тот же открытый банк, что и в чат-боте.
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # каталог bot/
SRC = BASE / "questions.json"
OUT = Path(__file__).resolve().parent / "quiz_data.js"

# Должно совпадать с bot.py.
EXAM_SIZE = 100
EXAM_PASS_PERCENT = 75


def main() -> None:
    questions = json.loads(SRC.read_text(encoding="utf-8"))
    slim = [
        {
            "id": q["id"],
            "topic": q["topic"],
            "q": q["q"],
            "options": q["options"],
            "answer": q["answer"],
            "expl": q.get("expl", ""),
        }
        for q in questions
    ]
    topics = sorted({q["topic"] for q in slim})
    payload = {
        "version": 1,
        "examSize": EXAM_SIZE,
        "passPercent": EXAM_PASS_PERCENT,
        "topics": topics,
        "questions": slim,
    }
    js = (
        "// АВТОГЕНЕРАЦИЯ — не редактировать вручную.\n"
        "// Источник: questions.json. Перегенерация: python webapp/build_quiz_data.py\n"
        "window.QUIZ_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    OUT.write_text(js, encoding="utf-8")
    print(f"OK: {len(slim)} вопросов, {len(topics)} тем -> {OUT.name} "
          f"({OUT.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    main()
