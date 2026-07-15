# -*- coding: utf-8 -*-
"""
Мультиязычный словарь интерфейса ISSA Trainer (бот) — RU / PL / UA / EN.

Только UI-строки («хром»): кнопки, меню, подписи, подсказки, вердикты,
сообщения об ошибках. Учебный КОНТЕНТ (вопросы, конспект, шпаргалки, словарь,
тексты задач, решения) не переводится и остаётся на русском — он приходит из
data-модулей (questions.json, content.py, glossary.py, marine.py, nav_tasks.py,
tides.py, calc.py).

Терминология и тон согласованы с веб-приложением (webapp/i18n.dict.js).
Код языка для украинского — "ua" (как в webapp), НЕ "uk".

Использование:
    from bot_i18n import t, norm_lang, LANG_LABELS, SUPPORTED
    t("disclaimer", "pl")
    t("stats", lang, answered=10, correct=8, pct=80, wrong_n=2, seen_n=50, total=300)
"""

SUPPORTED = ("ru", "pl", "ua", "en")

LANG_LABELS = {
    "ru": "🇷🇺 Русский",
    "pl": "🇵🇱 Polski",
    "ua": "🇺🇦 Українська",
    "en": "🇬🇧 English",
}


def norm_lang(code) -> str:
    """Telegram language_code (может быть None) → один из SUPPORTED.

    Смотрим первые 2 символа: ru→ru, pl→pl, uk→ua, en→en; всё прочее → ru.
    """
    if not code:
        return "ru"
    two = str(code)[:2].lower()
    return {"ru": "ru", "pl": "pl", "uk": "ua", "en": "en"}.get(two, "ru")


def t(key: str, lang: str = "ru", **kw) -> str:
    """Вернуть перевод key на lang (fallback на ru), подставив kw через .format."""
    entry = TR[key]  # KeyError, если ключ забыт — пусть всплывёт в тестах
    s = entry.get(lang) or entry["ru"]
    return s.format(**kw) if kw else s


TR = {
    # ─────────────── общее / кнопки навигации ───────────────
    "back": {"ru": "⬅️ Назад", "pl": "⬅️ Wstecz", "ua": "⬅️ Назад", "en": "⬅️ Back"},
    "back_menu": {"ru": "⬅️ В меню", "pl": "⬅️ Do menu", "ua": "⬅️ У меню", "en": "⬅️ To menu"},
    "back_sections": {"ru": "⬅️ Разделы", "pl": "⬅️ Sekcje", "ua": "⬅️ Розділи", "en": "⬅️ Sections"},
    "more_details": {"ru": "📖 Подробнее", "pl": "📖 Szczegóły", "ua": "📖 Детальніше", "en": "📖 Details"},

    "disclaimer": {
        "ru": ("ℹ️ <i>Бот и база вопросов — оригинальные, созданы для тренировки. "
               "Они <b>не содержат экзаменационных ключей</b> и <b>не являются официальным "
               "материалом ISSA</b> или какой-либо школы. Это вспомогательный учебный "
               "материал для самоподготовки.</i>"),
        "pl": ("ℹ️ <i>Bot i baza pytań są autorskie, stworzone do treningu. "
               "<b>Nie zawierają kluczy egzaminacyjnych</b> i <b>nie są oficjalnym "
               "materiałem ISSA</b> ani żadnej szkoły. To pomocniczy materiał edukacyjny "
               "do samodzielnej nauki.</i>"),
        "ua": ("ℹ️ <i>Бот і база питань — оригінальні, створені для тренування. "
               "Вони <b>не містять екзаменаційних ключів</b> і <b>не є офіційним "
               "матеріалом ISSA</b> чи будь-якої школи. Це допоміжний навчальний "
               "матеріал для самопідготовки.</i>"),
        "en": ("ℹ️ <i>The bot and question bank are original, built for practice. "
               "They <b>contain no exam answer keys</b> and are <b>not official ISSA "
               "material</b> or that of any school. This is a supporting study aid "
               "for self-preparation.</i>"),
    },

    # ─────────────── группы ───────────────
    "group_redirect": {
        "ru": "👋 Я тренажёр для самоподготовки. Открой меня в личном чате: @{username} → /start",
        "pl": "👋 Jestem trenerem do samodzielnej nauki. Otwórz mnie na czacie prywatnym: @{username} → /start",
        "ua": "👋 Я тренажер для самопідготовки. Відкрий мене в приватному чаті: @{username} → /start",
        "en": "👋 I'm a self-study trainer. Open me in a private chat: @{username} → /start",
    },
    "group_cb_redirect": {
        "ru": "Открой бота в личном чате 🙂",
        "pl": "Otwórz bota na czacie prywatnym 🙂",
        "ua": "Відкрий бота в приватному чаті 🙂",
        "en": "Open the bot in a private chat 🙂",
    },

    # ─────────────── главное меню (fallback без Mini App) ───────────────
    "mm_open_trainer": {"ru": "🚀 Открыть тренажёр", "pl": "🚀 Otwórz trener", "ua": "🚀 Відкрити тренажер", "en": "🚀 Open trainer"},
    "mm_pl_licenses": {
        "ru": "🇵🇱 Польские лицензии (Żeglarz / Sternik)",
        "pl": "🇵🇱 Polskie licencje (Żeglarz / Sternik)",
        "ua": "🇵🇱 Польські ліцензії (Żeglarz / Sternik)",
        "en": "🇵🇱 Polish licenses (Żeglarz / Sternik)",
    },
    "mm_random": {"ru": "🎯 Случайный вопрос", "pl": "🎯 Losowe pytanie", "ua": "🎯 Випадкове питання", "en": "🎯 Random question"},
    "mm_topics": {"ru": "📚 Тренировка по темам", "pl": "📚 Trening tematyczny", "ua": "📚 Тренування за темами", "en": "📚 Practice by topic"},
    "mm_exam": {"ru": "📝 Экзамен ({n} вопросов)", "pl": "📝 Egzamin ({n} pytań)", "ua": "📝 Екзамен ({n} питань)", "en": "📝 Exam ({n} questions)"},
    "mm_mistakes": {"ru": "🔁 Работа над ошибками", "pl": "🔁 Praca nad błędami", "ua": "🔁 Робота над помилками", "en": "🔁 Mistakes practice"},
    "mm_tasks": {"ru": "🧭 Решение задач (T-V-M-D-C)", "pl": "🧭 Zadania (T-V-M-D-C)", "ua": "🧭 Розв'язання задач (T-V-M-D-C)", "en": "🧭 Problems (T-V-M-D-C)"},
    "mm_calc": {"ru": "🧮 Морской калькулятор", "pl": "🧮 Kalkulator morski", "ua": "🧮 Морський калькулятор", "en": "🧮 Marine calculator"},
    "mm_ptasks": {"ru": "📝 Практические задачи", "pl": "📝 Zadania praktyczne", "ua": "📝 Практичні задачі", "en": "📝 Practical problems"},
    "mm_konspekt": {"ru": "📖 Конспект", "pl": "📖 Notatki", "ua": "📖 Конспект", "en": "📖 Notes"},
    "mm_cheat": {"ru": "📌 Шпаргалки", "pl": "📌 Ściągi", "ua": "📌 Шпаргалки", "en": "📌 Cheat sheets"},
    "mm_glossary": {"ru": "📚 Словарь яхтсмена", "pl": "📚 Słownik żeglarski", "ua": "📚 Словник яхтсмена", "en": "📚 Sailor's glossary"},
    "mm_stats": {"ru": "📊 Моя статистика", "pl": "📊 Moje statystyki", "ua": "📊 Моя статистика", "en": "📊 My stats"},
    "mm_reset": {"ru": "♻️ Сбросить прогресс", "pl": "♻️ Zresetuj postęp", "ua": "♻️ Скинути прогрес", "en": "♻️ Reset progress"},

    # ─────────────── reply-клавиатура «Тесты» ───────────────
    "quiz_reply_btn": {"ru": "🎓 Тесты (приложение)", "pl": "🎓 Testy (aplikacja)", "ua": "🎓 Тести (застосунок)", "en": "🎓 Tests (app)"},
    "quiz_placeholder": {"ru": "Меню — /menu", "pl": "Menu — /menu", "ua": "Меню — /menu", "en": "Menu — /menu"},

    # ─────────────── темы ───────────────
    "choose_topic": {"ru": "Выбери тему:", "pl": "Wybierz temat:", "ua": "Обери тему:", "en": "Pick a topic:"},
    "topic_empty": {"ru": "В этой теме вопросов нет.", "pl": "W tym temacie nie ma pytań.", "ua": "У цій темі питань немає.", "en": "No questions in this topic."},
    "topic_remaining": {
        "ru": "Тема «{topic}». Осталось новых: <b>{left}</b>",
        "pl": "Temat „{topic}”. Nowych zostało: <b>{left}</b>",
        "ua": "Тема «{topic}». Залишилось нових: <b>{left}</b>",
        "en": "Topic “{topic}”. New left: <b>{left}</b>",
    },

    # ─────────────── next-question клавиатуры ───────────────
    "next_question": {"ru": "➡️ Следующий вопрос", "pl": "➡️ Następne pytanie", "ua": "➡️ Наступне питання", "en": "➡️ Next question"},
    "next_topic": {"ru": "➡️ Ещё по этой теме", "pl": "➡️ Więcej z tego tematu", "ua": "➡️ Ще з цієї теми", "en": "➡️ More on this topic"},
    "next_mistake": {"ru": "🔁 Следующая ошибка", "pl": "🔁 Następny błąd", "ua": "🔁 Наступна помилка", "en": "🔁 Next mistake"},

    # ─────────────── случайный вопрос ───────────────
    "no_questions_left": {"ru": "Вопросы закончились 🤷", "pl": "Pytania się skończyły 🤷", "ua": "Питання закінчились 🤷", "en": "No more questions 🤷"},
    "remaining_in_circle": {
        "ru": "Осталось новых вопросов в круге: <b>{left}</b>",
        "pl": "Nowych pytań w rundzie zostało: <b>{left}</b>",
        "ua": "Залишилось нових питань у колі: <b>{left}</b>",
        "en": "New questions left this round: <b>{left}</b>",
    },

    # ─────────────── работа над ошибками ───────────────
    "mistakes_none": {
        "ru": "🎉 У тебя нет вопросов на повтор — ошибок не накоплено!",
        "pl": "🎉 Nie masz pytań do powtórki — brak nagromadzonych błędów!",
        "ua": "🎉 У тебе немає питань на повтор — помилок не накопичено!",
        "en": "🎉 You have no questions to review — no mistakes piled up!",
    },
    "mistakes_remaining": {
        "ru": "Вопросов на повтор осталось: <b>{n}</b>",
        "pl": "Pytań do powtórki zostało: <b>{n}</b>",
        "ua": "Питань на повтор залишилось: <b>{n}</b>",
        "en": "Questions to review left: <b>{n}</b>",
    },

    # ─────────────── study / подробнее ───────────────
    "no_details": {"ru": "Подробностей нет", "pl": "Brak szczegółów", "ua": "Подробиць немає", "en": "No details"},
    "study_more": {
        "ru": "📖 <b>Подробнее</b>\n\n{study}",
        "pl": "📖 <b>Szczegóły</b>\n\n{study}",
        "ua": "📖 <b>Детальніше</b>\n\n{study}",
        "en": "📖 <b>Details</b>\n\n{study}",
    },

    # ─────────────── сброс прогресса ───────────────
    "reset_confirm_btn": {
        "ru": "⚠️ Да, стереть весь прогресс",
        "pl": "⚠️ Tak, usuń cały postęp",
        "ua": "⚠️ Так, стерти весь прогрес",
        "en": "⚠️ Yes, erase all progress",
    },
    "cancel": {"ru": "Отмена", "pl": "Anuluj", "ua": "Скасувати", "en": "Cancel"},
    "reset_prompt": {
        "ru": ("♻️ <b>Сбросить прогресс?</b>\n\n"
               "Будут стёрты пройденные вопросы, работа над ошибками и статистика. "
               "Это действие необратимо."),
        "pl": ("♻️ <b>Zresetować postęp?</b>\n\n"
               "Usunięte zostaną przerobione pytania, praca nad błędami i statystyki. "
               "Ta operacja jest nieodwracalna."),
        "ua": ("♻️ <b>Скинути прогрес?</b>\n\n"
               "Будуть стерті пройдені питання, робота над помилками та статистика. "
               "Ця дія незворотна."),
        "en": ("♻️ <b>Reset progress?</b>\n\n"
               "Your answered questions, mistakes practice and stats will be erased. "
               "This action is irreversible."),
    },
    "reset_done": {"ru": "♻️ Прогресс сброшен.", "pl": "♻️ Postęp zresetowany.", "ua": "♻️ Прогрес скинуто.", "en": "♻️ Progress reset."},

    # ─────────────── экзамен ───────────────
    "exam_passed": {"ru": "✅ <b>СДАНО</b>", "pl": "✅ <b>ZDANE</b>", "ua": "✅ <b>СКЛАДЕНО</b>", "en": "✅ <b>PASSED</b>"},
    "exam_failed": {"ru": "❌ <b>НЕ СДАНО</b>", "pl": "❌ <b>NIEZDANE</b>", "ua": "❌ <b>НЕ СКЛАДЕНО</b>", "en": "❌ <b>FAILED</b>"},
    "exam_started": {
        "ru": ("📝 <b>Экзамен начат</b>\n"
               "Вопросов: {n} · Проходной балл: {pass}%\n"
               "Отвечай на каждый вопрос — в конце будет результат и разбор ошибок."),
        "pl": ("📝 <b>Egzamin rozpoczęty</b>\n"
               "Pytań: {n} · Próg zaliczenia: {pass}%\n"
               "Odpowiadaj na każde pytanie — na końcu będzie wynik i analiza błędów."),
        "ua": ("📝 <b>Екзамен розпочато</b>\n"
               "Питань: {n} · Прохідний бал: {pass}%\n"
               "Відповідай на кожне питання — наприкінці буде результат і розбір помилок."),
        "en": ("📝 <b>Exam started</b>\n"
               "Questions: {n} · Pass mark: {pass}%\n"
               "Answer every question — you'll get the result and an error review at the end."),
    },
    "exam_question_counter": {
        "ru": "Вопрос {i} из {n}",
        "pl": "Pytanie {i} z {n}",
        "ua": "Питання {i} з {n}",
        "en": "Question {i} of {n}",
    },
    "exam_finished_header": {
        "ru": ("🏁 <b>Экзамен завершён</b>\n"
               "Результат: <b>{correct}/{total}</b> ({pct}%)\n"
               "{verdict} (нужно ≥ {pass}%)"),
        "pl": ("🏁 <b>Egzamin zakończony</b>\n"
               "Wynik: <b>{correct}/{total}</b> ({pct}%)\n"
               "{verdict} (potrzeba ≥ {pass}%)"),
        "ua": ("🏁 <b>Екзамен завершено</b>\n"
               "Результат: <b>{correct}/{total}</b> ({pct}%)\n"
               "{verdict} (потрібно ≥ {pass}%)"),
        "en": ("🏁 <b>Exam finished</b>\n"
               "Score: <b>{correct}/{total}</b> ({pct}%)\n"
               "{verdict} (need ≥ {pass}%)"),
    },
    "exam_no_errors": {"ru": "🎉 Без ошибок!", "pl": "🎉 Bez błędów!", "ua": "🎉 Без помилок!", "en": "🎉 No errors!"},
    "error_review_header": {
        "ru": "\n<b>Разбор ошибок:</b>",
        "pl": "\n<b>Analiza błędów:</b>",
        "ua": "\n<b>Розбір помилок:</b>",
        "en": "\n<b>Error review:</b>",
    },
    "added_to_mistakes": {
        "ru": "\nЭти вопросы добавлены в «Работу над ошибками».",
        "pl": "\nTe pytania dodano do „Pracy nad błędami”.",
        "ua": "\nЦі питання додано до «Роботи над помилками».",
        "en": "\nThese questions were added to “Mistakes practice”.",
    },
    "exam_inactive": {
        "ru": ("Этот экзамен больше не активен (возможно, бот перезапускался). "
               "Начни заново: /menu → «📝 Экзамен»."),
        "pl": ("Ten egzamin nie jest już aktywny (bot mógł się restartować). "
               "Zacznij od nowa: /menu → „📝 Egzamin”."),
        "ua": ("Цей екзамен більше не активний (можливо, бот перезапускався). "
               "Почни заново: /menu → «📝 Екзамен»."),
        "en": ("This exam is no longer active (the bot may have restarted). "
               "Start over: /menu → “📝 Exam”."),
    },

    # ─────────────── команда /start ───────────────
    "start_webapp": {
        "ru": ("⚓ <b>ISSA Trainer</b> — подготовка к экзамену Inshore Skipper + SRC\n\n"
               "<b>{n} вопросов</b> с разбором и источниками, конспект по "
               "учебнику, морские калькуляторы, интервальное повторение, пробный экзамен "
               "и отслеживание готовности.\n\n"
               "👉 <b>Всё это — в приложении.</b> Нажми «Открыть тренажёр»:"),
        "pl": ("⚓ <b>ISSA Trainer</b> — przygotowanie do egzaminu Inshore Skipper + SRC\n\n"
               "<b>{n} pytań</b> z wyjaśnieniami i źródłami, notatki z "
               "podręcznika, kalkulatory morskie, powtórki interwałowe, egzamin próbny "
               "i śledzenie gotowości.\n\n"
               "👉 <b>Wszystko to — w aplikacji.</b> Naciśnij „Otwórz trener”:"),
        "ua": ("⚓ <b>ISSA Trainer</b> — підготовка до екзамену Inshore Skipper + SRC\n\n"
               "<b>{n} питань</b> з розбором і джерелами, конспект за "
               "підручником, морські калькулятори, інтервальне повторення, пробний екзамен "
               "і відстеження готовності.\n\n"
               "👉 <b>Усе це — у застосунку.</b> Натисни «Відкрити тренажер»:"),
        "en": ("⚓ <b>ISSA Trainer</b> — prep for the Inshore Skipper + SRC exam\n\n"
               "<b>{n} questions</b> with explanations and sources, textbook notes, "
               "marine calculators, spaced repetition, a mock exam "
               "and readiness tracking.\n\n"
               "👉 <b>All of it — in the app.</b> Tap “Open trainer”:"),
    },
    "start_fallback": {
        "ru": ("⚓ <b>Тренажёр ISSA Inshore Skipper + SRC</b>\n\n"
               "В банке <b>{n}</b> вопросов по темам: "
               "терминология, паруса, манёвры, якорение, навигация, "
               "IALA, COLREG (МППСС), огни/знаки, звуковые сигналы, метео, "
               "безопасность, VHF/SRC, планирование, практика.\n\n"
               "Вопросы <b>не повторяются</b>, пока не пройдёшь весь круг.\n\n"
               "{disclaimer}\n\nВыбери режим:"),
        "pl": ("⚓ <b>Trener ISSA Inshore Skipper + SRC</b>\n\n"
               "W bazie <b>{n}</b> pytań z tematów: "
               "terminologia, żagle, manewry, kotwiczenie, nawigacja, "
               "IALA, COLREG (MPZZM), światła/znaki, sygnały dźwiękowe, meteo, "
               "bezpieczeństwo, VHF/SRC, planowanie, praktyka.\n\n"
               "Pytania <b>się nie powtarzają</b>, dopóki nie przejdziesz całej rundy.\n\n"
               "{disclaimer}\n\nWybierz tryb:"),
        "ua": ("⚓ <b>Тренажер ISSA Inshore Skipper + SRC</b>\n\n"
               "У банку <b>{n}</b> питань за темами: "
               "термінологія, вітрила, маневри, якоріння, навігація, "
               "IALA, COLREG (МПЗЗС), вогні/знаки, звукові сигнали, метео, "
               "безпека, VHF/SRC, планування, практика.\n\n"
               "Питання <b>не повторюються</b>, доки не пройдеш усе коло.\n\n"
               "{disclaimer}\n\nОбери режим:"),
        "en": ("⚓ <b>ISSA Inshore Skipper + SRC Trainer</b>\n\n"
               "The bank has <b>{n}</b> questions across topics: "
               "terminology, sails, manoeuvres, anchoring, navigation, "
               "IALA, COLREG, lights/marks, sound signals, meteo, "
               "safety, VHF/SRC, planning, practice.\n\n"
               "Questions <b>don't repeat</b> until you complete a full round.\n\n"
               "{disclaimer}\n\nPick a mode:"),
    },
    "start_quiz_note": {
        "ru": ("🎓 Доступно приложение «Тесты» — кнопка снизу (тренировка и экзамен "
               "с таймером; результат сохраняется в твой прогресс)."),
        "pl": ("🎓 Dostępna aplikacja „Testy” — przycisk poniżej (trening i egzamin "
               "z timerem; wynik zapisuje się w Twoim postępie)."),
        "ua": ("🎓 Доступний застосунок «Тести» — кнопка знизу (тренування та екзамен "
               "з таймером; результат зберігається у твій прогрес)."),
        "en": ("🎓 The “Tests” app is available — button below (practice and exam "
               "with a timer; the result is saved to your progress)."),
    },

    # ─────────────── /tests ───────────────
    "tests_available": {
        "ru": ("🎓 <b>Приложение «Тесты»</b>\n"
               "Нажми кнопку снизу — откроется тренажёр (тренировка/экзамен). "
               "Результат вернётся в бота и сохранится в прогресс."),
        "pl": ("🎓 <b>Aplikacja „Testy”</b>\n"
               "Naciśnij przycisk poniżej — otworzy się trener (trening/egzamin). "
               "Wynik wróci do bota i zapisze się w postępie."),
        "ua": ("🎓 <b>Застосунок «Тести»</b>\n"
               "Натисни кнопку знизу — відкриється тренажер (тренування/екзамен). "
               "Результат повернеться в бота і збережеться в прогрес."),
        "en": ("🎓 <b>The “Tests” app</b>\n"
               "Tap the button below — the trainer opens (practice/exam). "
               "The result returns to the bot and is saved to your progress."),
    },
    "tests_unavailable": {
        "ru": ("Приложение «Тесты» пока не подключено. Тренироваться можно прямо "
               "в чате: /menu → «🎯 Случайный вопрос» или «📝 Экзамен»."),
        "pl": ("Aplikacja „Testy” nie jest jeszcze podłączona. Ćwiczyć można wprost "
               "na czacie: /menu → „🎯 Losowe pytanie” lub „📝 Egzamin”."),
        "ua": ("Застосунок «Тести» поки не підключено. Тренуватися можна прямо "
               "в чаті: /menu → «🎯 Випадкове питання» або «📝 Екзамен»."),
        "en": ("The “Tests” app isn't connected yet. You can practise right "
               "in the chat: /menu → “🎯 Random question” or “📝 Exam”."),
    },

    # ─────────────── /menu ───────────────
    "menu_webapp": {
        "ru": "👉 Открой тренажёр — весь функционал внутри приложения:",
        "pl": "👉 Otwórz trener — cała funkcjonalność w aplikacji:",
        "ua": "👉 Відкрий тренажер — весь функціонал усередині застосунку:",
        "en": "👉 Open the trainer — everything is inside the app:",
    },
    "menu_plain": {"ru": "Главное меню:", "pl": "Menu główne:", "ua": "Головне меню:", "en": "Main menu:"},

    # ─────────────── /help ───────────────
    "help": {
        "ru": ("<b>Команды:</b>\n"
               "/start — главное меню\n"
               "/menu — меню режимов\n"
               "/stats — моя статистика\n"
               "/calc — морской калькулятор (TVMDC, скорость/время/ETA)\n"
               "/tests — приложение «Тесты» (если подключено)\n"
               "/language — 🌐 язык / language\n"
               "/about — о боте\n"
               "/privacy — конфиденциальность\n"
               "/help — эта справка\n\n"
               "🌐 <b>Язык / Language:</b> /language — RU · PL · UA · EN\n\n"
               "В режиме quiz нажимай на вариант ответа — бот сразу покажет, "
               "верно ли, и даст пояснение."),
        "pl": ("<b>Komendy:</b>\n"
               "/start — menu główne\n"
               "/menu — menu trybów\n"
               "/stats — moje statystyki\n"
               "/calc — kalkulator morski (TVMDC, prędkość/czas/ETA)\n"
               "/tests — aplikacja „Testy” (jeśli podłączona)\n"
               "/language — 🌐 język / language\n"
               "/about — o bocie\n"
               "/privacy — prywatność\n"
               "/help — ta pomoc\n\n"
               "🌐 <b>Język / Language:</b> /language — RU · PL · UA · EN\n\n"
               "W trybie quiz naciskaj wariant odpowiedzi — bot od razu pokaże, "
               "czy dobrze, i doda wyjaśnienie."),
        "ua": ("<b>Команди:</b>\n"
               "/start — головне меню\n"
               "/menu — меню режимів\n"
               "/stats — моя статистика\n"
               "/calc — морський калькулятор (TVMDC, швидкість/час/ETA)\n"
               "/tests — застосунок «Тести» (якщо підключено)\n"
               "/language — 🌐 мова / language\n"
               "/about — про бота\n"
               "/privacy — конфіденційність\n"
               "/help — ця довідка\n\n"
               "🌐 <b>Мова / Language:</b> /language — RU · PL · UA · EN\n\n"
               "У режимі quiz натискай варіант відповіді — бот одразу покаже, "
               "чи правильно, і дасть пояснення."),
        "en": ("<b>Commands:</b>\n"
               "/start — main menu\n"
               "/menu — mode menu\n"
               "/stats — my stats\n"
               "/calc — marine calculator (TVMDC, speed/time/ETA)\n"
               "/tests — the “Tests” app (if connected)\n"
               "/language — 🌐 language\n"
               "/about — about the bot\n"
               "/privacy — privacy\n"
               "/help — this help\n\n"
               "🌐 <b>Language:</b> /language — RU · PL · UA · EN\n\n"
               "In quiz mode tap an answer option — the bot instantly shows "
               "whether it's correct and gives an explanation."),
    },

    # ─────────────── /about ───────────────
    "about_title": {
        "ru": "⚓ <b>Тренажёр ISSA Inshore Skipper + SRC</b>\n\n{disclaimer}",
        "pl": "⚓ <b>Trener ISSA Inshore Skipper + SRC</b>\n\n{disclaimer}",
        "ua": "⚓ <b>Тренажер ISSA Inshore Skipper + SRC</b>\n\n{disclaimer}",
        "en": "⚓ <b>ISSA Inshore Skipper + SRC Trainer</b>\n\n{disclaimer}",
    },

    # ─────────────── /privacy ───────────────
    "privacy": {
        "ru": ("🔒 <b>Конфиденциальность</b>\n\n"
               "Бот хранит только <b>ваш Telegram ID</b> и <b>прогресс обучения</b> "
               "(какие вопросы видели, ошибки, статистика) — чтобы вести вашу "
               "тренировку отдельно.\n\n"
               "❌ Не собираются: имя, телефон, переписка, геолокация, платежи.\n"
               "Бот работает только в личном чате и не читает группы.\n\n"
               "Удалить свои данные — кнопка «♻️ Сбросить прогресс» в меню."),
        "pl": ("🔒 <b>Prywatność</b>\n\n"
               "Bot przechowuje tylko <b>Twój Telegram ID</b> i <b>postęp nauki</b> "
               "(które pytania widziałeś, błędy, statystyki) — aby prowadzić Twój "
               "trening osobno.\n\n"
               "❌ Nie zbieramy: imienia, telefonu, korespondencji, geolokalizacji, płatności.\n"
               "Bot działa tylko na czacie prywatnym i nie czyta grup.\n\n"
               "Usuń swoje dane — przycisk „♻️ Zresetuj postęp” w menu."),
        "ua": ("🔒 <b>Конфіденційність</b>\n\n"
               "Бот зберігає лише <b>ваш Telegram ID</b> та <b>прогрес навчання</b> "
               "(які питання бачили, помилки, статистика) — щоб вести ваше "
               "тренування окремо.\n\n"
               "❌ Не збираються: ім'я, телефон, листування, геолокація, платежі.\n"
               "Бот працює лише в приватному чаті й не читає групи.\n\n"
               "Видалити свої дані — кнопка «♻️ Скинути прогрес» у меню."),
        "en": ("🔒 <b>Privacy</b>\n\n"
               "The bot stores only <b>your Telegram ID</b> and <b>learning progress</b> "
               "(which questions you saw, mistakes, stats) — to keep your "
               "training separate.\n\n"
               "❌ Not collected: name, phone, messages, location, payments.\n"
               "The bot works only in a private chat and doesn't read groups.\n\n"
               "Delete your data — the “♻️ Reset progress” button in the menu."),
    },

    # ─────────────── статистика ───────────────
    "stats": {
        "ru": ("📊 <b>Твоя статистика</b>\n\n"
               "Отвечено: <b>{answered}</b>\n"
               "Правильно: <b>{correct}</b> ({pct}%)\n"
               "Вопросов на повтор (ошибки): <b>{wrong_n}</b>\n"
               "Пройдено из банка: <b>{seen_n}/{total}</b>"),
        "pl": ("📊 <b>Twoje statystyki</b>\n\n"
               "Odpowiedziano: <b>{answered}</b>\n"
               "Poprawnie: <b>{correct}</b> ({pct}%)\n"
               "Pytań do powtórki (błędy): <b>{wrong_n}</b>\n"
               "Przerobiono z banku: <b>{seen_n}/{total}</b>"),
        "ua": ("📊 <b>Твоя статистика</b>\n\n"
               "Відповіли: <b>{answered}</b>\n"
               "Правильно: <b>{correct}</b> ({pct}%)\n"
               "Питань на повтор (помилки): <b>{wrong_n}</b>\n"
               "Пройдено з банку: <b>{seen_n}/{total}</b>"),
        "en": ("📊 <b>Your stats</b>\n\n"
               "Answered: <b>{answered}</b>\n"
               "Correct: <b>{correct}</b> ({pct}%)\n"
               "Questions to review (mistakes): <b>{wrong_n}</b>\n"
               "Covered from bank: <b>{seen_n}/{total}</b>"),
    },

    # ─────────────── донат ───────────────
    "donate_coffee": {"ru": "☕ Кофе", "pl": "☕ Kawa", "ua": "☕ Кава", "en": "☕ Coffee"},
    "donate_thanks_tier": {"ru": "⭐ Спасибо", "pl": "⭐ Dzięki", "ua": "⭐ Дякую", "en": "⭐ Thanks"},
    "donate_generous": {"ru": "🚀 Щедро", "pl": "🚀 Hojnie", "ua": "🚀 Щедро", "en": "🚀 Generous"},
    "donate_intro": {
        "ru": ("💙 <b>Спасибо, что хочешь поддержать проект!</b>\n\n"
               "Тренажёр — некоммерческий и делается в свободное время. "
               "Любая поддержка мотивирует развивать его дальше. "
               "Выбери сумму в Telegram Stars — это не обязательно и ни на что не влияет 🙂"),
        "pl": ("💙 <b>Dziękuję, że chcesz wesprzeć projekt!</b>\n\n"
               "Trener jest niekomercyjny i powstaje w wolnym czasie. "
               "Każde wsparcie motywuje do dalszego rozwoju. "
               "Wybierz kwotę w Telegram Stars — to nieobowiązkowe i na nic nie wpływa 🙂"),
        "ua": ("💙 <b>Дякую, що хочеш підтримати проєкт!</b>\n\n"
               "Тренажер — некомерційний і робиться у вільний час. "
               "Будь-яка підтримка мотивує розвивати його далі. "
               "Обери суму в Telegram Stars — це необов'язково і ні на що не впливає 🙂"),
        "en": ("💙 <b>Thanks for wanting to support the project!</b>\n\n"
               "The trainer is non-commercial and made in spare time. "
               "Any support motivates further development. "
               "Pick an amount in Telegram Stars — it's optional and changes nothing 🙂"),
    },
    "donate_bad_amount": {"ru": "Некорректная сумма", "pl": "Nieprawidłowa kwota", "ua": "Некоректна сума", "en": "Invalid amount"},
    "donate_invoice_title": {
        "ru": "Поддержка ISSA Trainer",
        "pl": "Wsparcie ISSA Trainer",
        "ua": "Підтримка ISSA Trainer",
        "en": "Support ISSA Trainer",
    },
    "donate_invoice_desc": {
        "ru": "Благодарность автору тренажёра. Спасибо за поддержку! ⚓",
        "pl": "Podziękowanie dla autora trenera. Dziękujemy za wsparcie! ⚓",
        "ua": "Подяка автору тренажера. Дякуємо за підтримку! ⚓",
        "en": "A thank-you to the trainer's author. Thanks for the support! ⚓",
    },
    "donate_price": {"ru": "{amount} Stars", "pl": "{amount} Stars", "ua": "{amount} Stars", "en": "{amount} Stars"},
    "donate_payment_thanks": {
        "ru": ("💙 <b>Огромное спасибо за поддержку — {stars} ⭐!</b>\n\n"
               "Это правда помогает развивать тренажёр. Попутного ветра! ⛵"),
        "pl": ("💙 <b>Ogromne dzięki za wsparcie — {stars} ⭐!</b>\n\n"
               "To naprawdę pomaga rozwijać trener. Pomyślnych wiatrów! ⛵"),
        "ua": ("💙 <b>Величезне дякую за підтримку — {stars} ⭐!</b>\n\n"
               "Це справді допомагає розвивати тренажер. Попутного вітру! ⛵"),
        "en": ("💙 <b>Huge thanks for the support — {stars} ⭐!</b>\n\n"
               "It really helps develop the trainer. Fair winds! ⛵"),
    },

    # ─────────────── /language ───────────────
    "language_pick": {
        "ru": "🌐 <b>Язык интерфейса</b>\nВыбери язык (контент вопросов остаётся на русском):",
        "pl": "🌐 <b>Język interfejsu</b>\nWybierz język (treść pytań pozostaje po rosyjsku):",
        "ua": "🌐 <b>Мова інтерфейсу</b>\nОбери мову (контент питань залишається російською):",
        "en": "🌐 <b>Interface language</b>\nPick a language (question content stays in Russian):",
    },
    "language_changed": {
        "ru": "✅ Язык интерфейса: 🇷🇺 Русский",
        "pl": "✅ Język interfejsu: 🇵🇱 Polski",
        "ua": "✅ Мова інтерфейсу: 🇺🇦 Українська",
        "en": "✅ Interface language: 🇬🇧 English",
    },

    # ─────────────── конспект ───────────────
    "konspekt_intro": {
        "ru": ("📖 <b>Конспект по теории ISSA Inshore Skipper + SRC</b>\n\n"
               "Выбери тему. Жирным выделены термины и формулы, которые чаще всего "
               "спрашивают на тесте."),
        "pl": ("📖 <b>Notatki z teorii ISSA Inshore Skipper + SRC</b>\n\n"
               "Wybierz temat. Pogrubieniem zaznaczono terminy i wzory, o które najczęściej "
               "pytają na teście."),
        "ua": ("📖 <b>Конспект з теорії ISSA Inshore Skipper + SRC</b>\n\n"
               "Обери тему. Жирним виділено терміни та формули, які найчастіше "
               "питають на тесті."),
        "en": ("📖 <b>ISSA Inshore Skipper + SRC theory notes</b>\n\n"
               "Pick a topic. Bold marks the terms and formulas most often "
               "asked on the test."),
    },
    "topic_not_found": {"ru": "Тема не найдена", "pl": "Nie znaleziono tematu", "ua": "Тему не знайдено", "en": "Topic not found"},
    "konspekt_next": {
        "ru": "⬆️ Тема выше. Выбери следующую:",
        "pl": "⬆️ Temat powyżej. Wybierz następny:",
        "ua": "⬆️ Тема вище. Обери наступну:",
        "en": "⬆️ Topic above. Pick the next one:",
    },

    # ─────────────── шпаргалки ───────────────
    "cheat_intro": {
        "ru": ("📌 <b>Шпаргалки</b>\n\nКраткие выжимки по ключевым темам — удобно "
               "повторить перед тестом или экзаменом."),
        "pl": ("📌 <b>Ściągi</b>\n\nKrótkie wyciągi z kluczowych tematów — wygodnie "
               "powtórzyć przed testem lub egzaminem."),
        "ua": ("📌 <b>Шпаргалки</b>\n\nКороткі витяги за ключовими темами — зручно "
               "повторити перед тестом чи екзаменом."),
        "en": ("📌 <b>Cheat sheets</b>\n\nShort summaries of key topics — handy "
               "to review before a test or exam."),
    },
    "choose_knot": {
        "ru": "Выбери узел — покажу пошагово с фото:",
        "pl": "Wybierz węzeł — pokażę krok po kroku ze zdjęciami:",
        "ua": "Обери вузол — покажу покроково з фото:",
        "en": "Pick a knot — I'll show it step by step with photos:",
    },
    "cheat_not_found": {"ru": "Шпаргалка не найдена", "pl": "Nie znaleziono ściągi", "ua": "Шпаргалку не знайдено", "en": "Cheat sheet not found"},
    "cheat_next": {
        "ru": "⬆️ Шпаргалка выше. Ещё:",
        "pl": "⬆️ Ściąga powyżej. Więcej:",
        "ua": "⬆️ Шпаргалка вище. Ще:",
        "en": "⬆️ Cheat sheet above. More:",
    },
    "back_cheat": {"ru": "⬅️ К шпаргалкам", "pl": "⬅️ Do ściąg", "ua": "⬅️ До шпаргалок", "en": "⬅️ To cheat sheets"},

    # ─────────────── узлы ───────────────
    "knot_not_found": {"ru": "Узел не найден", "pl": "Nie znaleziono węzła", "ua": "Вузол не знайдено", "en": "Knot not found"},
    "knot_done": {
        "ru": "Готово! Выбери другой узел:",
        "pl": "Gotowe! Wybierz inny węzeł:",
        "ua": "Готово! Обери інший вузол:",
        "en": "Done! Pick another knot:",
    },

    # ─────────────── словарь ───────────────
    "glossary_intro": {
        "ru": ("📚 <b>Словарь яхтсмена</b> ({n} терминов)\n\n"
               "Морские и яхтенные термины простыми словами. Выбери категорию "
               "или нажми «🔎 Поиск термина».\n\n"
               "<i>Вспомогательный материал для подготовки, не официальный учебник.</i>"),
        "pl": ("📚 <b>Słownik żeglarski</b> ({n} terminów)\n\n"
               "Morskie i żeglarskie terminy prostymi słowami. Wybierz kategorię "
               "lub naciśnij „🔎 Szukaj terminu”.\n\n"
               "<i>Materiał pomocniczy do nauki, nie oficjalny podręcznik.</i>"),
        "ua": ("📚 <b>Словник яхтсмена</b> ({n} термінів)\n\n"
               "Морські та яхтові терміни простими словами. Обери категорію "
               "або натисни «🔎 Пошук терміна».\n\n"
               "<i>Допоміжний матеріал для підготовки, не офіційний підручник.</i>"),
        "en": ("📚 <b>Sailor's glossary</b> ({n} terms)\n\n"
               "Marine and yachting terms in plain words. Pick a category "
               "or tap “🔎 Search term”.\n\n"
               "<i>A supporting study aid, not an official textbook.</i>"),
    },
    "glossary_search_btn": {"ru": "🔎 Поиск термина", "pl": "🔎 Szukaj terminu", "ua": "🔎 Пошук терміна", "en": "🔎 Search term"},
    "category_not_found": {"ru": "Категория не найдена", "pl": "Nie znaleziono kategorii", "ua": "Категорію не знайдено", "en": "Category not found"},
    "choose_term": {"ru": "Выбери термин:", "pl": "Wybierz termin:", "ua": "Обери термін:", "en": "Pick a term:"},
    "term_not_found": {"ru": "Термин не найден", "pl": "Nie znaleziono terminu", "ua": "Термін не знайдено", "en": "Term not found"},
    "back_categories": {"ru": "⬅️ К категориям", "pl": "⬅️ Do kategorii", "ua": "⬅️ До категорій", "en": "⬅️ To categories"},
    "back_list": {"ru": "⬅️ К списку", "pl": "⬅️ Do listy", "ua": "⬅️ До списку", "en": "⬅️ To list"},
    "categories_btn": {"ru": "📚 Категории", "pl": "📚 Kategorie", "ua": "📚 Категорії", "en": "📚 Categories"},
    "glossary_search_prompt": {
        "ru": ("🔎 Напиши слово для поиска по словарю (например <code>киль</code>, "
               "<code>mayday</code>, <code>галс</code>)."),
        "pl": ("🔎 Napisz słowo do wyszukania w słowniku (np. <code>киль</code>, "
               "<code>mayday</code>, <code>галс</code>)."),
        "ua": ("🔎 Напиши слово для пошуку по словнику (наприклад <code>киль</code>, "
               "<code>mayday</code>, <code>галс</code>)."),
        "en": ("🔎 Type a word to search the glossary (e.g. <code>киль</code>, "
               "<code>mayday</code>, <code>галс</code>)."),
    },
    "glossary_not_found": {
        "ru": "Ничего не нашёл 🤷 Попробуй другое слово или открой категории.",
        "pl": "Nic nie znalazłem 🤷 Spróbuj innego słowa lub otwórz kategorie.",
        "ua": "Нічого не знайшов 🤷 Спробуй інше слово або відкрий категорії.",
        "en": "Found nothing 🤷 Try another word or open the categories.",
    },
    "glossary_found": {
        "ru": "🔎 Найдено: {n}\n\n",
        "pl": "🔎 Znaleziono: {n}\n\n",
        "ua": "🔎 Знайдено: {n}\n\n",
        "en": "🔎 Found: {n}\n\n",
    },

    # ─────────────── практические задачи ───────────────
    "ptask_new": {"ru": "🎲 Новая задача", "pl": "🎲 Nowe zadanie", "ua": "🎲 Нова задача", "en": "🎲 New problem"},
    "ptask_solve_btn": {"ru": "💡 Показать решение", "pl": "💡 Pokaż rozwiązanie", "ua": "💡 Показати розв'язання", "en": "💡 Show solution"},
    "ptask_stats_btn": {"ru": "📊 Статистика", "pl": "📊 Statystyki", "ua": "📊 Статистика", "en": "📊 Stats"},
    "calc_btn": {"ru": "🧮 Калькулятор", "pl": "🧮 Kalkulator", "ua": "🧮 Калькулятор", "en": "🧮 Calculator"},
    "ptask_prompt": {
        "ru": ("📝 <b>Практическая задача</b>\n\n{text}\n\n"
               "✍️ Напиши ответ числом (в {unit}). Допуск ±{tol}."),
        "pl": ("📝 <b>Zadanie praktyczne</b>\n\n{text}\n\n"
               "✍️ Wpisz odpowiedź liczbą (w {unit}). Tolerancja ±{tol}."),
        "ua": ("📝 <b>Практична задача</b>\n\n{text}\n\n"
               "✍️ Напиши відповідь числом (у {unit}). Допуск ±{tol}."),
        "en": ("📝 <b>Practical problem</b>\n\n{text}\n\n"
               "✍️ Write the answer as a number (in {unit}). Tolerance ±{tol}."),
    },
    "ptasks_intro": {
        "ru": ("📝 <b>Практические задачи</b>\n\n"
               "Скорость · дистанция · время · ETA. Реши задачу — бот проверит ответ "
               "и покажет решение. Ведётся серия (streak)."),
        "pl": ("📝 <b>Zadania praktyczne</b>\n\n"
               "Prędkość · dystans · czas · ETA. Rozwiąż zadanie — bot sprawdzi odpowiedź "
               "i pokaże rozwiązanie. Liczona jest seria (streak)."),
        "ua": ("📝 <b>Практичні задачі</b>\n\n"
               "Швидкість · дистанція · час · ETA. Розв'яжи задачу — бот перевірить відповідь "
               "і покаже розв'язання. Ведеться серія (streak)."),
        "en": ("📝 <b>Practical problems</b>\n\n"
               "Speed · distance · time · ETA. Solve a problem — the bot checks your answer "
               "and shows the solution. A streak is tracked."),
    },
    "take_task_first": {"ru": "Сначала возьми задачу", "pl": "Najpierw weź zadanie", "ua": "Спершу візьми задачу", "en": "Take a problem first"},
    "ptask_solution": {
        "ru": ("💡 <b>Решение</b>\n\n{text}\n\n<pre>{solution}</pre>\n"
               "✅ Ответ: <b>{answer} {unit}</b>"),
        "pl": ("💡 <b>Rozwiązanie</b>\n\n{text}\n\n<pre>{solution}</pre>\n"
               "✅ Odpowiedź: <b>{answer} {unit}</b>"),
        "ua": ("💡 <b>Розв'язання</b>\n\n{text}\n\n<pre>{solution}</pre>\n"
               "✅ Відповідь: <b>{answer} {unit}</b>"),
        "en": ("💡 <b>Solution</b>\n\n{text}\n\n<pre>{solution}</pre>\n"
               "✅ Answer: <b>{answer} {unit}</b>"),
    },
    "ptask_stats": {
        "ru": ("📊 <b>Статистика практических задач</b>\n\n"
               "Решено верно: <b>{solved}</b> из {att} ({acc}%)\n"
               "🔥 Текущая серия: <b>{streak}</b>\n"
               "🏆 Лучшая серия: <b>{best}</b>\n\n"
               "Всего задач в банке: {total}."),
        "pl": ("📊 <b>Statystyki zadań praktycznych</b>\n\n"
               "Rozwiązano poprawnie: <b>{solved}</b> z {att} ({acc}%)\n"
               "🔥 Aktualna seria: <b>{streak}</b>\n"
               "🏆 Najlepsza seria: <b>{best}</b>\n\n"
               "Wszystkich zadań w banku: {total}."),
        "ua": ("📊 <b>Статистика практичних задач</b>\n\n"
               "Розв'язано правильно: <b>{solved}</b> з {att} ({acc}%)\n"
               "🔥 Поточна серія: <b>{streak}</b>\n"
               "🏆 Найкраща серія: <b>{best}</b>\n\n"
               "Усього задач у банку: {total}."),
        "en": ("📊 <b>Practical problems stats</b>\n\n"
               "Solved correctly: <b>{solved}</b> of {att} ({acc}%)\n"
               "🔥 Current streak: <b>{streak}</b>\n"
               "🏆 Best streak: <b>{best}</b>\n\n"
               "Total problems in the bank: {total}."),
    },
    "ptask_correct": {
        "ru": ("✅ <b>Верно!</b> Ответ {answer} {unit}.\n{streak_line}\n\n<pre>{solution}</pre>"),
        "pl": ("✅ <b>Dobrze!</b> Odpowiedź {answer} {unit}.\n{streak_line}\n\n<pre>{solution}</pre>"),
        "ua": ("✅ <b>Правильно!</b> Відповідь {answer} {unit}.\n{streak_line}\n\n<pre>{solution}</pre>"),
        "en": ("✅ <b>Correct!</b> Answer {answer} {unit}.\n{streak_line}\n\n<pre>{solution}</pre>"),
    },
    "ptask_wrong": {
        "ru": ("❌ Не то. Проверь формулу (t=D/V, D=V·t, V=D/t) и единицы.\n"
               "Попробуй ещё раз или нажми «💡 Показать решение».\n"
               "<i>Серия сброшена. Лучшая: {best}.</i>"),
        "pl": ("❌ Nie to. Sprawdź wzór (t=D/V, D=V·t, V=D/t) i jednostki.\n"
               "Spróbuj ponownie lub naciśnij „💡 Pokaż rozwiązanie”.\n"
               "<i>Seria wyzerowana. Najlepsza: {best}.</i>"),
        "ua": ("❌ Не те. Перевір формулу (t=D/V, D=V·t, V=D/t) і одиниці.\n"
               "Спробуй ще раз або натисни «💡 Показати розв'язання».\n"
               "<i>Серію скинуто. Найкраща: {best}.</i>"),
        "en": ("❌ Not quite. Check the formula (t=D/V, D=V·t, V=D/t) and the units.\n"
               "Try again or tap “💡 Show solution”.\n"
               "<i>Streak reset. Best: {best}.</i>"),
    },

    # ─────────────── задачи T-V-M-D-C ───────────────
    "task_new": {"ru": "🎲 Новая задача", "pl": "🎲 Nowe zadanie", "ua": "🎲 Нова задача", "en": "🎲 New problem"},
    "task_star": {"ru": "⭐ Со звёздочкой", "pl": "⭐ Z gwiazdką", "ua": "⭐ Із зірочкою", "en": "⭐ Starred"},
    "task_solve_btn": {"ru": "💡 Показать решение", "pl": "💡 Pokaż rozwiązanie", "ua": "💡 Показати розв'язання", "en": "💡 Show solution"},
    "task_stats_btn": {"ru": "📊 Статистика задач", "pl": "📊 Statystyki zadań", "ua": "📊 Статистика задач", "en": "📊 Problem stats"},
    "task_star_note": {
        "ru": " ⭐<i>(с подвохом — возможен переход через 360°)</i>",
        "pl": " ⭐<i>(z podchwytem — możliwe przejście przez 360°)</i>",
        "ua": " ⭐<i>(з підступом — можливий перехід через 360°)</i>",
        "en": " ⭐<i>(tricky — may wrap past 360°)</i>",
    },
    "task_prompt": {
        "ru": ("🧭 <b>Задача T-V-M-D-C</b>{star}\n\n{text}\n\n"
               "✍️ Напиши ответ числом (градусы), например <code>046</code>."),
        "pl": ("🧭 <b>Zadanie T-V-M-D-C</b>{star}\n\n{text}\n\n"
               "✍️ Wpisz odpowiedź liczbą (stopnie), np. <code>046</code>."),
        "ua": ("🧭 <b>Задача T-V-M-D-C</b>{star}\n\n{text}\n\n"
               "✍️ Напиши відповідь числом (градуси), наприклад <code>046</code>."),
        "en": ("🧭 <b>T-V-M-D-C problem</b>{star}\n\n{text}\n\n"
               "✍️ Write the answer as a number (degrees), e.g. <code>046</code>."),
    },
    "tasks_intro": {
        "ru": ("🧭 <b>Решение задач: поправки компаса (T-V-M-D-C)</b>\n\n"
               "Цепочка: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "Вниз (T→C): <b>East −, West +</b>. Вверх (C→T): наоборот.\n\n"
               "Задачи можно повторять — цель научиться решать. "
               "Есть задачи <b>со звёздочкой</b> (с подвохом, &gt;360°)."),
        "pl": ("🧭 <b>Zadania: poprawki kompasu (T-V-M-D-C)</b>\n\n"
               "Łańcuch: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "W dół (T→C): <b>East −, West +</b>. W górę (C→T): odwrotnie.\n\n"
               "Zadania można powtarzać — celem jest nauczyć się rozwiązywać. "
               "Są zadania <b>z gwiazdką</b> (z podchwytem, &gt;360°)."),
        "ua": ("🧭 <b>Розв'язання задач: поправки компаса (T-V-M-D-C)</b>\n\n"
               "Ланцюжок: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "Вниз (T→C): <b>East −, West +</b>. Вгору (C→T): навпаки.\n\n"
               "Задачі можна повторювати — мета навчитися розв'язувати. "
               "Є задачі <b>із зірочкою</b> (з підступом, &gt;360°)."),
        "en": ("🧭 <b>Problems: compass corrections (T-V-M-D-C)</b>\n\n"
               "Chain: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "Down (T→C): <b>East −, West +</b>. Up (C→T): the reverse.\n\n"
               "Problems can be repeated — the goal is to learn to solve them. "
               "There are <b>starred</b> problems (tricky, &gt;360°)."),
    },
    "task_inactive": {
        "ru": ("Задача не активна (возможно, бот перезапускался). Возьми новую: /tasks"),
        "pl": ("Zadanie nieaktywne (bot mógł się restartować). Weź nowe: /tasks"),
        "ua": ("Задача не активна (можливо, бот перезапускався). Візьми нову: /tasks"),
        "en": ("The problem isn't active (the bot may have restarted). Take a new one: /tasks"),
    },
    "task_solution": {
        "ru": ("💡 <b>Решение</b>\n\n{text}\n\n<pre>{solution}</pre>\n"
               "✅ Ответ: <b>{answer}°</b>"),
        "pl": ("💡 <b>Rozwiązanie</b>\n\n{text}\n\n<pre>{solution}</pre>\n"
               "✅ Odpowiedź: <b>{answer}°</b>"),
        "ua": ("💡 <b>Розв'язання</b>\n\n{text}\n\n<pre>{solution}</pre>\n"
               "✅ Відповідь: <b>{answer}°</b>"),
        "en": ("💡 <b>Solution</b>\n\n{text}\n\n<pre>{solution}</pre>\n"
               "✅ Answer: <b>{answer}°</b>"),
    },
    "task_stats": {
        "ru": ("📊 <b>Статистика по задачам T-V-M-D-C</b>\n\n"
               "Решено верно: <b>{solved}</b> из {att} ({acc}%)\n"
               "🔥 Текущая серия: <b>{streak}</b>\n"
               "🏆 Лучшая серия: <b>{best}</b>\n\n"
               "Всего задач в банке: {total} (⭐ с подвохом: {starred})."),
        "pl": ("📊 <b>Statystyki zadań T-V-M-D-C</b>\n\n"
               "Rozwiązano poprawnie: <b>{solved}</b> z {att} ({acc}%)\n"
               "🔥 Aktualna seria: <b>{streak}</b>\n"
               "🏆 Najlepsza seria: <b>{best}</b>\n\n"
               "Wszystkich zadań w banku: {total} (⭐ z podchwytem: {starred})."),
        "ua": ("📊 <b>Статистика задач T-V-M-D-C</b>\n\n"
               "Розв'язано правильно: <b>{solved}</b> з {att} ({acc}%)\n"
               "🔥 Поточна серія: <b>{streak}</b>\n"
               "🏆 Найкраща серія: <b>{best}</b>\n\n"
               "Усього задач у банку: {total} (⭐ з підступом: {starred})."),
        "en": ("📊 <b>T-V-M-D-C problem stats</b>\n\n"
               "Solved correctly: <b>{solved}</b> of {att} ({acc}%)\n"
               "🔥 Current streak: <b>{streak}</b>\n"
               "🏆 Best streak: <b>{best}</b>\n\n"
               "Total problems in the bank: {total} (⭐ tricky: {starred})."),
    },
    "task_correct": {
        "ru": ("✅ <b>Верно!</b> Ответ {answer}°.\n{streak_line}\n\n<pre>{solution}</pre>"),
        "pl": ("✅ <b>Dobrze!</b> Odpowiedź {answer}°.\n{streak_line}\n\n<pre>{solution}</pre>"),
        "ua": ("✅ <b>Правильно!</b> Відповідь {answer}°.\n{streak_line}\n\n<pre>{solution}</pre>"),
        "en": ("✅ <b>Correct!</b> Answer {answer}°.\n{streak_line}\n\n<pre>{solution}</pre>"),
    },
    "task_wrong": {
        "ru": ("❌ Неверно. Проверь правило знаков (вниз: <b>East −, West +</b>) "
               "и переход через 360°.\nПопробуй ещё раз или нажми «💡 Показать решение».\n"
               "<i>Серия сброшена. Лучшая серия: {best}.</i>"),
        "pl": ("❌ Źle. Sprawdź regułę znaków (w dół: <b>East −, West +</b>) "
               "i przejście przez 360°.\nSpróbuj ponownie lub naciśnij „💡 Pokaż rozwiązanie”.\n"
               "<i>Seria wyzerowana. Najlepsza seria: {best}.</i>"),
        "ua": ("❌ Неправильно. Перевір правило знаків (вниз: <b>East −, West +</b>) "
               "і перехід через 360°.\nСпробуй ще раз або натисни «💡 Показати розв'язання».\n"
               "<i>Серію скинуто. Найкраща серія: {best}.</i>"),
        "en": ("❌ Wrong. Check the sign rule (down: <b>East −, West +</b>) "
               "and the wrap past 360°.\nTry again or tap “💡 Show solution”.\n"
               "<i>Streak reset. Best streak: {best}.</i>"),
    },
    "task_not_found": {
        "ru": "Задача не найдена. /menu",
        "pl": "Nie znaleziono zadania. /menu",
        "ua": "Задачу не знайдено. /menu",
        "en": "Problem not found. /menu",
    },
    "streak_line": {
        "ru": "🔥 Серия: <b>{n}</b>",
        "pl": "🔥 Seria: <b>{n}</b>",
        "ua": "🔥 Серія: <b>{n}</b>",
        "en": "🔥 Streak: <b>{n}</b>",
    },
    "record_suffix": {"ru": " (рекорд!)", "pl": " (rekord!)", "ua": " (рекорд!)", "en": " (record!)"},

    # ─────────────── калькулятор ───────────────
    "open_calc_app": {
        "ru": "📱 Открыть приложение-калькулятор",
        "pl": "📱 Otwórz aplikację-kalkulator",
        "ua": "📱 Відкрити застосунок-калькулятор",
        "en": "📱 Open the calculator app",
    },
    "calc_compass_intro": {
        "ru": ("🧮 <b>Калькулятор поправок компаса (TVMDC)</b>\n\n"
               "Цепочка: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "Выбери, что во что пересчитать:"),
        "pl": ("🧮 <b>Kalkulator poprawek kompasu (TVMDC)</b>\n\n"
               "Łańcuch: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "Wybierz, co na co przeliczyć:"),
        "ua": ("🧮 <b>Калькулятор поправок компаса (TVMDC)</b>\n\n"
               "Ланцюжок: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "Обери, що на що перерахувати:"),
        "en": ("🧮 <b>Compass correction calculator (TVMDC)</b>\n\n"
               "Chain: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "Pick what to convert to what:"),
    },
    "calc_compass_pick": {
        "ru": ("🧭 <b>Поправки компаса (TVMDC)</b>\n\n"
               "Цепочка: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "Выбери, что во что пересчитать:"),
        "pl": ("🧭 <b>Poprawki kompasu (TVMDC)</b>\n\n"
               "Łańcuch: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "Wybierz, co na co przeliczyć:"),
        "ua": ("🧭 <b>Поправки компаса (TVMDC)</b>\n\n"
               "Ланцюжок: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "Обери, що на що перерахувати:"),
        "en": ("🧭 <b>Compass corrections (TVMDC)</b>\n\n"
               "Chain: <code>True ↔ Variation ↔ Magnetic ↔ Deviation ↔ Compass</code>\n"
               "Pick what to convert to what:"),
    },
    "calc_result_other": {"ru": "🔄 Другое направление", "pl": "🔄 Inny kierunek", "ua": "🔄 Інший напрямок", "en": "🔄 Other direction"},
    "calc_result_train": {"ru": "🧭 Потренироваться (задачи)", "pl": "🧭 Poćwicz (zadania)", "ua": "🧭 Потренуватися (задачі)", "en": "🧭 Practice (problems)"},
    "calc_sections": {
        "ru": "🧮 <b>Морской калькулятор</b>\n\nВыбери раздел:",
        "pl": "🧮 <b>Kalkulator morski</b>\n\nWybierz sekcję:",
        "ua": "🧮 <b>Морський калькулятор</b>\n\nОбери розділ:",
        "en": "🧮 <b>Marine calculator</b>\n\nPick a section:",
    },
    "cat_compass": {"ru": "🧭 Поправки компаса (TVMDC)", "pl": "🧭 Poprawki kompasu (TVMDC)", "ua": "🧭 Поправки компаса (TVMDC)", "en": "🧭 Compass corrections (TVMDC)"},
    "cat_time_eta": {"ru": "⏱ Скорость · время · ETA", "pl": "⏱ Prędkość · czas · ETA", "ua": "⏱ Швидкість · час · ETA", "en": "⏱ Speed · time · ETA"},

    # _calc_prompt составные части
    "calc_fields_var": {
        "ru": "<b>курс</b> и <b>Variation</b>",
        "pl": "<b>kurs</b> i <b>Variation</b>",
        "ua": "<b>курс</b> і <b>Variation</b>",
        "en": "<b>course</b> and <b>Variation</b>",
    },
    "calc_fields_dev": {
        "ru": "<b>курс</b> и <b>Deviation</b>",
        "pl": "<b>kurs</b> i <b>Deviation</b>",
        "ua": "<b>курс</b> і <b>Deviation</b>",
        "en": "<b>course</b> and <b>Deviation</b>",
    },
    "calc_fields_both": {
        "ru": "<b>курс</b>, <b>Variation</b> и <b>Deviation</b>",
        "pl": "<b>kurs</b>, <b>Variation</b> i <b>Deviation</b>",
        "ua": "<b>курс</b>, <b>Variation</b> і <b>Deviation</b>",
        "en": "<b>course</b>, <b>Variation</b> and <b>Deviation</b>",
    },
    "calc_hint_var": {
        "ru": "Формат: <code>курс  variation(E/W)</code>",
        "pl": "Format: <code>kurs  variation(E/W)</code>",
        "ua": "Формат: <code>курс  variation(E/W)</code>",
        "en": "Format: <code>course  variation(E/W)</code>",
    },
    "calc_hint_dev": {
        "ru": "Формат: <code>курс  deviation(E/W)</code>",
        "pl": "Format: <code>kurs  deviation(E/W)</code>",
        "ua": "Формат: <code>курс  deviation(E/W)</code>",
        "en": "Format: <code>course  deviation(E/W)</code>",
    },
    "calc_hint_both": {
        "ru": "Формат: <code>курс  variation(E/W)  deviation(E/W)</code>",
        "pl": "Format: <code>kurs  variation(E/W)  deviation(E/W)</code>",
        "ua": "Формат: <code>курс  variation(E/W)  deviation(E/W)</code>",
        "en": "Format: <code>course  variation(E/W)  deviation(E/W)</code>",
    },
    "calc_prompt_body": {
        "ru": ("Введи {fields} одной строкой.\n"
               "{hint}\n"
               "Пример: <code>{example}</code>\n\n"
               "Направление поправки указывай буквой: <b>E</b> (восток) или <b>W</b> (запад). "
               "Можно и русские: <b>В</b>/<b>З</b>."),
        "pl": ("Podaj {fields} w jednej linii.\n"
               "{hint}\n"
               "Przykład: <code>{example}</code>\n\n"
               "Kierunek poprawki podaj literą: <b>E</b> (wschód) lub <b>W</b> (zachód)."),
        "ua": ("Введи {fields} одним рядком.\n"
               "{hint}\n"
               "Приклад: <code>{example}</code>\n\n"
               "Напрямок поправки вказуй літерою: <b>E</b> (схід) або <b>W</b> (захід)."),
        "en": ("Enter {fields} in one line.\n"
               "{hint}\n"
               "Example: <code>{example}</code>\n\n"
               "Give the correction direction as a letter: <b>E</b> (east) or <b>W</b> (west)."),
    },
    "calc_dir_header": {
        "ru": "🧮 <b>{label}</b>\n\n{prompt}",
        "pl": "🧮 <b>{label}</b>\n\n{prompt}",
        "ua": "🧮 <b>{label}</b>\n\n{prompt}",
        "en": "🧮 <b>{label}</b>\n\n{prompt}",
    },
    "unknown_direction": {"ru": "Неизвестное направление", "pl": "Nieznany kierunek", "ua": "Невідомий напрямок", "en": "Unknown direction"},
    "calc_not_understood": {
        "ru": "Не понял ввод 🤔 {prompt}",
        "pl": "Nie zrozumiałem 🤔 {prompt}",
        "ua": "Не зрозумів ввід 🤔 {prompt}",
        "en": "Didn't understand the input 🤔 {prompt}",
    },

    # ─────────────── морские расчёты (скорость/время/ETA/прилив) ───────────────
    "mk_t_title": {"ru": "⏱ Время в пути", "pl": "⏱ Czas w drodze", "ua": "⏱ Час у дорозі", "en": "⏱ Travel time"},
    "mk_t_need": {
        "ru": "Скорость (узлы) и дистанцию (NM).",
        "pl": "Prędkość (węzły) i dystans (NM).",
        "ua": "Швидкість (вузли) і дистанцію (NM).",
        "en": "Speed (knots) and distance (NM).",
    },
    "mk_d_title": {"ru": "📏 Дистанция", "pl": "📏 Dystans", "ua": "📏 Дистанція", "en": "📏 Distance"},
    "mk_d_need": {
        "ru": "Скорость (узлы) и время (часы).",
        "pl": "Prędkość (węzły) i czas (godziny).",
        "ua": "Швидкість (вузли) і час (години).",
        "en": "Speed (knots) and time (hours).",
    },
    "mk_v_title": {"ru": "🚤 Средняя скорость", "pl": "🚤 Prędkość średnia", "ua": "🚤 Середня швидкість", "en": "🚤 Average speed"},
    "mk_v_need": {
        "ru": "Дистанцию (NM) и время (часы).",
        "pl": "Dystans (NM) i czas (godziny).",
        "ua": "Дистанцію (NM) і час (години).",
        "en": "Distance (NM) and time (hours).",
    },
    "mk_e_title": {"ru": "🎯 ETA / время прибытия", "pl": "🎯 ETA / czas przybycia", "ua": "🎯 ETA / час прибуття", "en": "🎯 ETA / arrival time"},
    "mk_e_need": {
        "ru": "Дистанцию (NM), скорость (узлы), запас % и время старта ЧЧ:ММ.",
        "pl": "Dystans (NM), prędkość (węzły), zapas % i czas startu GG:MM.",
        "ua": "Дистанцію (NM), швидкість (вузли), запас % і час старту ГГ:ХХ.",
        "en": "Distance (NM), speed (knots), reserve % and start time HH:MM.",
    },
    "mk_tide_title": {"ru": "🌊 Прилив (правило 12)", "pl": "🌊 Pływ (reguła 12)", "ua": "🌊 Приплив (правило 12)", "en": "🌊 Tide (rule of 12)"},
    "mk_tide_need": {
        "ru": "Малую воду LW, полную HW (м) и часы после малой воды (0–6).",
        "pl": "Wodę niską LW, wysoką HW (m) i godziny po wodzie niskiej (0–6).",
        "ua": "Малу воду LW, повну HW (м) і години після малої води (0–6).",
        "en": "Low water LW, high water HW (m) and hours after low water (0–6).",
    },
    "marine_pick": {
        "ru": "⏱ <b>Скорость · время · ETA</b>\n\nЧто посчитать?",
        "pl": "⏱ <b>Prędkość · czas · ETA</b>\n\nCo policzyć?",
        "ua": "⏱ <b>Швидкість · час · ETA</b>\n\nЩо порахувати?",
        "en": "⏱ <b>Speed · time · ETA</b>\n\nWhat to calculate?",
    },
    "marine_result_more": {"ru": "🔄 Ещё расчёт", "pl": "🔄 Kolejne obliczenie", "ua": "🔄 Ще розрахунок", "en": "🔄 Another calc"},
    "unknown_calc": {"ru": "Неизвестный расчёт", "pl": "Nieznane obliczenie", "ua": "Невідомий розрахунок", "en": "Unknown calculation"},
    "marine_input_prompt": {
        "ru": ("{title}\n\nВведи {need}\nОдной строкой через пробел.\n"
               "Пример: <code>{example}</code>"),
        "pl": ("{title}\n\nPodaj {need}\nW jednej linii, spacjami.\n"
               "Przykład: <code>{example}</code>"),
        "ua": ("{title}\n\nВведи {need}\nОдним рядком через пробіл.\n"
               "Приклад: <code>{example}</code>"),
        "en": ("{title}\n\nEnter {need}\nOn one line, space-separated.\n"
               "Example: <code>{example}</code>"),
    },
    "err_need_speed_dist": {
        "ru": "Нужны скорость и дистанция, например «5.5 13.2».",
        "pl": "Potrzeba prędkości i dystansu, np. „5.5 13.2”.",
        "ua": "Потрібні швидкість і дистанція, наприклад «5.5 13.2».",
        "en": "Need speed and distance, e.g. “5.5 13.2”.",
    },
    "err_need_speed_time": {
        "ru": "Нужны скорость и время, например «6 2.5».",
        "pl": "Potrzeba prędkości i czasu, np. „6 2.5”.",
        "ua": "Потрібні швидкість і час, наприклад «6 2.5».",
        "en": "Need speed and time, e.g. “6 2.5”.",
    },
    "err_need_dist_time": {
        "ru": "Нужны дистанция и время, например «15 3».",
        "pl": "Potrzeba dystansu i czasu, np. „15 3”.",
        "ua": "Потрібні дистанція і час, наприклад «15 3».",
        "en": "Need distance and time, e.g. “15 3”.",
    },
    "err_need_dist_speed": {
        "ru": "Нужны минимум дистанция и скорость, например «18 5 20 09:00».",
        "pl": "Potrzeba co najmniej dystansu i prędkości, np. „18 5 20 09:00”.",
        "ua": "Потрібні щонайменше дистанція і швидкість, наприклад «18 5 20 09:00».",
        "en": "Need at least distance and speed, e.g. “18 5 20 09:00”.",
    },
    "err_need_tide": {
        "ru": "Нужны LW, HW и часы после малой воды, например «2 8 3.5».",
        "pl": "Potrzeba LW, HW i godzin po wodzie niskiej, np. „2 8 3.5”.",
        "ua": "Потрібні LW, HW і години після малої води, наприклад «2 8 3.5».",
        "en": "Need LW, HW and hours after low water, e.g. “2 8 3.5”.",
    },
    "marine_res_time": {
        "ru": ("⏱ <b>Время в пути: {h} ч</b> ({hm})\n\n"
               "<pre>t = D / V = {d} / {v} = {h} ч</pre>"),
        "pl": ("⏱ <b>Czas w drodze: {h} h</b> ({hm})\n\n"
               "<pre>t = D / V = {d} / {v} = {h} h</pre>"),
        "ua": ("⏱ <b>Час у дорозі: {h} год</b> ({hm})\n\n"
               "<pre>t = D / V = {d} / {v} = {h} год</pre>"),
        "en": ("⏱ <b>Travel time: {h} h</b> ({hm})\n\n"
               "<pre>t = D / V = {d} / {v} = {h} h</pre>"),
    },
    "marine_res_dist": {
        "ru": ("📏 <b>Дистанция: {d} NM</b>\n\n"
               "<pre>D = V × t = {v} × {t} = {d} NM</pre>"),
        "pl": ("📏 <b>Dystans: {d} NM</b>\n\n"
               "<pre>D = V × t = {v} × {t} = {d} NM</pre>"),
        "ua": ("📏 <b>Дистанція: {d} NM</b>\n\n"
               "<pre>D = V × t = {v} × {t} = {d} NM</pre>"),
        "en": ("📏 <b>Distance: {d} NM</b>\n\n"
               "<pre>D = V × t = {v} × {t} = {d} NM</pre>"),
    },
    "marine_res_speed": {
        "ru": ("🚤 <b>Средняя скорость: {v} узла</b>\n\n"
               "<pre>V = D / t = {d} / {t} = {v} узла</pre>"),
        "pl": ("🚤 <b>Prędkość średnia: {v} w</b>\n\n"
               "<pre>V = D / t = {d} / {t} = {v} w</pre>"),
        "ua": ("🚤 <b>Середня швидкість: {v} вуз.</b>\n\n"
               "<pre>V = D / t = {d} / {t} = {v} вуз.</pre>"),
        "en": ("🚤 <b>Average speed: {v} kn</b>\n\n"
               "<pre>V = D / t = {d} / {t} = {v} kn</pre>"),
    },
    "marine_eta_line_t": {
        "ru": "t = D / V = {d} / {v} = {travel} ч",
        "pl": "t = D / V = {d} / {v} = {travel} h",
        "ua": "t = D / V = {d} / {v} = {travel} год",
        "en": "t = D / V = {d} / {v} = {travel} h",
    },
    "marine_eta_line_reserve": {
        "ru": "с запасом {r}% → {w} ч",
        "pl": "z zapasem {r}% → {w} h",
        "ua": "із запасом {r}% → {w} год",
        "en": "with {r}% reserve → {w} h",
    },
    "marine_eta_head": {
        "ru": "🎯 <b>В пути: {w} ч</b> ({hm})",
        "pl": "🎯 <b>W drodze: {w} h</b> ({hm})",
        "ua": "🎯 <b>У дорозі: {w} год</b> ({hm})",
        "en": "🎯 <b>Underway: {w} h</b> ({hm})",
    },
    "marine_eta_arrival": {
        "ru": "\n🕒 <b>ETA: {eta}</b>",
        "pl": "\n🕒 <b>ETA: {eta}</b>",
        "ua": "\n🕒 <b>ETA: {eta}</b>",
        "en": "\n🕒 <b>ETA: {eta}</b>",
    },
    "marine_tide_range": {
        "ru": "Диапазон = {hw} − {lw} = {rng} м; 1/12 = {tw} м",
        "pl": "Zakres = {hw} − {lw} = {rng} m; 1/12 = {tw} m",
        "ua": "Діапазон = {hw} − {lw} = {rng} м; 1/12 = {tw} м",
        "en": "Range = {hw} − {lw} = {rng} m; 1/12 = {tw} m",
    },
    "marine_tide_step": {
        "ru": "{i}ч  +{part}/12 → {acc} м",
        "pl": "{i}h  +{part}/12 → {acc} m",
        "ua": "{i}год  +{part}/12 → {acc} м",
        "en": "{i}h  +{part}/12 → {acc} m",
    },
    "marine_tide_header": {
        "ru": "🌊 <b>Высота воды через {hours} ч: {water} м</b>\n\n<pre>{rows}</pre>",
        "pl": "🌊 <b>Wysokość wody po {hours} h: {water} m</b>\n\n<pre>{rows}</pre>",
        "ua": "🌊 <b>Висота води через {hours} год: {water} м</b>\n\n<pre>{rows}</pre>",
        "en": "🌊 <b>Water height after {hours} h: {water} m</b>\n\n<pre>{rows}</pre>",
    },

    # ─────────────── результат из Mini App «Тесты» ───────────────
    "webapp_bad_read": {
        "ru": "Не удалось прочитать результат из приложения 🤷",
        "pl": "Nie udało się odczytać wyniku z aplikacji 🤷",
        "ua": "Не вдалося прочитати результат із застосунку 🤷",
        "en": "Couldn't read the result from the app 🤷",
    },
    "webapp_empty": {
        "ru": "Неизвестный или пустой результат из приложения.",
        "pl": "Nieznany lub pusty wynik z aplikacji.",
        "ua": "Невідомий або порожній результат із застосунку.",
        "en": "Unknown or empty result from the app.",
    },
    "webapp_time": {
        "ru": " · ⏱ {m}м {s}с",
        "pl": " · ⏱ {m}min {s}s",
        "ua": " · ⏱ {m}хв {s}с",
        "en": " · ⏱ {m}m {s}s",
    },
    "webapp_exam_head": {
        "ru": ("🏁 <b>Экзамен (приложение) завершён</b>\n"
               "Результат: <b>{correct}/{counted}</b> ({pct}%){tline}\n"
               "{verdict} (нужно ≥ {pass}%)"),
        "pl": ("🏁 <b>Egzamin (aplikacja) zakończony</b>\n"
               "Wynik: <b>{correct}/{counted}</b> ({pct}%){tline}\n"
               "{verdict} (potrzeba ≥ {pass}%)"),
        "ua": ("🏁 <b>Екзамен (застосунок) завершено</b>\n"
               "Результат: <b>{correct}/{counted}</b> ({pct}%){tline}\n"
               "{verdict} (потрібно ≥ {pass}%)"),
        "en": ("🏁 <b>Exam (app) finished</b>\n"
               "Score: <b>{correct}/{counted}</b> ({pct}%){tline}\n"
               "{verdict} (need ≥ {pass}%)"),
    },
    "random_label": {"ru": "случайные", "pl": "losowe", "ua": "випадкові", "en": "random"},
    "webapp_train_head": {
        "ru": ("🎯 <b>Тренировка (приложение): {label}</b>\n"
               "Результат: <b>{correct}/{counted}</b> ({pct}%)"),
        "pl": ("🎯 <b>Trening (aplikacja): {label}</b>\n"
               "Wynik: <b>{correct}/{counted}</b> ({pct}%)"),
        "ua": ("🎯 <b>Тренування (застосунок): {label}</b>\n"
               "Результат: <b>{correct}/{counted}</b> ({pct}%)"),
        "en": ("🎯 <b>Practice (app): {label}</b>\n"
               "Score: <b>{correct}/{counted}</b> ({pct}%)"),
    },
    "webapp_no_errors": {
        "ru": "🎉 Без ошибок! Результат сохранён.",
        "pl": "🎉 Bez błędów! Wynik zapisany.",
        "ua": "🎉 Без помилок! Результат збережено.",
        "en": "🎉 No errors! Result saved.",
    },

    # ─────────────── прочее ───────────────
    "not_understood_menu": {
        "ru": "Не понял. Откройте меню: /menu",
        "pl": "Nie zrozumiałem. Otwórz menu: /menu",
        "ua": "Не зрозумів. Відкрийте меню: /menu",
        "en": "Didn't get it. Open the menu: /menu",
    },
}
