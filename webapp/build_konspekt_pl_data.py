"""
Экспорт польского конспекта (Żeglarz + Sternik) в статический JS для Mini App.

konspekt_pl.py (KONSPEKT_PL / KONSPEKT_PL_ORDER)  ->  webapp/konspekt_pl_data.js

Mini App — статическая страница, поэтому темы вшиваем в файл. После любого
изменения конспекта перегенерировать:

    python webapp/build_konspekt_pl_data.py

Для каждой темы кладём:
  key, title (заголовок-кнопка), heading (первый <b>…</b>),
  html (текст темы как есть), text (без тегов — для поиска).

Дополнительно строим q2topic — карту «id вопроса -> ключ темы конспекта».
Источник карты — сами теги вида (zj-001) / (st-234) внутри текста темы: если
факт про вопрос лежит в теме X, то «лампочка-источник» этого вопроса ведёт в X.
Так exam_pl.html может у любого вопроса дать ссылку на разбор в конспекте.
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # каталог bot/
OUT = Path(__file__).resolve().parent / "konspekt_pl_data.js"

import sys
sys.path.insert(0, str(BASE))
import konspekt_pl  # noqa: E402

TAG_RE = re.compile(r"<[^>]+>")
ID_RE = re.compile(r"(?:zj|st)-\d{3}")


def strip_tags(html: str) -> str:
    txt = TAG_RE.sub(" ", html)
    txt = (txt.replace("&lt;", "<").replace("&gt;", ">")
              .replace("&amp;", "&").replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", txt).strip()


def first_heading(html: str) -> str:
    m = re.search(r"<b>(.*?)</b>", html, re.S)
    return strip_tags(m.group(1)) if m else ""


def main() -> None:
    order = list(getattr(konspekt_pl, "KONSPEKT_PL_ORDER", konspekt_pl.KONSPEKT_PL))
    topics = []
    q2topic = {}
    for key in order:
        title, html = konspekt_pl.KONSPEKT_PL[key]
        topics.append({
            "key": key,
            "title": title,
            "heading": first_heading(html),
            "html": html,
            "text": strip_tags(html),
        })
        # карта id -> первая тема, где он процитирован (по порядку тем)
        for qid in ID_RE.findall(html):
            q2topic.setdefault(qid, key)

    payload = {
        "version": 1,
        # обе лицензии живут в одном конспекте, темы общие
        "sections": [{"name": "Темы", "keys": order}],
        "topics": topics,
        "q2topic": q2topic,
    }
    js = (
        "// АВТОГЕНЕРАЦИЯ — не редактировать вручную.\n"
        "// Источник: konspekt_pl.py. Перегенерация: "
        "python webapp/build_konspekt_pl_data.py\n"
        "window.KONSPEKT_PL_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    OUT.write_text(js, encoding="utf-8")
    print(f"OK: {len(topics)} тем, {len(q2topic)} привязок вопросов "
          f"-> {OUT.name} ({OUT.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    main()
