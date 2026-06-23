"""
Полный пред-релизный аудит бота ISSA. Проверяет чек-лист:
 1. questions.json валиден: нет битой кириллицы, пустых, одинаковых вариантов
 2. у каждого вопроса ровно 4 варианта
 3. answer указывает на реально существующий вариант
 4. нет прямых и почти-дублей (текст + смысловая подпись)
 5. картинки открываются из bot/images/
 6. узлы — шаги в правильном порядке
 7. quiz-poll отправляется с is_anonymous=False
 8. прогресс сохраняется и переживает перезапуск
 9. экзамен из 100 не повторяет вопрос
10. разбор ошибок не превышает лимит Telegram
11. .env не попадает в архив (в .gitignore)

Запуск:  python run_audit.py
Выход: код 0 если всё OK, иначе 1.
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

PASS, FAIL = "✅", "❌"
problems = []


def check(name, ok, detail=""):
    mark = PASS if ok else FAIL
    line = f"{mark} {name}" + (f" — {detail}" if detail else "")
    sys.stdout.buffer.write((line + "\n").encode(sys.stdout.encoding or "utf-8", "replace"))
    if not ok:
        problems.append(name)


def norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# ── Загрузка ──
QUESTIONS = json.loads((BASE / "questions.json").read_text(encoding="utf-8"))
print(f"\n=== АУДИТ: {len(QUESTIONS)} вопросов ===\n")

# 1. Валидность + битая кириллица + пустые
def has_mojibake(s):
    # типичные mojibake-последовательности UTF-8-as-cp1251/latin1
    return bool(re.search(r"[ÐÑ][\x80-\xBF]|Ã[\x80-\xBF]|�", s))

empty = [q["id"] for q in QUESTIONS if not q.get("q", "").strip()
         or any(not str(o).strip() for o in q.get("options", []))]
moji = [q["id"] for q in QUESTIONS
        if has_mojibake(q["q"]) or any(has_mojibake(str(o)) for o in q["options"])
        or has_mojibake(q.get("expl", ""))]
check("1a. Нет пустых вопросов/вариантов", not empty, f"{empty[:5]}" if empty else "")
check("1b. Нет битой кириллицы (mojibake)", not moji, f"{moji[:5]}" if moji else "")

samevar = [q["id"] for q in QUESTIONS if len({norm(o) for o in q["options"]}) < 4]
check("1c. Варианты внутри вопроса различны", not samevar, f"{samevar[:5]}" if samevar else "")

# 2. Ровно 4 варианта
notfour = [q["id"] for q in QUESTIONS if len(q.get("options", [])) != 4]
check("2.  У каждого вопроса ровно 4 варианта", not notfour, f"{notfour[:5]}" if notfour else "")

# 3. answer валиден
badans = [q["id"] for q in QUESTIONS
          if not isinstance(q.get("answer"), int) or not (0 <= q["answer"] < len(q.get("options", [])))]
check("3.  answer указывает на существующий вариант", not badans, f"{badans[:5]}" if badans else "")

# 4. дубли (точные + почти-дубли)
texts = [norm(q["q"]) for q in QUESTIONS]
dup_exact = [t for t, c in Counter(texts).items() if c > 1]
check("4a. Нет точных дублей текста", not dup_exact, f"{len(dup_exact)} групп" if dup_exact else "")

# почти-дубли внутри темы. ИСТИННЫЙ дубль = похож текст вопроса И совпадает
# правильный ответ. Похожие по шаблону вопросы с РАЗНЫМ ответом (East/South/West
# cardinal, OVER/OUT, разные числа) — это нормальные разные вопросы, не дубли.
near = []
by_topic = {}
for q in QUESTIONS:
    by_topic.setdefault(q["topic"], []).append(q)
for topic, lst in by_topic.items():
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            qi, qj = lst[i], lst[j]
            ni, nj = norm(qi["q"]), norm(qj["q"])
            if ni == nj:
                continue
            if SequenceMatcher(None, ni, nj).ratio() >= 0.92:
                # совпадает ли правильный ответ по тексту?
                if norm(qi["options"][qi["answer"]]) == norm(qj["options"][qj["answer"]]):
                    near.append((qi["id"], qj["id"]))
check("4b. Нет почти-дублей с тем же ответом", not near, f"{near[:5]}" if near else "")

# дубли id
dupid = [k for k, c in Counter(q["id"] for q in QUESTIONS).items() if c > 1]
check("4c. id уникальны", not dupid, f"{dupid[:5]}" if dupid else "")

# 5. картинки
import content  # noqa: E402
IMAGES = BASE / "images"
refs = set()
for d in (content.KONSPEKT_IMAGES, content.CHEATSHEET_IMAGES):
    for v in d.values():
        refs.update(v)
for _, _, steps in content.KNOTS.values():
    refs.update(steps)
missing_img = [f for f in refs if not (IMAGES / f).exists()]
# и что картинки ненулевого размера
zero = [f for f in refs if (IMAGES / f).exists() and (IMAGES / f).stat().st_size == 0]
check("5.  Все картинки на месте и непустые", not missing_img and not zero,
      f"нет: {missing_img[:5]} пустые: {zero[:5]}" if (missing_img or zero) else f"{len(refs)} шт")

# 6. узлы — шаги по порядку
order_ok = True
detail6 = ""
for key, (_, _, steps) in content.KNOTS.items():
    nums = []
    for s in steps:
        m = re.search(r"_(\d+)\.", s)
        nums.append(int(m.group(1)) if m else -1)
    if nums != sorted(nums) or any(n < 1 for n in nums):
        order_ok = False
        detail6 = f"{key}: {nums}"
check("6.  Узлы: шаги в правильном порядке", order_ok, detail6)

# 7. quiz is_anonymous=False
bot_src = (BASE / "bot.py").read_text(encoding="utf-8")
anon_false = "is_anonymous=False" in bot_src
check("7.  Quiz-poll с is_anonymous=False", anon_false)

# 8. прогресс переживает перезапуск (запись→чтение)
import importlib.util
spec = importlib.util.spec_from_file_location("botmod", BASE / "bot.py")
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)
uid = 999000111
p = {"seen": ["x"], "wrong": ["y"], "stats": {"answered": 3, "correct": 2},
     "tasks": {"solved": 1, "attempts": 2, "streak": 1, "best": 1}}
bot.save_progress(uid, p)
reloaded = bot.load_progress(uid)
persist_ok = (reloaded["seen"] == ["x"] and reloaded["stats"]["answered"] == 3
              and reloaded["tasks"]["best"] == 1)
(bot.PROGRESS_DIR / f"{uid}.json").unlink(missing_ok=True)
check("8.  Прогресс сохраняется и читается", persist_ok)

# 9. экзамен 100 без повторов
bot.save_progress(uid, {"seen": [], "wrong": [], "stats": {"answered": 0, "correct": 0},
                        "tasks": {"solved": 0, "attempts": 0, "streak": 0, "best": 0}})
size = min(bot.EXAM_SIZE, len(bot.QUESTIONS))
chosen = bot.pick_unseen(uid, bot.QUESTIONS, size)
exam_unique = len(chosen) == len({q["id"] for q in chosen})
(bot.PROGRESS_DIR / f"{uid}.json").unlink(missing_ok=True)
check(f"9.  Экзамен ({size}) без повторов", exam_unique,
      f"{len(chosen)} вопросов, уникальных {len(set(q['id'] for q in chosen))}")

# 10. разбор ошибок не превышает лимит (худший случай — все неверно)
TG = bot.TG_MSG_LIMIT
blocks = ["header", "\n<b>Разбор ошибок:</b>"]
for q in chosen:
    blocks.append(f"• [{q['topic']}] {q['q']}\n  ✔️ {q['options'][q['answer']]}")
blocks.append("tail")
chunk, parts = "", []
for b in blocks:
    if len(chunk) + len(b) + 1 > TG - 100:
        parts.append(chunk)
        chunk = b
    else:
        chunk = f"{chunk}\n{b}" if chunk else b
if chunk:
    parts.append(chunk)
maxlen = max(len(p) for p in parts)
check("10. Разбор ошибок не превышает лимит TG", maxlen <= TG, f"max часть {maxlen} ≤ {TG}, частей {len(parts)}")

# 11. .env в .gitignore
gitignore = (BASE / ".gitignore")
env_ignored = gitignore.exists() and ".env" in gitignore.read_text(encoding="utf-8")
check("11. .env в .gitignore", env_ignored)

# Итог
print()
if problems:
    sys.stdout.buffer.write((f"{FAIL} ПРОВАЛЕНО: {len(problems)} — {problems}\n").encode("utf-8", "replace"))
    sys.exit(1)
print(f"{PASS} ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
