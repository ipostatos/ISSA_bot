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
    bookDownload:{ ru: "Скачать", pl: "Pobierz", ua: "Завантажити", en: "Download" }
  };

  return { LANGS: LANGS, DICT: DICT };
});
