# -*- coding: utf-8 -*-
"""Нейроозвучка для аудио-повторения (audio.html).

Генерирует MP3-файлы для всех фраз плеера нейроголосом Microsoft
(edge-tts, бесплатно) и манифест tts_index.js (ключ фразы -> имя файла).

Фразы:
  q:<id>   — текст вопроса ISSA
  o:<id>   — «Варианты. А. ... Б. ...» (режим «с вариантами»)
  a:<id>   — «Правильный ответ: ...»
  t:<term> — термин словаря
  d:<term> — определение термина

Имя файла = sha1(голос|текст)[:16].mp3 — при изменении текста вопроса
файл перегенерируется сам, неизменённые берутся из кэша. Файлы, на
которые манифест больше не ссылается, удаляются (prune).

Запуск:
  python webapp/build_audio_tts.py --cache /opt/issa-bot/tts_cache
  python webapp/build_audio_tts.py --cache webapp/tts --limit 12   # локальная проба

Требует: pip install edge-tts (и сеть до серверов Microsoft).
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import sys

VOICE = "ru-RU-DmitryNeural"     # альтернатива: ru-RU-SvetlanaNeural
CONCURRENCY = 6
RETRIES = 3
LETTERS = ["А", "Б", "В", "Г", "Д"]

HERE = os.path.dirname(os.path.abspath(__file__))


def load_data_js(path):
    """window.X = {...json...} -> dict."""
    with open(path, encoding="utf-8") as f:
        s = f.read()
    m = re.search(r"=\s*(\{.*\});?\s*$", s, re.S)
    return json.loads(m.group(1))


def collect_phrases():
    """Все фразы плеера: [(key, text)]."""
    quiz = load_data_js(os.path.join(HERE, "quiz_data.js"))
    gloss = load_data_js(os.path.join(HERE, "glossary_data.js"))
    phrases = []
    for q in quiz["questions"]:
        qid = q["id"]
        phrases.append(("q:" + qid, q["q"]))
        opts = ". ".join(LETTERS[i] + ". " + o for i, o in enumerate(q["options"]))
        phrases.append(("o:" + qid, "Варианты. " + opts))
        phrases.append(("a:" + qid, "Правильный ответ: " + q["options"][q["answer"]]))
    for cat in gloss["categories"]:
        for t in cat["terms"]:
            phrases.append(("t:" + t["term"], t["term"]))
            phrases.append(("d:" + t["term"], t["definition"]))
    return phrases


def fname_for(text):
    h = hashlib.sha1((VOICE + "|" + text).encode("utf-8")).hexdigest()[:16]
    return h + ".mp3"


async def synth_one(sem, text, path):
    import edge_tts
    async with sem:
        for attempt in range(RETRIES):
            try:
                await edge_tts.Communicate(text, VOICE).save(path)
                if os.path.getsize(path) > 500:      # пустышки не считаем успехом
                    return True
                os.remove(path)
            except Exception:
                if os.path.exists(path):
                    try: os.remove(path)
                    except OSError: pass
                await asyncio.sleep(1.5 * (attempt + 1))
    return False


async def main_async(args):
    phrases = collect_phrases()
    if args.limit:
        phrases = phrases[: args.limit]
    os.makedirs(args.cache, exist_ok=True)

    manifest = {}
    todo = []
    for key, text in phrases:
        fn = fname_for(text)
        manifest[key] = fn
        path = os.path.join(args.cache, fn)
        if not (os.path.exists(path) and os.path.getsize(path) > 500):
            todo.append((key, text, path))

    print(f"фраз: {len(phrases)}, в кэше: {len(phrases) - len(todo)}, генерировать: {len(todo)}")
    failed = 0
    if todo:
        sem = asyncio.Semaphore(CONCURRENCY)
        tasks = [synth_one(sem, text, path) for _, text, path in todo]
        done_n = 0
        for i in range(0, len(tasks), 50):
            chunk = tasks[i:i + 50]
            results = await asyncio.gather(*chunk)
            failed += sum(1 for r in results if not r)
            done_n += len(chunk)
            print(f"  {done_n}/{len(todo)} (ошибок: {failed})", flush=True)

    # фразы без файла выкидываем из манифеста — плеер уйдёт в фолбэк на синтез
    ok_manifest = {k: v for k, v in manifest.items()
                   if os.path.exists(os.path.join(args.cache, v))}

    # prune: файлы, на которые никто не ссылается
    referenced = set(ok_manifest.values())
    pruned = 0
    for f in os.listdir(args.cache):
        if f.endswith(".mp3") and f not in referenced:
            os.remove(os.path.join(args.cache, f))
            pruned += 1

    index_path = os.path.join(HERE, "tts_index.js")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("// АВТОГЕНЕРАЦИЯ — не редактировать. Источник: build_audio_tts.py\n")
        f.write("window.TTS_INDEX = ")
        json.dump({"voice": VOICE, "files": ok_manifest}, f, ensure_ascii=False,
                  separators=(",", ":"))
        f.write(";\n")

    size_mb = sum(os.path.getsize(os.path.join(args.cache, f))
                  for f in os.listdir(args.cache) if f.endswith(".mp3")) / 1e6
    print(f"готово: {len(ok_manifest)}/{len(phrases)} фраз, кэш {size_mb:.0f} МБ, "
          f"удалено устаревших: {pruned}, манифест: {index_path}")
    # генерация неполна — не валим деплой, но сигналим кодом 2
    return 0 if not failed else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True, help="каталог с mp3 (кэш между запусками)")
    ap.add_argument("--limit", type=int, default=0, help="только первые N фраз (проба)")
    args = ap.parse_args()
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("edge-tts не установлен (pip install edge-tts) — пропускаю генерацию")
        return 3
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
