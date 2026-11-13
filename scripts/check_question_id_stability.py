#!/usr/bin/env python3
"""
Сторож стабильности id вопросов (волна 1, шаг 0).

id вопроса — это ключ, по которому хранится прогресс живых людей: seen/wrong
у бота (progress/<user_id>.json), SRS-коробки на устройствах и в state.db,
solved польских лицензий. Прежний assign_ids строил id из позиции внутри темы,
и одна перегенерация банка молча перенумеровывала бо́льшую часть id — прогресс
всех пользователей начинал указывать не на те вопросы, причём БЕЗ единой
ошибки в логах (неизвестные id тихо игнорируются).

Утверждённый инвариант (владелец, 2026-07-31):
  ЗАПРЕЩЕНО   — неизменённый текст вопроса переехал на другой id;
              — два вопроса с одинаковым id;
  РАЗРЕШЕНО   — правка текста под тем же id (исправление опечаток);
              — новый вопрос с новым id;
  ПОКА ПРЕДУПРЕЖДЕНИЕ — удаление вопроса (станет ошибкой после реестра
              отставленных id, следующий этап).

Ключ вопроса = текст + картинка. В Sternik десятки вопросов с одинаковым
текстом («Przedstawiony znak oznacza:») различаются только полем image;
по одному тексту перестановка картинок между ними проходила бы молча, хотя
для человека это ровно «вопрос переехал на чужой id» (волна C, 13.11.2026).

Смена правильного ответа при НЕизменённых вариантах (тот же id, тот же
текст, те же options, другой answer) — ошибка, если правка не подтверждена
в scripts/answer_fixes.json: {"<id>": "<текст нового правильного варианта>"}.
Это ловит съехавший индекс при пересборке банка и оставляет путь для
осознанной правки ключа.

Намеренно НЕ сравниваем «хеш текста при id» — это запретило бы правку опечаток
и вернуло бы отклонённую модель хеш-id.

Нормализация текста только безопасная: Unicode NFC, strip, схлопывание
пробельных серий. Пунктуацию не трогаем и нечёткого сравнения не делаем:
чрезмерная нормализация склеивает РАЗНЫЕ вопросы в «одинаковые» и даёт
ложные срабатывания.

Одинаковые тексты с разными id (легальные дубли формулировок) сравниваются
через multimap: перенос ловится только там, где соответствие текст→id
однозначно В ОБЕИХ ревизиях; неоднозначное — предупреждение, не ошибка.

Запуск:
    python scripts/check_question_id_stability.py                 # база: HEAD^
    python scripts/check_question_id_stability.py --base <SHA>    # явная база
    python scripts/check_question_id_stability.py --repo <путь>   # другой репозиторий (для тестов)

Выход: 0 — стабильно; 1 — обнаружен перенос id или дубль id.
База не содержит банка (файл только появился) — банк считается новым, PASS.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# Банки, чьи id попадают в пользовательский прогресс. Пути — реальные
# (questions_zeglarz/sternik лежат в webapp/, см. build_*_data.py).
BANKS = [
    ("questions.json",                 "ISSA Inshore Skipper + SRC (RU)"),
    ("webapp/questions_zeglarz.json",  "Żeglarz jachtowy (PL)"),
    ("webapp/questions_sternik.json",  "Sternik motorowodny (PL)"),
]


def canon(text: str) -> str:
    """Безопасная каноникализация: NFC + strip + схлопывание пробелов."""
    s = unicodedata.normalize("NFC", str(text))
    return re.sub(r"\s+", " ", s).strip()


def qkey(q: dict) -> str:
    """Ключ соответствия: текст + картинка (у ISSA картинок нет — только текст)."""
    img = str(q.get("image") or "").strip()
    return canon(q.get("q", "")) + ("|" + img if img else "")


def load_answer_fixes(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): canon(v) for k, v in data.items() if not str(k).startswith("_")}


def load_questions(raw: str, label: str) -> list[dict]:
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("questions", [])
    if not isinstance(data, list):
        raise ValueError(f"{label}: неожиданная структура банка")
    return [q for q in data if isinstance(q, dict)]


def git_show(repo: Path, rev: str, path: str) -> str | None:
    """Содержимое файла в ревизии; None — файла в базе нет (банк новый)."""
    r = subprocess.run(
        ["git", "-C", str(repo), "show", f"{rev}:{path}"],
        capture_output=True, text=True, encoding="utf-8",
    )
    return r.stdout if r.returncode == 0 else None


def check_bank(repo: Path, base: str, path: str, label: str,
               answer_fixes: dict[str, str] | None = None) -> tuple[int, int]:
    """Возвращает (ошибок, предупреждений) по одному банку."""
    errors = warnings = 0

    new_file = repo / path
    if not new_file.exists():
        print(f"  ⚠ {label}: {path} отсутствует в рабочей копии — пропускаю")
        return 0, 1
    new_qs = load_questions(new_file.read_text(encoding="utf-8"), label)

    # ── уникальность id в текущей версии (проверяется всегда) ──
    seen_ids: dict[str, int] = defaultdict(int)
    for q in new_qs:
        seen_ids[str(q.get("id", ""))] += 1
    for qid, n in sorted(seen_ids.items()):
        if not qid:
            print(f"  ✗ {label}: вопрос без id")
            errors += 1
        elif n > 1:
            print(f"  ✗ {label}: id «{qid}» встречается {n} раз — id обязан быть уникален")
            errors += 1

    old_raw = git_show(repo, base, path)
    if old_raw is None:
        print(f"  · {label}: банка нет в базе ({base[:12]}) — считается новым, переносы не проверяются")
        return errors, warnings
    old_qs = load_questions(old_raw, label)

    def text_to_ids(qs: list[dict]) -> dict[str, list[str]]:
        m: dict[str, list[str]] = defaultdict(list)
        for q in qs:
            qid = str(q.get("id", ""))
            if qid:
                m[qkey(q)].append(qid)
        return m

    old_map = text_to_ids(old_qs)
    new_map = text_to_ids(new_qs)
    old_by_id = {str(q.get("id", "")): qkey(q) for q in old_qs}
    new_by_id = {str(q.get("id", "")): qkey(q) for q in new_qs}

    # ── ГЛАВНЫЙ инвариант: неизменённый текст не может сменить id ──
    moved: list[tuple[str, str, str]] = []
    for text, old_ids in old_map.items():
        new_ids = new_map.get(text)
        if not new_ids:
            continue                      # текст исчез или отредактирован — не наш случай
        if len(old_ids) != 1 or len(new_ids) != 1:
            # Легальные дубли формулировок (в Sternik 91 картиночный вопрос
            # различается только полем image при одинаковом тексте) —
            # однозначного соответствия текст→id нет, ложно не падаем.
            # Предупреждаем ТОЛЬКО если множество id у этого текста изменилось;
            # стабильные дубли шумом не считаем, иначе 7 предупреждений на
            # каждом чистом прогоне приучат их игнорировать.
            if sorted(old_ids) != sorted(new_ids):
                print(f"  ⚠ {label}: неоднозначный текст сменил набор id "
                      f"({sorted(old_ids)} → {sorted(new_ids)}) — проверьте руками: «{text[:60]}…»")
                warnings += 1
            continue
        if old_ids[0] != new_ids[0]:
            moved.append((old_ids[0], new_ids[0], text))
    if moved:
        print(f"  ✗ {label}: {len(moved)} вопрос(ов) с НЕИЗМЕНЁННЫМ текстом сменили id "
              f"— это перепутает прогресс пользователей:")
        for old_id, new_id, text in moved[:10]:
            print(f"      {old_id} → {new_id}  «{text[:70]}»")
        if len(moved) > 10:
            print(f"      … и ещё {len(moved) - 10}")
        errors += len(moved)

    # ── смена правильного ответа при тех же вариантах ──
    fixes = answer_fixes or {}
    old_full = {str(q.get("id", "")): q for q in old_qs}
    flipped = []
    for q in new_qs:
        qid = str(q.get("id", ""))
        o = old_full.get(qid)
        if not o or qkey(o) != qkey(q):
            continue
        if [canon(x) for x in o.get("options", [])] != [canon(x) for x in q.get("options", [])]:
            continue                      # варианты правились — это другой случай
        if o.get("answer") == q.get("answer"):
            continue
        opts = q.get("options", [])
        a = q.get("answer")
        new_right = canon(opts[a]) if isinstance(a, int) and 0 <= a < len(opts) else ""
        if fixes.get(qid) == new_right and new_right:
            print(f"  · {label}: {qid} — правильный ответ изменён осознанно (answer_fixes.json)")
            continue
        flipped.append((qid, o.get("answer"), a))
    if flipped:
        print(f"  ✗ {label}: {len(flipped)} вопрос(ов) сменили правильный ответ при тех же вариантах:")
        for qid, a0, a1 in flipped[:10]:
            print(f"      {qid}: answer {a0} → {a1}")
        print("    Если это исправление ключа — внесите id и ТЕКСТ нового правильного варианта"
              " в scripts/answer_fixes.json.")
        errors += len(flipped)

    # ── информация и предупреждения ──
    edited = [qid for qid, t in new_by_id.items()
              if qid in old_by_id and old_by_id[qid] != t]
    if edited:
        print(f"  · {label}: текст отредактирован под тем же id (разрешено): "
              f"{', '.join(edited[:8])}{' …' if len(edited) > 8 else ''}")

    removed = sorted(set(old_by_id) - set(new_by_id))
    if removed:
        print(f"  ⚠ {label}: удалено {len(removed)} id ({', '.join(removed[:8])}"
              f"{' …' if len(removed) > 8 else ''}) — пока предупреждение; "
              f"после появления реестра отставленных id станет проверкой на переиспользование")
        warnings += 1

    added = sorted(set(new_by_id) - set(old_by_id))
    if added:
        print(f"  · {label}: добавлено {len(added)} новых id (разрешено)")

    if not errors:
        print(f"  ✓ {label}: id стабильны "
              f"({len(new_qs)} вопросов, +{len(added)} / −{len(removed)} / правок текста: {len(edited)})")
    return errors, warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="Проверка стабильности id вопросов")
    ap.add_argument("--base", default="HEAD^",
                    help="базовая ревизия для сравнения (по умолчанию HEAD^; "
                         "в CI передаётся base SHA пул-реквеста или github.event.before)")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent),
                    help="корень git-репозитория (для тестов на копиях)")
    args = ap.parse_args()
    repo = Path(args.repo)

    # база должна резолвиться; на новой ветке/force-push CI передаёт HEAD^
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", f"{args.base}^{{commit}}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"⚠ база «{args.base}» не резолвится (первый коммит?) — сравнивать не с чем, PASS")
        return 0
    base = r.stdout.strip()
    print(f"База сравнения: {base[:12]}")

    total_err = total_warn = 0
    fixes = load_answer_fixes(repo / "scripts" / "answer_fixes.json")
    for path, label in BANKS:
        e, w = check_bank(repo, base, path, label, fixes)
        total_err += e
        total_warn += w

    if total_err:
        print(f"\nID STABILITY: ОШИБОК {total_err} — id пользовательского прогресса под угрозой.")
        print("Если перенос сделан осознанно (не бывает почти никогда) — сначала прочитайте")
        print("docs/CONTENT_PIPELINE.md, раздел «Иммутабельность id».")
        return 1
    print(f"\nID STABILITY OK (предупреждений: {total_warn})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
