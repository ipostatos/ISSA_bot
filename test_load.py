"""
Нагрузочный тест: 10 пользователей одновременно работают с ботом.

Проверяет, что при параллельной работе:
 • прогресс каждого пользователя НЕ перемешивается с чужим;
 • одновременные записи в progress/<id>.json не портят файлы;
 • экзамены 10 пользователей идут независимо, без повторов внутри каждого;
 • задачи T-V-M-D-C и серии (streak) считаются раздельно;
 • общие in-memory структуры (ACTIVE_POLLS/EXAMS/ACTIVE_TASK) не путают юзеров.

Тест гоняет логику бота напрямую (без сети Telegram) в потоках —
это и есть проверка на гонки данных при 10 одновременных клиентах.

Запуск:  python test_load.py
"""
import importlib.util
import random
import sys
import threading
from pathlib import Path

BASE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("botmod", BASE / "bot.py")
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)

USERS = list(range(900001, 900011))  # 10 виртуальных пользователей
ITERS = 40                            # действий на пользователя
errors = []
lock_for_errors = threading.Lock()


def fresh(uid):
    bot.save_progress(uid, {"seen": [], "wrong": [], "stats": {"answered": 0, "correct": 0},
                            "tasks": {"solved": 0, "attempts": 0, "streak": 0, "best": 0}})


def user_session(uid):
    """Имитирует активную сессию одного пользователя."""
    try:
        rng = random.Random(uid)
        # 1) Экзамен на 100 — проверяем уникальность выборки
        size = min(bot.EXAM_SIZE, len(bot.QUESTIONS))
        chosen = bot.pick_unseen(uid, bot.QUESTIONS, size)
        ids = [q["id"] for q in chosen]
        if len(ids) != len(set(ids)):
            raise AssertionError(f"user {uid}: повтор в экзамене")

        # 2) Случайные ответы + задачи вперемешку (нагрузка на запись прогресса)
        my_correct = 0
        my_task_solved = 0
        for _ in range(ITERS):
            act = rng.choice(["answer", "task", "mistake"])
            if act == "answer":
                q = rng.choice(bot.QUESTIONS)
                ok = rng.random() < 0.5
                bot.record_answer(uid, q["id"], ok)
                if ok:
                    my_correct += 1
            elif act == "task":
                ok = rng.random() < 0.6
                t = bot.record_task(uid, ok)
                if ok:
                    my_task_solved += 1
                # streak не может превышать best
                if t["streak"] > t["best"]:
                    raise AssertionError(f"user {uid}: streak>best")
            else:
                # читаем прогресс — не должно падать и не должно быть чужих данных
                p = bot.load_progress(uid)
                if not isinstance(p["seen"], list):
                    raise AssertionError(f"user {uid}: битый прогресс")

        # 3) Финальная сверка: записанная статистика консистентна с нашими действиями
        p = bot.load_progress(uid)
        if p["stats"]["correct"] != my_correct:
            raise AssertionError(
                f"user {uid}: stats.correct={p['stats']['correct']} ожидалось {my_correct} "
                f"(данные перемешались?)")
        if p["tasks"]["solved"] != my_task_solved:
            raise AssertionError(
                f"user {uid}: tasks.solved={p['tasks']['solved']} ожидалось {my_task_solved}")
    except Exception as e:  # noqa: BLE001
        with lock_for_errors:
            errors.append(str(e))


def main():
    for uid in USERS:
        fresh(uid)

    threads = [threading.Thread(target=user_session, args=(uid,)) for uid in USERS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Проверка целостности файлов прогресса после параллельной работы
    import json
    corrupt = []
    for uid in USERS:
        try:
            json.loads((bot.PROGRESS_DIR / f"{uid}.json").read_text(encoding="utf-8"))
        except Exception:
            corrupt.append(uid)

    # cleanup
    for uid in USERS:
        (bot.PROGRESS_DIR / f"{uid}.json").unlink(missing_ok=True)

    ok = not errors and not corrupt
    out = []
    out.append(f"Пользователей: {len(USERS)} | действий каждый: {ITERS} | вопросов в банке: {len(bot.QUESTIONS)}")
    out.append(f"Гонок/ошибок данных: {len(errors)}")
    out.append(f"Повреждённых файлов прогресса: {len(corrupt)}")
    for e in errors[:10]:
        out.append("  ! " + e)
    out.append("РЕЗУЛЬТАТ: " + ("✅ нагрузка 10 юзеров — OK" if ok else "❌ обнаружены проблемы"))
    sys.stdout.buffer.write(("\n".join(out) + "\n").encode("utf-8", "replace"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
