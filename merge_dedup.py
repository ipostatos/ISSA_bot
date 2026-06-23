"""
Объединение нескольких баз вопросов + глубокий анализ дубликатов.

Что делает:
  1. Читает существующий questions.json и все CSV-файлы из папки sources/
     (формат CSV: topic,question,A,B,C,D,answer,explanation[,study_material]).
  2. Нормализует текст вопросов (регистр, пробелы, пунктуация, латиница ↔ юникод).
  3. Удаляет ТОЧНЫЕ дубли (одинаковый нормализованный текст вопроса).
  4. Находит и помечает БЛИЗКИЕ (near-duplicate) вопросы по схожести (SequenceMatcher).
  5. Находит КОНФЛИКТЫ (одинаковый вопрос, но разный правильный ответ).
  6. Пишет итоговый questions.json и подробный отчёт dedup_report.txt.

Запуск:
    python merge_dedup.py                 # анализ + запись результата
    python merge_dedup.py --dry-run       # только анализ и отчёт, без записи
    python merge_dedup.py --threshold 0.90  # порог похожести (по умолчанию 0.88)
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

BASE_DIR = Path(__file__).parent
SOURCES_DIR = BASE_DIR / "sources"
QUESTIONS_FILE = BASE_DIR / "questions.json"
REPORT_FILE = BASE_DIR / "dedup_report.txt"

LETTER_TO_IDX = {"A": 0, "B": 1, "C": 2, "D": 3, "А": 0, "Б": 1, "В": 2, "Г": 3}
NEAR_DUP_THRESHOLD = 0.88


# ──────────────────────────── Нормализация ────────────────────────────

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def norm_key(text: str) -> str:
    """Ключ для сравнения вопросов: убираем регистр, пунктуацию, лишние пробелы."""
    text = unicodedata.normalize("NFKC", text or "").lower().strip()
    text = _PUNCT.sub(" ", text)
    text = _WS.sub(" ", text).strip()
    return text


def parse_answer(value: str, n_options: int) -> int | None:
    v = (value or "").strip().upper()
    if v in LETTER_TO_IDX:
        return LETTER_TO_IDX[v]
    if v.isdigit():
        idx = int(v)
        if 1 <= idx <= n_options:
            return idx - 1
        if 0 <= idx < n_options:
            return idx
    return None


def slug(topic: str) -> str:
    s = unicodedata.normalize("NFKD", topic or "")
    s = s.encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "q"


# ──────────────────────── Семантическая подпись (смысловые дубли) ─────────────
#
# Идея: два вопроса проверяют ОДИН факт, даже если сформулированы по-разному.
# Строим "подпись факта" из ключевых сущностей вопроса+ответа. Совпали подписи —
# вероятный смысловой дубль (выводим в отчёт для ручной проверки).
#
# Сигнатуры строятся по морским концептам:
#   • COLREG: номер правила (rule 5/6/8/…)
#   • Огни: комбинация цветов (red-red, red-white-red, green-white, white-red…)
#   • Звуки: число и тип гудков (1-short, 2-prolonged, 5-short…)
#   • IALA: кардинал/латераль + сторона/цвет + что спрашивают (свет/топ/обход)
#   • Навигация: набор чисел в задаче (S=D/T) или связка var/dev
#   • Терминология: какой ТЕРМИН определяется
#   • MOB/пожар/течь/газ: тип аварийной процедуры

# Морские лексические якоря → канонический тег факта.
_CONCEPT_PATTERNS: list[tuple[re.Pattern, str]] = []

def _cp(pat: str, tag: str):
    _CONCEPT_PATTERNS.append((re.compile(pat, re.IGNORECASE | re.UNICODE), tag))

# Огни (комбинации) — по-русски и по-английски.
_cp(r"\bred[\s\-]*over[\s\-]*red\b|два\s+красн\w*\s+(?:огн|верт)", "light:R-R(NUC)")
_cp(r"\bred[\s\-]*white[\s\-]*red\b|красн\w*[\s\-]*бел\w*[\s\-]*красн\w*", "light:R-W-R(RAM)")
_cp(r"\bтри\s+красн\w*|three\s+red\b|constrained\s+by\s+draught|огранич\w*\s+осадк", "light:3R(CBD)")
_cp(r"\bgreen[\s\-]*over[\s\-]*white\b|зел\w*\s+над\s+бел\w*|\bтрал(?:ен|ер|ит|я)\w*", "light:G-W(trawl)")
_cp(r"\bred[\s\-]*over[\s\-]*white\b|красн\w*\s+над\s+бел\w*", "light:R-W(fishing)")
_cp(r"\bwhite[\s\-]*over[\s\-]*red\b|бел\w*\s+над\s+красн\w*|лоцман|pilot", "light:W-R(pilot)")
_cp(r"два\s+черн\w*\s+шар|two\s+black\s+ball", "light:2balls(NUC-day)")
_cp(r"черн\w*\s+шар|black\s+ball|якорн\w*.*днем|днем.*якор", "light:ball(anchor-day)")

# Звуки (паттерн гудков).
_cp(r"один\s+коротк|1\s*short|\bone\s+short", "snd:1short(stbd)")
_cp(r"два\s+коротк|2\s*short|\btwo\s+short", "snd:2short(port)")
_cp(r"три\s+коротк|3\s*short|astern|маши?н\w*\s+назад", "snd:3short(astern)")
_cp(r"пять\s+коротк|5\s*short|five\s+short|сомнен|doubt|danger", "snd:5short(doubt)")
_cp(r"один\s+продолжит.*туман|туман.*один\s+продолжит|prolonged.*2\s*min", "snd:1prolonged(fog-underway)")

# IALA кардинальные.
_cp(r"north\s+cardinal|норд\w*\s+кардинал|кардинал\w*\s+north", "iala:N-cardinal")
_cp(r"south\s+cardinal|кардинал\w*\s+south", "iala:S-cardinal")
_cp(r"east\s+cardinal|кардинал\w*\s+east", "iala:E-cardinal")
_cp(r"west\s+cardinal|кардинал\w*\s+west", "iala:W-cardinal")
_cp(r"isolated\s+danger|изолирован\w*\s+опасн", "iala:isolated-danger")
_cp(r"safe\s+water|безопасн\w*\s+вод", "iala:safe-water")
_cp(r"special\s+mark|спец\w*\s+(?:знак|зон)|желт\w*.*крест", "iala:special-mark")
_cp(r"preferred\s+channel|предпочтительн\w*\s+канал|основн\w*\s+канал", "iala:preferred-channel")
_cp(r"регион\w*\s+a|region\s+a|латерал\w*|красн\w*.*слев|зел\w*.*справ", "iala:lateral-regionA")

# COLREG правила и ситуации.
_cp(r"rule\s*5|правил\w*\s*5|постоянн\w*\s+наблюден|look\s*-?\s*out", "colreg:rule5-lookout")
_cp(r"rule\s*6|правил\w*\s*6|безопасн\w*\s+скорост|safe\s+speed", "colreg:rule6-safespeed")
_cp(r"rule\s*8|правил\w*\s*8|ранн\w*.*действ|действ\w*.*избеж", "colreg:rule8-action")
_cp(r"rule\s*9|правил\w*\s*9|узк\w*\s+канал|narrow\s+channel", "colreg:rule9-narrow")
_cp(r"rule\s*10|правил\w*\s*10|tss|раздел\w*\s+движен", "colreg:rule10-tss")
_cp(r"rule\s*12|правил\w*\s*12|галс|tack|windward|наветрен|подветрен", "colreg:rule12-sail")
_cp(r"rule\s*13|правил\w*\s*13|обгон|overtak", "colreg:rule13-overtaking")
_cp(r"rule\s*14|правил\w*\s*14|навстреч|head[\s\-]*on|прямо.*встреч", "colreg:rule14-headon")
_cp(r"rule\s*15|правил\w*\s*15|пересек\w*\s+курс|crossing", "colreg:rule15-crossing")
_cp(r"rule\s*17|правил\w*\s*17|stand[\s\-]*on|сохран\w*\s+курс", "colreg:rule17-standon")
_cp(r"rule\s*18|правил\w*\s*18|приоритет|nuc.*ram|иерарх", "colreg:rule18-hierarchy")
_cp(r"rule\s*19|правил\w*\s*19|огранич\w*\s+видим|restricted\s+visib|туман", "colreg:rule19-restricted-vis")

# VHF / SRC.
_cp(r"\bmayday\b|бедств", "vhf:mayday")
_cp(r"pan[\s\-]*pan|срочн\w*", "vhf:panpan")
_cp(r"securite|securit|безопасн\w*\s+сообщ|навигац\w*\s+предупрежд", "vhf:securite")
_cp(r"channel\s*16|канал\w*\s*16|ch\s*16", "vhf:ch16")
_cp(r"channel\s*70|канал\w*\s*70|ch\s*70|dsc", "vhf:ch70-dsc")
_cp(r"\bmmsi\b", "vhf:mmsi")
_cp(r"\bover\b|\bout\b|\broger\b|процедурн\w*\s+слов", "vhf:procwords")

# Аварийные процедуры.
_cp(r"\bmob\b|человек\s+за\s+борт|за\s+борт", "safety:mob")
_cp(r"пожар|fire", "safety:fire")
_cp(r"течь|пробоин|seacock|поступлен\w*\s+вод", "safety:leak")
_cp(r"газ\w*\b|lpg|пропан", "safety:gas")
_cp(r"мел\w*|aground|grounding|посадк\w*\s+на\s+мел", "safety:aground")
_cp(r"harness|страхов\w*\s+привяз|leeway?\s*line|жилет|lifejacket", "safety:harness-pfd")

# Якорение / приливы.
_cp(r"\bscope\b|длин\w*\s+(?:цеп|канат).*глубин|отношен\w*.*глубин", "anchor:scope")
_cp(r"держ\w*\s+(?:ли\s+)?якор|anchor.*hold|dragg|ползёт\s+якор|задн\w*\s+ход.*пеленг", "anchor:check-holding")
_cp(r"swing\s+circle|радиус\w*\s+разворот|круг\w*\s+разворот", "anchor:swing-circle")
_cp(r"rule\s+of\s+twelfths|правил\w*\s+двенадцат", "tide:rule-of-twelfths")
_cp(r"spring\s+tide|сизигийн|neap|квадратурн", "tide:spring-neap")

# Метео.
_cp(r"холодн\w*\s+фронт|cold\s+front", "met:cold-front")
_cp(r"тёпл\w*\s+фронт|тепл\w*\s+фронт|warm\s+front", "met:warm-front")
_cp(r"бофорт|beaufort", "met:beaufort")
_cp(r"бриз|sea\s+breeze", "met:sea-breeze")
_cp(r"бойс\w*\s*-?\s*балло|buys\s*-?\s*ballot", "met:buys-ballot")
_cp(r"гист|gust|поры?в", "met:gusts-reefing")
_cp(r"бароме\w*|давлен\w*\s+пада", "met:falling-barometer")


# Термин в вопросе «Что такое X?» / «Что означает X?» — определяющий факт.
_DEFINE_Q = re.compile(
    r"что\s+так(?:ое|ой)\s+(.+?)\s*\??$|"
    r"что\s+означа\w+\s+(.+?)\s*\??$|"
    r"что\s+делает\s+(.+?)\s*\??$|"
    r"для\s+чего\s+(?:нужен|нужна|служит)\s+(.+?)\s*\??$",
    re.IGNORECASE | re.UNICODE,
)
# Латинский «термин» внутри (starboard, prop walk, scope, MMSI, EPIRB, leeway…).
_TERM_LATIN = re.compile(r"[a-z][a-z\s\-]{2,}", re.IGNORECASE)


def _defined_term(q: str) -> str | None:
    m = _DEFINE_Q.search(q.strip())
    if not m:
        return None
    term = next((g for g in m.groups() if g), "").strip()
    term = _PUNCT.sub(" ", term).lower()
    term = _WS.sub(" ", term).strip()
    # короткий, конкретный термин — иначе это не определение, а ситуация
    return term if 0 < len(term) <= 40 else None


def fact_signature(it: dict) -> str | None:
    """
    Канонический тег ФАКТА (а не темы), который проверяет вопрос.

    Приоритет:
      1) Если вопрос вида «Что такое <термин>?» — подпись = define:<термин>.
         (так «Что такое scope?» не смешивается с «какой scope рекомендуется?»)
      2) Числовые задачи навигации — подпись по набору чисел.
      3) Конвертация курса var/dev — подпись по числам и E/W.
      4) Иначе — связка распознанных морских концептов (огни/звуки/правила…).
         Берём не более 2 самых специфичных тегов, чтобы не склеивать разные факты.
    """
    q = it["q"]
    # 1) определение термина — самый надёжный признак смыслового дубля
    term = _defined_term(q)
    if term:
        return f"define:{term}"

    try:
        ans_text = it["options"][it["answer"]]
    except (IndexError, KeyError):
        ans_text = ""
    blob = f"{q} {ans_text}"

    # 2) навигационная задача S=D/T — по набору чисел.
    #    Единицы ловим с учётом русских словоформ (мил-и/ь, узл-ах/ов, час-а, мин-ут).
    if re.search(r"\d+(?:[.,]\d+)?\s*(?:nm|kt|мил\w*|узл\w*|час\w*|\bч\b|мин\w*)", q, re.IGNORECASE):
        nums = tuple(sorted(re.findall(r"\d+(?:[.,]\d+)?", q)))
        if nums:
            return "nav:calc:" + "-".join(nums)

    # 3) конвертация курса
    if re.search(r"\b(var|dev|variation|deviation|вариац|девиац|tc|mc|cc)\b", blob, re.IGNORECASE):
        nums = tuple(sorted(re.findall(r"\d{2,3}", blob)))
        if nums:
            return f"nav:compass:{'-'.join(nums)}"

    # 4) концепты — но только специфичные (light:/snd:/iala:/colreg:rule…),
    #    и максимум ДВА, чтобы не делать «корзину темы».
    SPECIFIC = ("light:", "snd:", "iala:", "colreg:rule", "anchor:", "tide:")
    tags = sorted(
        {tag for pat, tag in _CONCEPT_PATTERNS if pat.search(blob)
         and tag.startswith(SPECIFIC)}
    )
    if not tags:
        return None
    if len(tags) > 2:
        # слишком много концептов = это ситуационный вопрос, не простой дубль факта
        return None
    return "|".join(tags)


def find_semantic_dupes(unique: list[dict]):
    """Группирует вопросы с одинаковой сигнатурой факта (смысловые дубли)."""
    groups: dict[str, list[dict]] = {}
    for it in unique:
        sig = fact_signature(it)
        if sig:
            groups.setdefault(sig, []).append(it)
    # оставляем только группы из 2+ вопросов
    return {sig: g for sig, g in groups.items() if len(g) > 1}


# ──────────────────────────── Загрузка ────────────────────────────

def load_json_questions() -> list[dict]:
    if not QUESTIONS_FILE.exists():
        return []
    return json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))


def load_csv_questions(path: Path) -> list[dict]:
    out = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            q = (row.get("question") or "").strip()
            if not q:
                continue
            options = [(row.get(k) or "").strip() for k in ("A", "B", "C", "D")]
            options = [o for o in options if o]
            if len(options) < 2:
                continue
            ans = parse_answer(row.get("answer", ""), len(options))
            if ans is None or not (0 <= ans < len(options)):
                continue
            out.append({
                "topic": (row.get("topic") or "Прочее").strip(),
                "q": q,
                "options": options,
                "answer": ans,
                "expl": (row.get("explanation") or "").strip(),
                "study": (row.get("study_material") or "").strip(),
                "_src": path.name,
            })
    return out


def collect_all() -> list[dict]:
    items = []
    for jq in load_json_questions():
        items.append({
            "topic": jq.get("topic", "Прочее"),
            "q": jq.get("q", ""),
            "options": jq.get("options", []),
            "answer": jq.get("answer", 0),
            "expl": jq.get("expl", ""),
            "study": jq.get("study", ""),
            "_src": "questions.json",
        })
    if SOURCES_DIR.exists():
        for csv_path in sorted(SOURCES_DIR.glob("*.csv")):
            items.extend(load_csv_questions(csv_path))
    return items


# ──────────────────────────── Дедупликация ────────────────────────────

def dedup(items: list[dict]):
    """Возвращает (unique, exact_dupes, conflicts)."""
    seen: dict[str, dict] = {}
    exact_dupes = []
    conflicts = []

    for it in items:
        key = norm_key(it["q"])
        if key not in seen:
            seen[key] = it
            continue
        # дубль текста вопроса
        first = seen[key]
        # сравним правильный ответ по ТЕКСТУ варианта (индексы могут отличаться)
        try:
            ans_first = norm_key(first["options"][first["answer"]])
            ans_dup = norm_key(it["options"][it["answer"]])
        except (IndexError, KeyError):
            ans_first, ans_dup = "?", "??"
        if ans_first != ans_dup:
            conflicts.append((first, it))
        else:
            exact_dupes.append((first, it))
        # если у дубля есть study_material, а у первого нет — обогащаем
        if not first.get("study") and it.get("study"):
            first["study"] = it["study"]
        if not first.get("expl") and it.get("expl"):
            first["expl"] = it["expl"]

    return list(seen.values()), exact_dupes, conflicts


def find_near_dupes(unique: list[dict], threshold: float):
    """Группирует похожие (но не идентичные) вопросы внутри одной темы."""
    near = []
    by_topic: dict[str, list[dict]] = {}
    for it in unique:
        by_topic.setdefault(it["topic"], []).append(it)
    for topic, group in by_topic.items():
        keys = [(norm_key(it["q"]), it) for it in group]
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                k1, it1 = keys[i]
                k2, it2 = keys[j]
                if k1 == k2:
                    continue
                ratio = SequenceMatcher(None, k1, k2).ratio()
                if ratio >= threshold:
                    near.append((round(ratio, 3), topic, it1["q"], it2["q"]))
    near.sort(reverse=True)
    return near


def assign_ids(unique: list[dict]) -> None:
    counters: dict[str, int] = {}
    for it in unique:
        base = slug(it["topic"])
        counters[base] = counters.get(base, 0) + 1
        it["id"] = f"{base}-{counters[base]:03}"


# ──────────────────────────── main ────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--threshold", type=float, default=NEAR_DUP_THRESHOLD)
    ap.add_argument("--collapse-semantic", action="store_true",
                    help="Оставлять только ОДИН вопрос из каждой группы смысловых дублей "
                         "(лучший: с study_material/пояснением). По умолчанию — только отчёт.")
    args = ap.parse_args()

    items = collect_all()
    if not items:
        sys.exit("Нет данных. Положите CSV-файлы в папку sources/ и/или создайте questions.json.")

    unique, exact_dupes, conflicts = dedup(items)
    near = find_near_dupes(unique, args.threshold)
    semantic = find_semantic_dupes(unique)

    collapsed_count = 0
    if args.collapse_semantic and semantic:
        drop_ids = set()
        for sig, group in semantic.items():
            # лучший = у кого есть study, затем expl, затем самый длинный вопрос
            best = max(group, key=lambda x: (bool(x.get("study")), bool(x.get("expl")), len(x["q"])))
            for it in group:
                if it is not best:
                    drop_ids.add(id(it))
        unique = [it for it in unique if id(it) not in drop_ids]
        collapsed_count = len(drop_ids)
        # пересчитать группы для отчёта уже не нужно — отчёт покажет, что было свёрнуто

    assign_ids(unique)

    # ── Отчёт ──
    lines = []
    lines.append("=" * 70)
    lines.append("ОТЧЁТ ОБ ОБЪЕДИНЕНИИ И ДЕДУПЛИКАЦИИ БАЗ ВОПРОСОВ")
    lines.append("=" * 70)
    from collections import Counter
    src_counts = Counter(it["_src"] for it in items)
    lines.append("\nИсточники (всего строк прочитано):")
    for src, n in src_counts.most_common():
        lines.append(f"  {n:4}  {src}")
    lines.append(f"\nВсего прочитано:        {len(items)}")
    lines.append(f"Точных дублей удалено:  {len(exact_dupes)}")
    lines.append(f"Конфликтов (вопрос=, ответ≠): {len(conflicts)}")
    lines.append(f"Групп смысловых дублей: {len(semantic)}")
    if args.collapse_semantic:
        lines.append(f"Смысловых дублей свёрнуто: {collapsed_count}")
    lines.append(f"Уникальных вопросов:    {len(unique)}")

    lines.append("\nРаспределение по темам (после дедупа):")
    for t, n in Counter(it["topic"] for it in unique).most_common():
        lines.append(f"  {n:4}  {t}")

    if conflicts:
        lines.append("\n" + "-" * 70)
        lines.append("⚠️  КОНФЛИКТЫ — одинаковый вопрос, РАЗНЫЙ правильный ответ")
        lines.append("    (нужна ручная проверка — оставлен первый вариант):")
        for a, b in conflicts:
            lines.append(f"\n  Q: {a['q']}")
            lines.append(f"     [{a['_src']}] ответ: {a['options'][a['answer']]}")
            lines.append(f"     [{b['_src']}] ответ: {b['options'][b['answer']]}")

    if near:
        lines.append("\n" + "-" * 70)
        lines.append(f"БЛИЗКИЕ ВОПРОСЫ ПО ТЕКСТУ (схожесть ≥ {args.threshold}) — кандидаты на ручную чистку:")
        for ratio, topic, q1, q2 in near[:200]:
            lines.append(f"\n  [{ratio}] {topic}")
            lines.append(f"    1) {q1}")
            lines.append(f"    2) {q2}")

    if semantic:
        lines.append("\n" + "=" * 70)
        lines.append("СМЫСЛОВЫЕ ДУБЛИ — один и тот же факт, разная формулировка")
        lines.append("(сгруппированы по 'подписи факта'; решите, сколько оставить)")
        if args.collapse_semantic:
            lines.append("Режим --collapse-semantic: из каждой группы оставлен ОДИН лучший вопрос.")
        lines.append("=" * 70)
        # сортируем: самые большие группы вверху
        for sig, group in sorted(semantic.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"\n▸ факт [{sig}]  — {len(group)} вопрос(ов):")
            for it in group:
                star = " ★study" if it.get("study") else ""
                lines.append(f"    • ({it['_src']}{star}) {it['q']}")

    report = "\n".join(lines)
    REPORT_FILE.write_text(report, encoding="utf-8")
    # Console may be cp1251 on Windows — print encoding-safely.
    _enc = (sys.stdout.encoding or "utf-8")
    sys.stdout.buffer.write(report[:3000].encode(_enc, errors="replace"))
    sys.stdout.buffer.write(f"\n\n…полный отчёт: {REPORT_FILE}\n".encode(_enc, errors="replace"))

    if args.dry_run:
        print("\n[dry-run] questions.json НЕ изменён.")
        return

    out = [{
        "id": it["id"],
        "topic": it["topic"],
        "q": it["q"],
        "options": it["options"],
        "answer": it["answer"],
        "expl": it["expl"],
        **({"study": it["study"]} if it.get("study") else {}),
    } for it in unique]
    QUESTIONS_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Записано {len(out)} вопросов в {QUESTIONS_FILE}")


if __name__ == "__main__":
    main()
