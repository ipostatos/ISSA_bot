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
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # каталог bot/
SRC = BASE / "questions.json"
OUT = Path(__file__).resolve().parent / "quiz_data.js"

sys.path.insert(0, str(BASE))
import konspekt_text as kt  # источник тем конспекта (single source of truth)

# Должно совпадать с bot.py.
EXAM_SIZE = 100
EXAM_PASS_PERCENT = 75

# Тема вопроса (topic в questions.json) → ключи тем конспекта, где это изучают.
# Используется «лампочкой-источником» в тренировке и в фидбеке после теста.
# Первый ключ — основной (на него ведёт лампочка). Все ключи обязаны
# существовать в konspekt_text.KONSPEKT — это проверяется ниже.
TOPIC_TO_KONSPEKT = {
    "Навигация":        ["nav", "fix"],
    "COLREG":           ["colreg"],
    "VHF / SRC":        ["instruments"],
    "Огни и знаки":     ["lights"],
    "Безопасность":     ["skipper", "firstaid"],
    "IALA":             ["iala"],
    "Метео":            ["meteo", "beaufort"],
    "Якорение":         ["anchor"],
    "Терминология":     ["skipper", "nav"],
    "Маневры":          ["motor", "sail"],
    "Паруса":           ["sail"],
    "Принятие яхты":    ["skipper"],
    "Звуковые сигналы": ["lights"],
    "Планирование":     ["passage"],
    "Практика":         ["fix", "nav"],
}


def main() -> None:
    questions = json.loads(SRC.read_text(encoding="utf-8"))

    # — целостность маппинга: каждая тема вопросов покрыта, все ключи реальны —
    q_topics = {q["topic"] for q in questions}
    missing = q_topics - set(TOPIC_TO_KONSPEKT)
    if missing:
        raise SystemExit(f"TOPIC_TO_KONSPEKT не покрывает темы: {sorted(missing)}")
    bad = {k for keys in TOPIC_TO_KONSPEKT.values()
             for k in keys if k not in kt.KONSPEKT}
    if bad:
        raise SystemExit(f"TOPIC_TO_KONSPEKT ссылается на несуществующие темы конспекта: {sorted(bad)}")

    slim = [
        {
            "id": q["id"],
            "topic": q["topic"],
            "q": q["q"],
            "options": q["options"],
            "answer": q["answer"],
            "expl": q.get("expl", ""),
            # ключи тем конспекта для «лампочки-источника» (первый — основной)
            "src": TOPIC_TO_KONSPEKT.get(q["topic"], []),
        }
        for q in questions
    ]
    topics = sorted({q["topic"] for q in slim})
    # справочник тем конспекта: ключ → кнопка (для подписи ссылок-источников)
    konspekt_titles = {key: kt.KONSPEKT_BTN[key] for key in kt.KONSPEKT_ORDER}
    payload = {
        "version": 1,
        "examSize": EXAM_SIZE,
        "passPercent": EXAM_PASS_PERCENT,
        "topics": topics,
        "konspekt": konspekt_titles,
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
