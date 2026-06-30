"""
Экспорт банка Sternik motorowodny в статический JS для Mini App «Лицензии».

questions_sternik.json  ->  webapp/sternik_data.js  (глобал window.STERNIK_DATA)

Вопросы хранятся в ГИБРИДНОМ виде (польский + русский в одном поле через \n),
ровно как на экзаменационном листе — ничего не переводим. У части вопросов есть
картинка (знак/огни), путь относительно webapp/.

Польский экзамен: 75 вопросов, проходной 65 правильных, 90 минут.

Перегенерация после изменения банка:
    python webapp/build_sternik_data.py
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent          # bot/
SRC = Path(__file__).resolve().parent / "questions_sternik.json"
OUT = Path(__file__).resolve().parent / "sternik_data.js"

# Параметры экзамена Sternik motorowodny (PZŻ): 75 вопросов, 65 верных, 90 мин.
EXAM_SIZE = 75
EXAM_PASS = 65
EXAM_MINUTES = 90

BANK_REVISION = "июнь 2026"


def main() -> None:
    questions = json.loads(SRC.read_text(encoding="utf-8"))

    # целостность: id уникальны, ответ есть, 3 варианта
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), "дубли id в questions_sternik.json"
    bad = [q["id"] for q in questions
           if q.get("answer") is None or not (0 <= q["answer"] < len(q["options"]))]
    assert not bad, f"вопросы с битым ответом: {bad}"
    bad_opts = [q["id"] for q in questions if len(q["options"]) < 2]
    assert not bad_opts, f"вопросы без вариантов: {bad_opts}"

    def slim(q):
        d = {
            "id": q["id"],
            "q": q["q"],                 # гибрид PL\nRU
            "options": q["options"],     # каждый вариант — гибрид PL\nRU
            "answer": q["answer"],
        }
        if q.get("topic"):
            d["topic"] = q["topic"]
        if q.get("image"):
            d["image"] = q["image"]      # путь относительно webapp/
        if q.get("ref"):
            d["ref"] = q["ref"]
        return d

    slim_qs = [slim(q) for q in questions]
    with_img = sum(1 for q in slim_qs if "image" in q)

    payload = {
        "version": 1,
        "license": "sternik",
        "title": "Sternik motorowodny",
        "examSize": EXAM_SIZE,
        "examPass": EXAM_PASS,
        "examMinutes": EXAM_MINUTES,
        "meta": {
            "revision": BANK_REVISION,
            "total": len(slim_qs),
            "withImage": with_img,
        },
        "questions": slim_qs,
    }
    js = (
        "// АВТОГЕНЕРАЦИЯ — не редактировать вручную.\n"
        "// Источник: questions_sternik.json. Перегенерация: python webapp/build_sternik_data.py\n"
        "window.STERNIK_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    OUT.write_text(js, encoding="utf-8")
    print(f"OK: {len(slim_qs)} вопросов ({with_img} с картинками) -> {OUT.name} "
          f"({OUT.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    main()
