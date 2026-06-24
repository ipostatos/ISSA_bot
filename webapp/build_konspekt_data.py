"""
Экспорт конспекта в статический JS для Mini App «Конспект».

content.py (KONSPEKT/KONSPEKT_BTN/KONSPEKT_IMAGES)  ->  webapp/konspekt_data.js

Mini App — статическая страница, поэтому темы вшиваем в файл. После любого
изменения конспекта перегенерировать:

    python webapp/build_konspekt_data.py

Для каждой темы кладём:
  key, title (короткая кнопка), heading (первый <b>…</b> — заголовок темы),
  html (текст темы как есть — теги <b>/<i>/<code> отрисуются и в вебе),
  text (без тегов — для поиска), images (имена файлов в /images/).
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # каталог bot/
OUT = Path(__file__).resolve().parent / "konspekt_data.js"

import sys
sys.path.insert(0, str(BASE))
import content  # noqa: E402

TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(html: str) -> str:
    txt = TAG_RE.sub(" ", html)
    txt = (txt.replace("&lt;", "<").replace("&gt;", ">")
              .replace("&amp;", "&").replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", txt).strip()


def first_heading(html: str) -> str:
    m = re.search(r"<b>(.*?)</b>", html, re.S)
    return strip_tags(m.group(1)) if m else ""


def main() -> None:
    topics = []
    for key, (title, html) in content.KONSPEKT.items():
        topics.append({
            "key": key,
            "title": content.KONSPEKT_BTN.get(key, title),
            "heading": first_heading(html),
            "html": html,
            "text": strip_tags(html),
            "images": content.KONSPEKT_IMAGES.get(key, []),
        })
    payload = {"version": 1, "topics": topics}
    js = (
        "// АВТОГЕНЕРАЦИЯ — не редактировать вручную.\n"
        "// Источник: content.py (KONSPEKT). Перегенерация: "
        "python webapp/build_konspekt_data.py\n"
        "window.KONSPEKT_DATA = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    OUT.write_text(js, encoding="utf-8")
    print(f"OK: {len(topics)} тем -> {OUT.name} ({OUT.stat().st_size // 1024} КБ)")


if __name__ == "__main__":
    main()
