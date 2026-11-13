"""
Регрессия мелочей бота из аудита (волна E, 13.11.2026).

Telegram не нужен: колбэки и сообщения — заглушки, файлы состояния бота —
во временном каталоге.

Запуск:  python test_bot_hardening.py
"""
import asyncio
import importlib.util
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

fails = 0


def ok(cond, name):
    global fails
    print(("  OK   " if cond else "  FAIL ") + name)
    if not cond:
        fails += 1


spec = importlib.util.spec_from_file_location("botmod", BASE / "bot.py")
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)
_tmp = tempfile.TemporaryDirectory()
bot.PROGRESS_DIR = Path(_tmp.name) / "progress"
bot.PROGRESS_DIR.mkdir()


class FakeMsg:
    def __init__(self):
        self.sent = []
        self.chat = type("C", (), {"id": 1})()

    async def answer(self, text, **kw):
        self.sent.append(text)


class FakeCb:
    def __init__(self, data):
        self.data = data
        self.from_user = type("U", (), {"id": 4242})()
        self.message = FakeMsg()
        self.answered = []
        self.bot = None

    async def answer(self, text=None, **kw):
        self.answered.append(text)


# 1. Подделанный callback_data не роняет хендлеры (раньше — вечный спиннер)
for handler, data in ((bot.cb_glossary_term, "gl:t:нет-двоеточия"),
                      (bot.cb_glossary_term, "gl:t:"),
                      (bot.cb_calc_dir, "calc:dir:T"),
                      (bot.cb_calc_dir, "calc:dir:"),
                      (bot.cb_calc_dir, "calc:dir:TCX")):
    cb = FakeCb(data)
    try:
        asyncio.run(handler(cb))
        ok(len(cb.answered) == 1, f"{handler.__name__}({data!r}) — не падает и гасит спиннер")
    except Exception as e:  # noqa: BLE001
        ok(False, f"{handler.__name__}({data!r}) — упал: {type(e).__name__}: {e}")

# 2. Последний рубеж: исключение в хендлере → спиннер погашен, ошибка залогирована
cb = FakeCb("x")
update = type("Up", (), {"callback_query": cb})()
event = type("Ev", (), {"exception": RuntimeError("boom"), "update": update})()
handled = asyncio.run(bot.on_handler_error(event))
ok(handled is True and len(cb.answered) == 1, "errors-хендлер гасит спиннер и помечает ошибку обработанной")

# 3. Разбор ошибок экранирует HTML (бот шлёт parse_mode=HTML)
line = bot.review_line({"topic": "A<b>", "q": "x < y & z?", "options": ["<ok>", "n"], "answer": 0})
ok("<b>" not in line and "&lt;b&gt;" in line and "&amp;" in line and "&lt;ok&gt;" in line,
   "review_line экранирует тему, вопрос и ответ")
amp = [q for q in bot.QUESTIONS if any(c in q["q"] + "".join(q["options"]) + q["topic"] for c in "<>&")]
ok(all("<" not in bot.review_line(q).replace("<b>", "") for q in amp),
   f"вопросы банка с <>& дают безопасный разбор ({', '.join(q['id'] for q in amp) or 'нет'})")

# 4. Морской калькулятор: сверхдлинное число → понятная ошибка, а не OverflowError
crashes = []
for kind in bot.MARINE_KINDS:
    for text in ("9" * 400 + " 5", "5 " + "9" * 400, "5 2000000"):
        try:
            bot.compute_marine(kind, text)
        except ValueError:
            pass
        except Exception as e:  # noqa: BLE001
            crashes.append(f"{kind}:{type(e).__name__}")
ok(not crashes, f"compute_marine: огромные числа → ValueError ({crashes or 'падений нет'})")
ok("2.4" in bot.compute_marine("t", "5.5 13.2"), "compute_marine: обычный расчёт не сломан")

print()
if fails:
    print(f"ПРОВАЛЕНО: {fails}")
    sys.exit(1)
print("OK: bot hardening tests passed")
