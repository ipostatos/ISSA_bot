"""
Стабильные id вопросов для скриптов, которые пересобирают банк.

id вопроса — ключ прогресса живых людей (seen/wrong в progress/, SRS-коробки
на устройствах и в state.db). Поэтому любой скрипт, который пересобирает
questions.json, обязан:

  1. оставить существующему вопросу ЕГО id — сопоставление по точному
     совпадению текста (canon: NFC + strip + схлопывание пробелов, без
     нечёткого сравнения — оно склеивает разные вопросы);
  2. выдать новому вопросу НОВЫЙ id из монотонного распределителя: номер
     больше любого, который когда-либо был в банке, — никогда не занятая
     или освободившаяся строка;
  3. не терять поля, которых скрипт не знает (`why`, `ref`, `difficulty`,
     `image`, …): существующий вопрос выходит из скрипта тем же словарём,
     в который дописаны только явно изменённые поля.

Тот же canon() использует сторож scripts/check_question_id_stability.py.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

# Префикс для новых вопросов ISSA. Старые префиксы (colreg-, iala-, vhf-src-)
# остаются у своих вопросов навсегда, новые им не выдаются: assign по теме
# когда-то строил id из позиции и мог выдать «colreg-012» другому вопросу.
NEW_ID_PREFIX = "q"

_NUM_TAIL = re.compile(r"-(\d+)$")


def canon(text: str) -> str:
    """Безопасная каноникализация: NFC + strip + схлопывание пробелов."""
    s = unicodedata.normalize("NFC", str(text or ""))
    return re.sub(r"\s+", " ", s).strip()


def max_id_number(ids, prefix: str = NEW_ID_PREFIX) -> int:
    """Наибольший номер среди id вида '<prefix>-NNN'."""
    best = 0
    for qid in ids:
        qid = str(qid)
        if not qid.startswith(prefix + "-"):
            continue
        m = _NUM_TAIL.search(qid)
        if m and qid[: m.start()] == prefix:
            best = max(best, int(m.group(1)))
    return best


class IdAllocator:
    """Монотонная выдача новых id: только вперёд от максимума, без дыр-переиспользований."""

    def __init__(self, known_ids, prefix: str = NEW_ID_PREFIX, width: int = 3):
        self.prefix = prefix
        self.width = width
        self.taken = {str(i) for i in known_ids}
        self.next = max_id_number(self.taken, prefix) + 1

    def new(self) -> str:
        while True:
            qid = f"{self.prefix}-{self.next:0{self.width}}"
            self.next += 1
            if qid not in self.taken:
                self.taken.add(qid)
                return qid


def historic_ids(repo, path: str) -> set[str]:
    """Все id, когда-либо бывшие в банке `path` по истории git (best effort).

    Нужны распределителю: удалённый вопрос мог оставить свой id в прогрессе
    людей, и выдать эту строку новому вопросу — значит тихо приписать чужую
    историю. Без git (архив, CI без истории) возвращает пустое множество.
    """
    import json
    import subprocess
    try:
        revs = subprocess.run(
            ["git", "-C", str(repo), "rev-list", "--all", "--", path],
            capture_output=True, text=True, check=True,
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return set()
    out: set[str] = set()
    for rev in revs:
        r = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{path}"],
                           capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            continue
        try:
            data = json.loads(r.stdout)
        except ValueError:
            continue
        if isinstance(data, dict):
            data = data.get("questions", [])
        out.update(str(q["id"]) for q in data if isinstance(q, dict) and q.get("id"))
    return out


def reconcile_ids(existing: list[dict], items: list[dict],
                  extra_known_ids=(), prefix: str = NEW_ID_PREFIX) -> dict:
    """Проставляет id элементам `items` (in place) и возвращает счётчики.

    Элемент с текстом, который есть в `existing`, получает id того вопроса.
    Одинаковые тексты (легальные дубли формулировок) разбираются по порядку:
    каждый старый id выдаётся не более одного раза. Остальные получают новые
    id из IdAllocator. `extra_known_ids` — id, которые нельзя выдавать, даже
    если их сейчас нет в банке (удалённые раньше, из истории git).
    """
    pool: dict[str, list[str]] = defaultdict(list)
    for q in existing:
        qid = q.get("id")
        if qid:
            pool[canon(q.get("q", ""))].append(str(qid))

    alloc = IdAllocator([q.get("id") for q in existing if q.get("id")]
                        + [str(i) for i in extra_known_ids], prefix=prefix)
    used: set[str] = set()
    kept = fresh = 0
    for it in items:
        candidates = pool.get(canon(it.get("q", "")), [])
        while candidates and candidates[0] in used:
            candidates.pop(0)
        if candidates:
            it["id"] = candidates.pop(0)
            kept += 1
        else:
            it["id"] = alloc.new()
            fresh += 1
        used.add(it["id"])
    return {"kept": kept, "new": fresh}
