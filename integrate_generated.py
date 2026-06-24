 """
Интеграция сгенерированных+проверенных вопросов в questions.json.

Берёт JSON-файл вида {"kept":[{topic,q,options,answer,expl,...}], ...}
(вывод воркфлоу issa-build-500), объединяет с текущим банком, удаляет
точные и смысловые дубли (та же логика, что в merge_dedup.py), назначает id,
балансирует по темам до целевого размера и пишет questions.json.

Запуск:
    python integrate_generated.py generated.json [--target 500]
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).parent
QUESTIONS_FILE = BASE_DIR / "questions.json"

# Переиспользуем нормализацию и подпись факта из merge_dedup.
sys.path.insert(0, str(BASE_DIR))
from merge_dedup import norm_key, fact_signature, slug  # noqa: E402


def load_existing() -> list[dict]:
    return json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))


def valid(q: dict) -> bool:
    if not q.get("q") or not isinstance(q.get("options"), list):
        return False
    opts = [o for o in q["options"] if str(o).strip()]
    if len(opts) != 4:
        return False
    a = q.get("answer")
    if not isinstance(a, int) or not (0 <= a < 4):
        return False
    # варианты должны различаться
    if len({norm_key(o) for o in q["options"]}) < 4:
        return False
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("generated")
    ap.add_argument("--target", type=int, default=500)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads(Path(args.generated).read_text(encoding="utf-8"))
    new_items = data.get("kept", data if isinstance(data, list) else [])

    existing = load_existing()

    # Индексы для дедупа по существующей базе.
    seen_text = {norm_key(q["q"]) for q in existing}
    seen_sig = {fact_signature(q) for q in existing if fact_signature(q)}

    per_topic_existing = defaultdict(int)
    for q in existing:
        per_topic_existing[q["topic"]] += 1

    added, drop_dupe, drop_invalid = [], 0, 0
    for it in new_items:
        q = {
            "topic": (it.get("topic") or "Прочее").strip(),
            "q": (it.get("q") or "").strip(),
            "options": [str(o).strip() for o in it.get("options", [])][:4],
            "answer": it.get("answer", 0),
            "expl": (it.get("expl") or "").strip(),
        }
        if not valid(q):
            drop_invalid += 1
            continue
        k = norm_key(q["q"])
        sig = fact_signature(q)
        if k in seen_text or (sig and sig in seen_sig):
            drop_dupe += 1
            continue
        seen_text.add(k)
        if sig:
            seen_sig.add(sig)
        added.append(q)

    # Балансировка до target: не раздувать одну тему сверх меры.
    # Сначала все существующие, затем добавленные, но обрезаем общий размер.
    combined = list(existing)
    # сортируем добавленные так, чтобы добивать «бедные» темы первыми
    added.sort(key=lambda q: per_topic_existing[q["topic"]])
    for q in added:
        if len(combined) >= args.target:
            break
        combined.append(q)
        per_topic_existing[q["topic"]] += 1

    # Назначаем id заново (стабильно по темам).
    counters = defaultdict(int)
    for q in combined:
        base = slug(q["topic"])
        counters[base] += 1
        q["id"] = f"{base}-{counters[base]:03}"

    # Финальная форма (study сохраняем, если был).
    out = []
    for q in combined:
        item = {
            "id": q["id"], "topic": q["topic"], "q": q["q"],
            "options": q["options"], "answer": q["answer"], "expl": q.get("expl", ""),
        }
        if q.get("study"):
            item["study"] = q["study"]
        out.append(item)

    from collections import Counter
    dist = Counter(q["topic"] for q in out)
    print(f"Существовало:        {len(existing)}")
    print(f"Сгенерировано (kept):{len(new_items)}")
    print(f"  отклонено дублей:  {drop_dupe}")
    print(f"  отклонено невалид: {drop_invalid}")
    print(f"  добавлено:         {len(out) - len(existing)}")
    print(f"ИТОГО:               {len(out)}")
    print("\nРаспределение по темам:")
    for t, n in dist.most_common():
        # печать через буфер из-за cp1251 на Windows
        line = f"  {n:4}  {t}\n"
        sys.stdout.buffer.write(line.encode(sys.stdout.encoding or "utf-8", "replace"))

    if args.dry_run:
        print("\n[dry-run] questions.json не изменён.")
        return
    QUESTIONS_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nЗаписано {len(out)} вопросов в {QUESTIONS_FILE}")


if __name__ == "__main__":
    main()
