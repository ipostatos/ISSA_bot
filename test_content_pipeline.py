"""
Тесты контент-конвейера (волна C): стабильные id, сохранение полей,
сторож стабильности id.

Сторож гоняется по-настоящему: во временном git-репозитории делаются
коммиты с банком, затем scripts/check_question_id_stability.py --repo.

Запуск:  python test_content_pipeline.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from bank_ids import IdAllocator, canon, reconcile_ids  # noqa: E402
import merge_dedup  # noqa: E402

GUARD = BASE / "scripts" / "check_question_id_stability.py"
fails = 0


def ok(cond, name):
    global fails
    print(("  OK   " if cond else "  FAIL ") + name)
    if not cond:
        fails += 1


# ── bank_ids ──
print("bank_ids")
ok(canon("  á  b\n c ") == "á b c", "canon: NFC + схлопывание пробелов")

alloc = IdAllocator(["q-001", "q-007", "colreg-050", "q-x"], )
ok(alloc.new() == "q-008", "распределитель: следующий после максимума q-*")
ok(alloc.new() == "q-009", "распределитель: монотонно")
alloc = IdAllocator(["q-003"] + ["q-120"])  # q-120 — удалённый id из истории
ok(alloc.new() == "q-121", "распределитель: не выдаёт id из истории")

existing = [{"id": "colreg-012", "q": "Правило 5?"}, {"id": "q-004", "q": "Дубль"},
            {"id": "q-009", "q": "Дубль"}]
items = [{"q": "Дубль"}, {"q": "  Правило   5? "}, {"q": "Дубль"}, {"q": "Новый"}, {"q": "Дубль"}]
st = reconcile_ids(existing, items)
ok([it["id"] for it in items] == ["q-004", "colreg-012", "q-009", "q-010", "q-011"],
   "reconcile: текст сохраняет id, дубли по одному разу, новые — вперёд")
ok(st == {"kept": 3, "new": 2}, "reconcile: счётчики")

# ── merge_dedup: id и неизвестные поля не теряются ──
print("merge_dedup")
orig = {"id": "colreg-061", "topic": "COLREG", "q": "Q?", "options": ["a", "b", "c", "d"],
        "answer": 2, "expl": "", "why": ["w"], "ref": "R", "difficulty": 3}
it = {"topic": "COLREG", "q": "Q?", "options": orig["options"], "answer": 2,
      "expl": "обогащено", "study": "", "_src": "questions.json", "_orig": orig}
new = {"topic": "Новая тема", "q": "Новый?", "options": ["a", "b", "c", "d"], "answer": 0,
       "expl": "e", "study": "", "_src": "x.csv"}
merge_dedup.historic_ids = lambda *_: {"q-900"}      # история банка без git
stats = merge_dedup.assign_ids([it, new])
out_old, out_new = merge_dedup.output_item(it), merge_dedup.output_item(new)
ok(out_old["id"] == "colreg-061", "существующий вопрос сохранил id (старый префикс)")
ok(all(out_old.get(k) == orig[k] for k in ("why", "ref", "difficulty")),
   "why/ref/difficulty сохранены")
ok(out_old["expl"] == "обогащено", "пустое expl обогащено из дубля")
ok(out_new["id"] == "q-901", "новый вопрос — после максимума истории")
ok(stats == {"kept": 1, "new": 1}, "счётчики assign_ids")


# ── сторож стабильности id ──
print("сторож id")


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def run_guard(repo, base="HEAD^"):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(GUARD), "--repo", str(repo), "--base", base],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    return r.returncode, r.stdout


ST = [
    {"id": "st-001", "q": "Przedstawiony znak oznacza:", "options": ["x", "y", "z"], "answer": 0,
     "image": "images/st/a.png"},
    {"id": "st-002", "q": "Przedstawiony znak oznacza:", "options": ["x", "y", "z"], "answer": 1,
     "image": "images/st/b.png"},
    {"id": "st-003", "q": "Pytanie?", "options": ["p", "q", "r"], "answer": 2},
]


def scenario(mutate, fixes=None, base="HEAD^"):
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "t@t")
        git(repo, "config", "user.name", "t")
        (repo / "webapp").mkdir()
        (repo / "scripts").mkdir()
        for name in ("questions.json", "webapp/questions_zeglarz.json"):
            (repo / name).write_text("[]", encoding="utf-8")
        bank = repo / "webapp" / "questions_sternik.json"
        bank.write_text(json.dumps(ST), encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "base")
        qs = json.loads(json.dumps(ST))
        mutate(qs)
        bank.write_text(json.dumps(qs), encoding="utf-8")
        if fixes is not None:
            (repo / "scripts" / "answer_fixes.json").write_text(json.dumps(fixes), encoding="utf-8")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "--allow-empty", "-m", "change")
        return run_guard(repo, base)


def swap_images(qs):
    qs[0]["image"], qs[1]["image"] = qs[1]["image"], qs[0]["image"]


def flip_answer(qs):
    qs[2]["answer"] = 0


def fix_typo(qs):
    qs[2]["q"] = "Pytanie poprawione?"


def renumber(qs):
    qs[2]["id"] = "st-004"


code, out = scenario(lambda qs: None)
ok(code == 0, "без изменений — PASS")
code, out = scenario(swap_images)
ok(code == 1 and "НЕИЗМЕНЁННЫМ" in out, "перестановка картинок между дублями текста — FAIL")
code, out = scenario(flip_answer)
ok(code == 1 and "сменили правильный ответ" in out, "смена answer при тех же options — FAIL")
code, out = scenario(flip_answer, fixes={"st-003": "p"})
ok(code == 0, "смена answer, подтверждённая в answer_fixes.json — PASS")
code, out = scenario(flip_answer, fixes={"st-003": "q"})
ok(code == 1, "реестр с другим текстом ответа не спасает — FAIL")
code, out = scenario(fix_typo)
ok(code == 0, "правка опечатки под тем же id — PASS")
code, out = scenario(renumber)
ok(code == 1, "перенумерация неизменённого вопроса — FAIL")
code, out = scenario(lambda qs: None, base="0123456789abcdef0123456789abcdef01234567")
ok(code == 1 and "НЕ выполнена" in out, "база не резолвится (force-push) — FAIL, а не молчаливый PASS")

print()
if fails:
    print(f"ПРОВАЛЕНО: {fails}")
    sys.exit(1)
print("OK: content pipeline tests passed")
