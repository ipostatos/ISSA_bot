"""
Импорт дополнительных вопросов из CSV в questions.json.

Формат CSV (с заголовком, разделитель «,»):
    topic,question,A,B,C,D,answer,explanation
где answer — буква A/B/C/D (или индекс 0..3 / 1..4).

Дубликаты (по тексту вопроса) пропускаются — вопросы не повторяются.
ID присваивается автоматически: <slug-темы>-<номер>.

Использование:
    python import_csv.py путь/к/новым_вопросам.csv
"""

import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).parent
QUESTIONS_FILE = BASE_DIR / "questions.json"

LETTER_TO_IDX = {"A": 0, "B": 1, "C": 2, "D": 3, "А": 0, "Б": 1, "В": 2, "Г": 3}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "q"


def parse_answer(value: str, n_options: int) -> int:
    value = value.strip()
    if value.upper() in LETTER_TO_IDX:
        return LETTER_TO_IDX[value.upper()]
    if value.isdigit():
        idx = int(value)
        return idx - 1 if idx >= 1 and idx > n_options - 1 else idx
    raise ValueError(f"Не понял ответ: {value!r}")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        sys.exit(f"Файл не найден: {csv_path}")

    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    existing_texts = {q["q"].strip().lower() for q in questions}
    existing_ids = {q["id"] for q in questions}

    added, skipped = 0, 0
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            q_text = (row.get("question") or "").strip()
            if not q_text:
                continue
            if q_text.lower() in existing_texts:
                skipped += 1
                continue
            options = [(row.get(k) or "").strip() for k in ("A", "B", "C", "D")]
            options = [o for o in options if o]
            if len(options) < 2:
                skipped += 1
                continue
            try:
                answer = parse_answer(row.get("answer", ""), len(options))
            except ValueError as e:
                print("Пропуск (ошибка ответа):", e)
                skipped += 1
                continue
            if not (0 <= answer < len(options)):
                skipped += 1
                continue
            topic = (row.get("topic") or "Прочее").strip()
            base = slugify(topic)
            n = 1
            new_id = f"{base}-imp-{n:03}"
            while new_id in existing_ids:
                n += 1
                new_id = f"{base}-imp-{n:03}"
            existing_ids.add(new_id)
            existing_texts.add(q_text.lower())
            questions.append({
                "id": new_id,
                "topic": topic,
                "q": q_text,
                "options": options,
                "answer": answer,
                "expl": (row.get("explanation") or "").strip(),
            })
            added += 1

    QUESTIONS_FILE.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Готово. Добавлено: {added}, пропущено дубликатов/ошибок: {skipped}.")
    print(f"Всего в банке: {len(questions)} вопросов.")


if __name__ == "__main__":
    main()
