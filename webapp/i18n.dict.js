// ===========================================================================
// I18N DICT — словарь интерфейса ISSA Trainer (RU / PL / UA / EN).
// Только UI-строки (кнопки, меню, подписи). Учебный контент (вопросы, конспект)
// не переводится. Подключать ПЕРЕД i18n.js. Ключи добавляются по мере миграции
// страниц; каждый ключ обязан иметь все 4 языка (проверяется webapp/_i18n_check.mjs).
// ===========================================================================
(function (root, factory) {
  "use strict";
  var dict = factory();
  if (typeof module === "object" && module.exports) module.exports = dict;
  else root.ISSA_I18N = dict;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var LANGS = [
    { code: "ru", label: "Русский",    flag: "🇷🇺" },
    { code: "pl", label: "Polski",     flag: "🇵🇱" },
    { code: "ua", label: "Українська", flag: "🇺🇦" },
    { code: "en", label: "English",    flag: "🇬🇧" }
  ];

  var DICT = {
    /* ── общее / чрезстраничное ── */
    langBtn:   { ru: "Язык", pl: "Język", ua: "Мова", en: "Language" },
    back:      { ru: "Назад", pl: "Wstecz", ua: "Назад", en: "Back" },
    home:      { ru: "На главную", pl: "Strona główna", ua: "На головну", en: "Home" },

    /* ── home: шапка и приоритетный блок ── */
    homeSub:   { ru: "Подготовка к экзамену Inshore Skipper + SRC", pl: "Przygotowanie do egzaminu Inshore Skipper + SRC", ua: "Підготовка до іспиту Inshore Skipper + SRC", en: "Prep for the Inshore Skipper + SRC exam" },
    nextStart: { ru: "С чего начать", pl: "Od czego zacząć", ua: "З чого почати", en: "Where to start" },
    nextTrain: { ru: "Тренировка и экзамен", pl: "Trening i egzamin", ua: "Тренування та іспит", en: "Practice & exam" },
    nextHint:  { ru: "{n} вопросов · перемешанные варианты · разбор и источники", pl: "{n} pytań · losowa kolejność odpowiedzi · wyjaśnienia i źródła", ua: "{n} питань · перемішані варіанти · розбір і джерела", en: "{n} questions · shuffled options · explanations & sources" },
    btnStart:  { ru: "Начать", pl: "Zacznij", ua: "Почати", en: "Start" },
    btnTheory: { ru: "Теория", pl: "Teoria", ua: "Теорія", en: "Theory" },

    /* ── home: динамика приоритетного блока (SRS) ── */
    dueLabel:  { ru: "Пора повторить", pl: "Czas na powtórkę", ua: "Час повторити", en: "Time to review" },
    dueTitle:  { ru: "{n} к повторению", pl: "{n} do powtórki", ua: "{n} до повторення", en: "{n} to review" },
    dueHint:   { ru: "Интервальное повторение · закреплено {done} из {total}", pl: "Powtórki interwałowe · utrwalono {done} z {total}", ua: "Інтервальне повторення · закріплено {done} з {total}", en: "Spaced repetition · {done} of {total} mastered" },
    btnReview: { ru: "Повторить", pl: "Powtórz", ua: "Повторити", en: "Review" },
    keepUp:    { ru: "Так держать", pl: "Tak trzymaj", ua: "Так тримати", en: "Keep it up" },
    allDone:   { ru: "На сегодня всё повторено · закреплено {done} из {total}", pl: "Na dziś wszystko powtórzone · utrwalono {done} z {total}", ua: "На сьогодні все повторено · закріплено {done} з {total}", en: "All reviewed for today · {done} of {total} mastered" },

    /* ── home: готовность ── */
    readyIssa: { ru: "Готовность · ISSA", pl: "Gotowość · ISSA", ua: "Готовність · ISSA", en: "Readiness · ISSA" },
    readyOf:   { ru: "Готовность · {title}", pl: "Gotowość · {title}", ua: "Готовність · {title}", en: "Readiness · {title}" },
    lblToday:  { ru: "Сегодня", pl: "Dziś", ua: "Сьогодні", en: "Today" },
    lblStreak: { ru: "Серия", pl: "Seria", ua: "Серія", en: "Streak" },
    lblBest:   { ru: "Рекорд", pl: "Rekord", ua: "Рекорд", en: "Best" },
    weakTop:   { ru: "Слабее всего: {list}", pl: "Najsłabsze: {list}", ua: "Найслабші: {list}", en: "Weakest: {list}" },
    noWeak:    { ru: "Слабых тем нет — отличная база!", pl: "Brak słabych tematów — świetna baza!", ua: "Слабких тем немає — чудова база!", en: "No weak topics — great foundation!" },
    lblLearned:{ ru: "Изучено", pl: "Nauczone", ua: "Вивчено", en: "Learned" },
    lblBestExam:{ ru: "Лучший экз.", pl: "Najlepszy egz.", ua: "Кращий іспит", en: "Best exam" },
    lblThreshold:{ ru: "Порог", pl: "Próg", ua: "Поріг", en: "Pass" },
    openTrainer:{ ru: "Открыть тренажёр →", pl: "Otwórz trener →", ua: "Відкрити тренажер →", en: "Open trainer →" },

    /* ── home: план к дате экзамена ── */
    setExamDate:{ ru: "Задать дату экзамена", pl: "Ustaw datę egzaminu", ua: "Задати дату іспиту", en: "Set exam date" },
    examOn:    { ru: "Экзамен {date} — {left}", pl: "Egzamin {date} — {left}", ua: "Іспит {date} — {left}", en: "Exam {date} — {left}" },
    examToday: { ru: "сегодня!", pl: "dziś!", ua: "сьогодні!", en: "today!" },
    daysLeft:  { ru: "осталось {n} дн.", pl: "zostało {n} dni", ua: "залишилось {n} дн.", en: "{n} days left" },
    bankReady: { ru: "банк закреплён", pl: "baza utrwalona", ua: "банк закріплено", en: "bank mastered" },
    needPerDay:{ ru: "нужно ~{n} отв./день", pl: "trzeba ~{n} odp./dzień", ua: "потрібно ~{n} відп./день", en: "~{n} answers/day" },
    raiseGoal: { ru: "(цель {g} — подними её)", pl: "(cel {g} — podnieś go)", ua: "(ціль {g} — підніми її)", en: "(goal {g} — raise it)" },

    /* ── home: секции и плитки ── */
    activity:  { ru: "Активность", pl: "Aktywność", ua: "Активність", en: "Activity" },
    secPractice:{ ru: "Практика", pl: "Praktyka", ua: "Практика", en: "Practice" },
    secTheory: { ru: "Теория и справка", pl: "Teoria i pomoc", ua: "Теорія та довідка", en: "Theory & reference" },
    secBonus:  { ru: "Бонус · интерактив", pl: "Bonus · interaktyw", ua: "Бонус · інтерактив", en: "Bonus · interactive" },
    cQuizT:    { ru: "Тесты ISSA", pl: "Testy ISSA", ua: "Тести ISSA", en: "ISSA tests" },
    cQuizD:    { ru: "Темы и экзамен, таймер, разбор", pl: "Tematy i egzamin, timer, wyjaśnienia", ua: "Теми та іспит, таймер, розбір", en: "Topics & exam, timer, review" },
    cPlT:      { ru: "Лицензии PL", pl: "Licencje PL", ua: "Ліцензії PL", en: "PL licences" },
    cPlD:      { ru: "Żeglarz + Sternik · экзамен 75/65", pl: "Żeglarz + Sternik · egzamin 75/65", ua: "Żeglarz + Sternik · іспит 75/65", en: "Żeglarz + Sternik · exam 75/65" },
    cTasksT:   { ru: "Задачки", pl: "Zadania", ua: "Задачі", en: "Problems" },
    cTasksD:   { ru: "Скорость·время·ETA, приливы", pl: "Prędkość·czas·ETA, pływy", ua: "Швидкість·час·ETA, припливи", en: "Speed·time·ETA, tides" },
    cNavT:     { ru: "T-V-M-D-C", pl: "T-V-M-D-C", ua: "T-V-M-D-C", en: "T-V-M-D-C" },
    cNavD:     { ru: "50 задач на поправки компаса", pl: "50 zadań na poprawki kompasu", ua: "50 задач на поправки компаса", en: "50 compass-correction tasks" },
    cCalcT:    { ru: "Калькулятор", pl: "Kalkulator", ua: "Калькулятор", en: "Calculator" },
    cCalcD:    { ru: "TVMDC и S·D·T·ETA", pl: "TVMDC oraz S·D·T·ETA", ua: "TVMDC та S·D·T·ETA", en: "TVMDC and S·D·T·ETA" },
    cWeatherT: { ru: "Погода", pl: "Pogoda", ua: "Погода", en: "Weather" },
    cWeatherD: { ru: "Ветер и волна по точке", pl: "Wiatr i fala w punkcie", ua: "Вітер і хвиля в точці", en: "Wind & waves by point" },
    cKonspektT:{ ru: "Конспект", pl: "Konspekt", ua: "Конспект", en: "Notes" },
    cKonspektD:{ ru: "16 тем по учебнику ISSA", pl: "16 tematów wg podręcznika ISSA", ua: "16 тем за підручником ISSA", en: "16 topics from the ISSA book" },
    cCheatT:   { ru: "Шпаргалки", pl: "Ściągi", ua: "Шпаргалки", en: "Cheat sheets" },
    cCheatD:   { ru: "МППСС, огни, IALA, узлы…", pl: "COLREG, światła, IALA, węzły…", ua: "МПЗЗС, вогні, IALA, вузли…", en: "COLREG, lights, IALA, knots…" },
    cGlossaryT:{ ru: "Словарь", pl: "Słownik", ua: "Словник", en: "Glossary" },
    cGlossaryD:{ ru: "180+ терминов с поиском", pl: "180+ terminów z wyszukiwarką", ua: "180+ термінів з пошуком", en: "180+ terms, searchable" },
    cBookT:    { ru: "Библиотека", pl: "Biblioteka", ua: "Бібліотека", en: "Library" },
    cBookD:    { ru: "Учебники целиком (PDF)", pl: "Pełne podręczniki (PDF)", ua: "Підручники повністю (PDF)", en: "Full textbooks (PDF)" },
    cAudioT:   { ru: "Аудио-повторение 🎧", pl: "Powtórka audio 🎧", ua: "Аудіо-повторення 🎧", en: "Audio review 🎧" },
    cAudioD:   { ru: "Вопросы на слух — в дорогу", pl: "Pytania ze słuchu — w drogę", ua: "Питання на слух — у дорогу", en: "Questions by ear — on the go" },
    cLightsT:  { ru: "Огни судов 🚢", pl: "Światła statków 🚢", ua: "Вогні суден 🚢", en: "Ship lights 🚢" },
    cLightsD:  { ru: "Распознавание ночью · COLREG", pl: "Rozpoznawanie nocą · COLREG", ua: "Розпізнавання вночі · COLREG", en: "Night recognition · COLREG" },
    cBuoysT:   { ru: "Буи IALA 🔆", pl: "Boje IALA 🔆", ua: "Буї IALA 🔆", en: "IALA buoys 🔆" },
    cBuoysD:   { ru: "Знаки и проблески · куда обходить", pl: "Znaki i błyski · z której strony", ua: "Знаки та проблиски · куди обходити", en: "Marks & flashes · which side" },
    cShapesT:  { ru: "Фигуры и флаги ⚑", pl: "Znaki i flagi ⚑", ua: "Фігури та прапори ⚑", en: "Shapes & flags ⚑" },
    cShapesD:  { ru: "Дневные фигуры COLREG · флаги МСС", pl: "Znaki dzienne COLREG · flagi MKS", ua: "Денні фігури COLREG · прапори МЗС", en: "COLREG day shapes · ICS flags" },
    cProfileT: { ru: "Профиль и достижения", pl: "Profil i osiągnięcia", ua: "Профіль і досягнення", en: "Profile & achievements" },
    cProfileD: { ru: "Звания, бейджи, прогресс", pl: "Rangi, odznaki, postęp", ua: "Звання, бейджі, прогрес", en: "Ranks, badges, progress" },
    achOf:     { ru: "Достижения: {n} из {tot} · звания, бейджи", pl: "Osiągnięcia: {n} z {tot} · rangi, odznaki", ua: "Досягнення: {n} з {tot} · звання, бейджі", en: "Achievements: {n} of {tot} · ranks, badges" },
    cHistoryT: { ru: "История прохождений", pl: "Historia podejść", ua: "Історія проходжень", en: "Session history" },
    cHistoryD: { ru: "Все тесты и экзамены, динамика результатов", pl: "Wszystkie testy i egzaminy, dynamika wyników", ua: "Усі тести та іспити, динаміка результатів", en: "All tests & exams, result trends" },
    cAboutT:   { ru: "О банке вопросов", pl: "O bazie pytań", ua: "Про банк питань", en: "About the question bank" },
    cAboutD:   { ru: "Источники, проверка, состав — прозрачно", pl: "Źródła, weryfikacja, skład — przejrzyście", ua: "Джерела, перевірка, склад — прозоро", en: "Sources, checks, contents — transparent" },
    homeFoot:  { ru: "Учебный тренажёр. Не является официальным материалом ISSA и не содержит экзаменационных ключей.", pl: "Trener edukacyjny. Nie jest oficjalnym materiałem ISSA i nie zawiera kluczy egzaminacyjnych.", ua: "Навчальний тренажер. Не є офіційним матеріалом ISSA і не містить екзаменаційних ключів.", en: "A study trainer. Not official ISSA material and contains no exam answer keys." },

    /* ── prompt/alert (нативные диалоги) ── */
    promptGoal:{ ru: "Дневная цель — сколько вопросов в день? (5–100)", pl: "Cel dzienny — ile pytań dziennie? (5–100)", ua: "Денна ціль — скільки питань на день? (5–100)", en: "Daily goal — how many questions per day? (5–100)" },
    promptDate:{ ru: "Дата экзамена (ГГГГ-ММ-ДД), пусто — убрать:", pl: "Data egzaminu (RRRR-MM-DD), pusto — usuń:", ua: "Дата іспиту (РРРР-ММ-ДД), пусто — прибрати:", en: "Exam date (YYYY-MM-DD), empty — remove:" },
    badDate:   { ru: "Формат: ГГГГ-ММ-ДД, например 2026-08-15", pl: "Format: RRRR-MM-DD, np. 2026-08-15", ua: "Формат: РРРР-ММ-ДД, напр. 2026-08-15", en: "Format: YYYY-MM-DD, e.g. 2026-08-15" },

    /* ── profile.html ── */
    pTitle:    { ru: "Профиль", pl: "Profil", ua: "Профіль", en: "Profile" },
    pReady:    { ru: "готовность", pl: "gotowość", ua: "готовність", en: "readiness" },
    pStreak:   { ru: "серия", pl: "seria", ua: "серія", en: "streak" },
    pBadges:   { ru: "бейджей", pl: "odznak", ua: "бейджів", en: "badges" },
    pAch:      { ru: "Достижения", pl: "Osiągnięcia", ua: "Досягнення", en: "Achievements" },
    pFoot:     { ru: "Достижения считаются из вашей активности на этом устройстве и синхронизируются между устройствами.", pl: "Osiągnięcia liczone są z Twojej aktywności na tym urządzeniu i synchronizują się między urządzeniami.", ua: "Досягнення рахуються з вашої активності на цьому пристрої й синхронізуються між пристроями.", en: "Achievements are computed from your activity on this device and sync across devices." },
    pOpenedOf: { ru: "Открыто {n} из {tot} достижений", pl: "Odblokowano {n} z {tot} osiągnięć", ua: "Відкрито {n} з {tot} досягнень", en: "{n} of {tot} achievements unlocked" },
    rankCaptain:{ ru: "Капитан", pl: "Kapitan", ua: "Капітан", en: "Captain" },
    rankSkipper:{ ru: "Шкипер", pl: "Skiper", ua: "Шкіпер", en: "Skipper" },
    rankNav:   { ru: "Штурман", pl: "Nawigator", ua: "Штурман", en: "Navigator" },
    rankSailor:{ ru: "Матрос", pl: "Marynarz", ua: "Матрос", en: "Sailor" },
    rankCabin: { ru: "Юнга", pl: "Junga", ua: "Юнга", en: "Cabin boy" },

    /* ── glossary.html ── */
    glossTitle:  { ru: "Словарь яхтсмена", pl: "Słownik żeglarski", ua: "Словник яхтсмена", en: "Sailor's glossary" },
    glossSearch: { ru: "Термин по-русски / English…", pl: "Termin po polsku / English…", ua: "Термін українською / English…", en: "Term in English…" },
    glossFoot:   { ru: "Учебный словарь простыми словами. Не является официальным материалом ISSA.", pl: "Słownik edukacyjny prostymi słowami. Nie jest oficjalnym materiałem ISSA.", ua: "Навчальний словник простими словами. Не є офіційним матеріалом ISSA.", en: "A plain-language study glossary. Not official ISSA material." },
    glossAll:    { ru: "Все", pl: "Wszystkie", ua: "Усі", en: "All" },
    glossShown:  { ru: "Показано: {n}", pl: "Pokazano: {n}", ua: "Показано: {n}", en: "Shown: {n}" },
    glossNone:   { ru: "Ничего не найдено.", pl: "Nic nie znaleziono.", ua: "Нічого не знайдено.", en: "Nothing found." },
    glossNoneQ:  { ru: "Ничего не найдено по «{q}».", pl: "Nic nie znaleziono dla „{q}”.", ua: "Нічого не знайдено за «{q}».", en: "Nothing found for “{q}”." },
    glossLoadFail:{ ru: "Не удалось загрузить словарь.", pl: "Nie udało się załadować słownika.", ua: "Не вдалося завантажити словник.", en: "Couldn't load the glossary." },

    /* ── cheatsheet.html ── */
    cheatTitle:  { ru: "Шпаргалки", pl: "Ściągi", ua: "Шпаргалки", en: "Cheat sheets" },
    cheatFoot:   { ru: "Учебные выжимки. Не является официальным материалом ISSA.", pl: "Edukacyjne wyciągi. Nie jest oficjalnym materiałem ISSA.", ua: "Навчальні витяги. Не є офіційним матеріалом ISSA.", en: "Study summaries. Not official ISSA material." },
    cheatFootR:  { ru: "Учебные выжимки.", pl: "Edukacyjne wyciągi.", ua: "Навчальні витяги.", en: "Study summaries." },
    cheatLoadFail:{ ru: "Не удалось загрузить шпаргалки.", pl: "Nie udało się załadować ściąg.", ua: "Не вдалося завантажити шпаргалки.", en: "Couldn't load the cheat sheets." },
    step:        { ru: "шаг {n}", pl: "krok {n}", ua: "крок {n}", en: "step {n}" },

    /* ── book.html ── */
    bookTitle:   { ru: "Библиотека", pl: "Biblioteka", ua: "Бібліотека", en: "Library" },
    bookSub:     { ru: "Учебники и пособия по яхтингу", pl: "Podręczniki i materiały żeglarskie", ua: "Підручники та посібники з яхтингу", en: "Yachting textbooks and guides" },
    bookFoot:    { ru: "«Открыть» — чтение прямо в приложении (листание и зум). «Скачать» — сохранить файл. Авторские права принадлежат правообладателям.", pl: "„Otwórz” — czytanie w aplikacji (przewijanie i zoom). „Pobierz” — zapis pliku. Prawa autorskie należą do właścicieli.", ua: "«Відкрити» — читання просто в застосунку (гортання і зум). «Завантажити» — зберегти файл. Авторські права належать правовласникам.", en: "“Open” reads it inside the app (swipe & zoom). “Download” saves the file. Copyrights belong to their owners." },
    bookOpen:    { ru: "Открыть", pl: "Otwórz", ua: "Відкрити", en: "Open" },
    bookDownload:{ ru: "Скачать", pl: "Pobierz", ua: "Завантажити", en: "Download" },

    /* ── общий футер учебного тренажёра (переиспользуется) ── */
    footTrainer:{ ru: "Учебный тренажёр. Не является официальным материалом ISSA.", pl: "Trener edukacyjny. Nie jest oficjalnym materiałem ISSA.", ua: "Навчальний тренажер. Не є офіційним матеріалом ISSA.", en: "A study trainer. Not official ISSA material." },

    /* ── tasks.html ── */
    taskTitle:  { ru: "Задачки", pl: "Zadania", ua: "Задачі", en: "Problems" },
    taskCat:    { ru: "Навигация и приливы", pl: "Nawigacja i pływy", ua: "Навігація і припливи", en: "Navigation & tides" },
    taskStreak: { ru: "серия: {n}", pl: "seria: {n}", ua: "серія: {n}", en: "streak: {n}" },
    taskSpeed:  { ru: "Скорость/ETA", pl: "Prędkość/ETA", ua: "Швидкість/ETA", en: "Speed/ETA" },
    taskTide:   { ru: "Прилив", pl: "Pływ", ua: "Приплив", en: "Tide" },
    taskPh:     { ru: "ответ числом", pl: "odpowiedź liczbą", ua: "відповідь числом", en: "answer as a number" },
    taskSolve:  { ru: "Решение", pl: "Rozwiązanie", ua: "Розв'язання", en: "Solution" },
    taskNext:   { ru: "Новая →", pl: "Nowe →", ua: "Нова →", en: "New →" },
    taskEmpty:  { ru: "В этой категории задач нет.", pl: "W tej kategorii nie ma zadań.", ua: "У цій категорії задач немає.", en: "No problems in this category." },
    taskLoadFail:{ ru: "Не удалось загрузить задачи.", pl: "Nie udało się załadować zadań.", ua: "Не вдалося завантажити задачі.", en: "Couldn't load the problems." },
    taskNaN:    { ru: "Введи ответ числом.", pl: "Wpisz odpowiedź liczbą.", ua: "Введи відповідь числом.", en: "Enter the answer as a number." },
    taskCorrect:{ ru: "Верно! Ответ {a} {unit}.", pl: "Dobrze! Odpowiedź {a} {unit}.", ua: "Правильно! Відповідь {a} {unit}.", en: "Correct! Answer {a} {unit}." },
    taskWrong:  { ru: "Не то. Нажми «Решение» и попробуй разобраться.", pl: "Nie to. Kliknij „Rozwiązanie” i spróbuj zrozumieć.", ua: "Не те. Натисни «Розв'язання» і спробуй розібратися.", en: "Not quite. Tap “Solution” and work it through." },

    /* ── shapes.html (фигуры и флаги) ── */
    shapeTitle:   { ru: "Фигуры и флаги", pl: "Kształty i flagi", ua: "Фігури і прапори", en: "Shapes & flags" },
    shapeSub:     { ru: "Дневные фигуры COLREG + однофлажные сигналы МСС", pl: "Znaki dzienne COLREG + jednoflagowe sygnały MKS", ua: "Денні фігури COLREG + однофлажні сигнали МСС", en: "COLREG day shapes + single-flag ICS signals" },
    shapeDay:     { ru: "Дневные фигуры", pl: "Znaki dzienne", ua: "Денні фігури", en: "Day shapes" },
    shapeDaySub:  { ru: "Шары, конусы, ромб, цилиндр — что несёт судно днём", pl: "Kule, stożki, romb, walec — co statek nosi w dzień", ua: "Кулі, конуси, ромб, циліндр — що несе судно вдень", en: "Balls, cones, diamond, cylinder — what a vessel shows by day" },
    shapeFlags:   { ru: "Флаги МСС", pl: "Flagi MKS", ua: "Прапори МСС", en: "ICS flags" },
    shapeFlagsSub:{ ru: "A — водолаз, B — опасный груз, O — человек за бортом…", pl: "A — nurek, B — ładunek niebezpieczny, O — człowiek za burtą…", ua: "A — водолаз, B — небезпечний вантаж, O — людина за бортом…", en: "A — diver, B — dangerous cargo, O — man overboard…" },
    shapeQuiz:    { ru: "Тест", pl: "Test", ua: "Тест", en: "Quiz" },
    shapeQuizSub: { ru: "Фигуры и флаги вперемешку — что означает?", pl: "Kształty i flagi na przemian — co oznacza?", ua: "Фігури і прапори впереміш — що означає?", en: "Shapes and flags mixed — what does it mean?" },
    shapeMenu:    { ru: "← Меню", pl: "← Menu", ua: "← Меню", en: "← Menu" },
    shapeList:    { ru: "← Список", pl: "← Lista", ua: "← Список", en: "← List" },
    shapeWhat:    { ru: "Что означает?", pl: "Co oznacza?", ua: "Що означає?", en: "What does it mean?" },
    shapeNext:    { ru: "Следующий →", pl: "Następny →", ua: "Наступний →", en: "Next →" },
    shapeResult:  { ru: "Результат: {ok} / {n}", pl: "Wynik: {ok} / {n}", ua: "Результат: {ok} / {n}", en: "Score: {ok} / {n}" },
    shapeDone:    { ru: "Тест завершён!", pl: "Test zakończony!", ua: "Тест завершено!", en: "Quiz complete!" },

    /* ── audio.html (аудио-повторение) ── */
    audTitle:     { ru: "Аудио-повторение", pl: "Powtórka audio", ua: "Аудіо-повторення", en: "Audio review" },
    audSub:       { ru: "Вопросы и ответы на слух — повторяй в дороге, у штурвала, на пробежке", pl: "Pytania i odpowiedzi na słuch — powtarzaj w drodze, przy sterze, na biegu", ua: "Питання й відповіді на слух — повторюй у дорозі, за штурвалом, на пробіжці", en: "Questions and answers by ear — review on the go, at the helm, on a run" },
    audNoSupport: { ru: "Синтез речи не поддерживается этим клиентом Telegram. Открой Mini App на другом устройстве или обнови приложение.", pl: "Synteza mowy nie jest obsługiwana przez tego klienta Telegram. Otwórz Mini App na innym urządzeniu lub zaktualizuj aplikację.", ua: "Синтез мовлення не підтримується цим клієнтом Telegram. Відкрий Mini App на іншому пристрої або онови застосунок.", en: "Speech synthesis isn't supported by this Telegram client. Open the Mini App on another device or update the app." },
    audWeak:      { ru: "Слабые вопросы ISSA", pl: "Słabe pytania ISSA", ua: "Слабкі питання ISSA", en: "Weak ISSA questions" },
    audBySchedule:{ ru: "по расписанию повторения", pl: "według harmonogramu powtórek", ua: "за розкладом повторення", en: "on the review schedule" },
    audPlSub:     { ru: "польские формулировки + перевод", pl: "polskie sformułowania + tłumaczenie", ua: "польські формулювання + переклад", en: "Polish wording + translation" },
    audNowDefault:{ ru: "Выбери источник и нажми ▶ — вопрос прозвучит, затем правильный ответ.", pl: "Wybierz źródło i naciśnij ▶ — zabrzmi pytanie, potem prawidłowa odpowiedź.", ua: "Обери джерело й натисни ▶ — прозвучить питання, потім правильна відповідь.", en: "Pick a source and press ▶ — the question plays, then the correct answer." },
    audPrev:      { ru: "Назад", pl: "Wstecz", ua: "Назад", en: "Back" },
    audNext:      { ru: "Дальше", pl: "Dalej", ua: "Далі", en: "Next" },
    audScreenNote:{ ru: "Не выключай экран: синтез речи живёт в открытой странице Mini App.", pl: "Nie wyłączaj ekranu: synteza mowy działa tylko przy otwartej stronie Mini App.", ua: "Не вимикай екран: синтез мовлення живе у відкритій сторінці Mini App.", en: "Keep the screen on: speech runs only while the Mini App page is open." },
    audEmpty:     { ru: "Плейлист пуст.", pl: "Playlista jest pusta.", ua: "Плейлист порожній.", en: "Playlist is empty." },
    audDueCount:  { ru: "{n} к повторению", pl: "{n} do powtórki", ua: "{n} до повторення", en: "{n} to review" },

    /* ── history.html (прогресс и история) ── */
    histTitle:    { ru: "История", pl: "Historia", ua: "Історія", en: "History" },
    histH1:       { ru: "Прогресс и история", pl: "Postępy i historia", ua: "Прогрес та історія", en: "Progress & history" },
    histSub:      { ru: "Динамика, слабые темы и все прохождения", pl: "Dynamika, słabe tematy i wszystkie podejścia", ua: "Динаміка, слабкі теми й усі проходження", en: "Trends, weak topics and every attempt" },
    histTotal:    { ru: "всего", pl: "razem", ua: "усього", en: "total" },
    histAvgExam:  { ru: "ср. экзамен", pl: "śr. egzamin", ua: "сер. екзамен", en: "avg exam" },
    histBest:     { ru: "лучший", pl: "najlepszy", ua: "найкращий", en: "best" },
    histTrend:    { ru: "Динамика результатов", pl: "Dynamika wyników", ua: "Динаміка результатів", en: "Score trend" },
    histWeakH:    { ru: "Слабые темы — стоит повторить", pl: "Słabe tematy — warto powtórzyć", ua: "Слабкі теми — варто повторити", en: "Weak topics — worth reviewing" },
    histAll:      { ru: "Все прохождения", pl: "Wszystkie podejścia", ua: "Усі проходження", en: "All attempts" },
    histLoading:  { ru: "Загрузка…", pl: "Ładowanie…", ua: "Завантаження…", en: "Loading…" },
    modeExam:     { ru: "Экзамен", pl: "Egzamin", ua: "Екзамен", en: "Exam" },
    modeReview:   { ru: "Повторение", pl: "Powtórka", ua: "Повторення", en: "Review" },
    modeTrain:    { ru: "Тренировка", pl: "Trening", ua: "Тренування", en: "Practice" },
    modeTopic:    { ru: "Тема: {t}", pl: "Temat: {t}", ua: "Тема: {t}", en: "Topic: {t}" },
    histRevTitle: { ru: "Повторить сегодня", pl: "Powtórz dziś", ua: "Повторити сьогодні", en: "Review today" },
    histRevSub:   { ru: "{n} к повторению", pl: "{n} do powtórki", ua: "{n} до повторення", en: "{n} to review" },
    histTopicTitle:{ ru: "Подтянуть: {t}", pl: "Podciągnij: {t}", ua: "Підтягнути: {t}", en: "Brush up: {t}" },
    histTopicSub: { ru: "Готовность темы {p}%", pl: "Gotowość tematu {p}%", ua: "Готовність теми {p}%", en: "Topic readiness {p}%" },
    histAllGood:  { ru: "Всё в форме!", pl: "Wszystko w formie!", ua: "Все у формі!", en: "All in shape!" },
    histAllGoodSub:{ ru: "Слабых тем нет — так держать", pl: "Brak słabych tematów — tak trzymać", ua: "Слабких тем немає — так тримати", en: "No weak topics — keep it up" },
    histEmpty:    { ru: "Пока нет завершённых тестов.<br>Пройди тренировку или экзамен — здесь появится история.", pl: "Brak ukończonych testów.<br>Zrób trening lub egzamin — tu pojawi się historia.", ua: "Поки немає завершених тестів.<br>Пройди тренування або екзамен — тут з'явиться історія.", en: "No completed tests yet.<br>Take a practice or exam — history will appear here." },
    histSyncNote: { ru: "История прохождений синхронизируется при открытии из Telegram. Слабые темы и рекомендации доступны и так.", pl: "Historia podejść synchronizuje się po otwarciu z Telegrama. Słabe tematy i rekomendacje są dostępne i tak.", ua: "Історія проходжень синхронізується при відкритті з Telegram. Слабкі теми й рекомендації доступні й так.", en: "Attempt history syncs when opened from Telegram. Weak topics and tips are available regardless." },
    hMin:         { ru: "м", pl: "min", ua: "хв", en: "m" },
    hSec:         { ru: "с", pl: "s", ua: "с", en: "s" }
  };

  return { LANGS: LANGS, DICT: DICT };
});
