// ДНЕВНЫЕ ФИГУРЫ (COLREG, правило 30 и др.) + СИГНАЛЬНЫЕ ФЛАГИ МСС.
// База для тренажёра «Фигуры и флаги»: справочник + тест «что означает?».
//
// Дневные фигуры: чёрные фигуры, поднимаемые днём вместо огней. figures —
// список СВЕРХУ ВНИЗ: ball | diamond | cone-up | cone-down | cones-apex |
// cylinder (cones-apex — два конуса вершинами вместе, «песочные часы»).
// В банке Sternik эти же фигуры спрашиваются текстом (st-439…st-445) —
// тренажёр даёт им зрительный образ.
//
// Флаги МСС: однофлажные сигналы, которые реально спрашивают на экзаменах и
// которые обязан знать шкипер (A — водолаз, B — опасный груз, O — человек за
// бортом…). draw — декларативный рисунок: renderer в shapes.html понимает
// перечисленные kind'ы. swallowtail — флаг с косицами (A, B).
//
// Источники: COLREG (МППСС-72) Part C/D, Международный свод сигналов (МСС).
// Учебный материал — не заменяет официальные издания.
window.SHAPES_DATA = {
  version: 1,

  dayshapes: [
    { key: "anchor", title: "Шар",
      figures: ["ball"],
      meaning: "Судно на якоре",
      note: "Правило 30. Один чёрный шар в носовой части. Ночью — якорный огонь." },
    { key: "nuc", title: "Два шара по вертикали",
      figures: ["ball", "ball"],
      meaning: "Судно, лишённое возможности управляться (NUC)",
      note: "Правило 27(a). Ночью — два красных огня по вертикали." },
    { key: "aground", title: "Три шара по вертикали",
      figures: ["ball", "ball", "ball"],
      meaning: "Судно на мели",
      note: "Правило 30(d). Якорные шары + ещё: на мели поднимают ТРИ шара." },
    { key: "ram", title: "Шар — ромб — шар",
      figures: ["ball", "diamond", "ball"],
      meaning: "Судно, ограниченное в возможности маневрировать (RAM)",
      note: "Правило 27(b): дноуглубление, водолазные, кабельные работы. Ночью — красный/белый/красный." },
    { key: "motorsailing", title: "Конус вершиной вниз",
      figures: ["cone-down"],
      meaning: "Судно под парусом, идущее одновременно под двигателем",
      note: "Правило 25(e). Паруса подняты + мотор работает → конус вершиной ВНИЗ в носовой части." },
    { key: "fishing", title: "Два конуса вершинами вместе",
      figures: ["cones-apex"],
      meaning: "Судно, занятое ловом рыбы (в т.ч. трал)",
      note: "Правило 26. «Песочные часы» из двух конусов. Ночью: зелёный/белый (трал) или красный/белый (прочий лов)." },
    { key: "cbd", title: "Цилиндр",
      figures: ["cylinder"],
      meaning: "Судно, стеснённое своей осадкой (CBD)",
      note: "Правило 28. Чёрный цилиндр. Ночью — три красных огня по вертикали." },
    { key: "tow", title: "Ромб",
      figures: ["diamond"],
      meaning: "Буксируемый объект (длина буксира больше 200 м)",
      note: "Правило 24. Ромб и на буксировщике, и на буксируемом, когда буксир > 200 м." },
  ],

  flags: [
    { key: "A", name: "Alfa",
      meaning: "У меня спущен водолаз; держитесь в стороне на малом ходу",
      draw: { shape: "swallowtail", kind: "vsplit", colors: ["#ffffff", "#1948a8"] } },
    { key: "B", name: "Bravo",
      meaning: "Гружу / выгружаю / имею на борту опасный груз",
      draw: { shape: "swallowtail", kind: "solid", colors: ["#d22d2d"] } },
    { key: "C", name: "Charlie",
      meaning: "«Да» (утвердительный)",
      draw: { shape: "rect", kind: "hstripes", colors: ["#1948a8", "#ffffff", "#d22d2d", "#ffffff", "#1948a8"] } },
    { key: "G", name: "Golf",
      meaning: "Мне нужен лоцман",
      draw: { shape: "rect", kind: "vstripes", colors: ["#f2c327", "#1948a8", "#f2c327", "#1948a8", "#f2c327", "#1948a8"] } },
    { key: "H", name: "Hotel",
      meaning: "У меня на борту лоцман",
      draw: { shape: "rect", kind: "vsplit", colors: ["#ffffff", "#d22d2d"] } },
    { key: "N", name: "November",
      meaning: "«Нет» (отрицательный)",
      draw: { shape: "rect", kind: "checker", colors: ["#1948a8", "#ffffff"], n: 4 } },
    { key: "O", name: "Oscar",
      meaning: "Человек за бортом!",
      draw: { shape: "rect", kind: "diag", colors: ["#d22d2d", "#f2c327"] } },
    { key: "P", name: "Papa («Blue Peter»)",
      meaning: "Всем быть на борту: судно скоро снимается",
      draw: { shape: "rect", kind: "center-rect", colors: ["#1948a8", "#ffffff"] } },
    { key: "Q", name: "Quebec",
      meaning: "Моё судно не заражено, прошу свободную практику (карантинный)",
      draw: { shape: "rect", kind: "solid", colors: ["#f2c327"] } },
    { key: "V", name: "Victor",
      meaning: "Мне необходима помощь",
      draw: { shape: "rect", kind: "saltire", colors: ["#ffffff", "#d22d2d"] } },
    { key: "W", name: "Whiskey",
      meaning: "Мне необходима медицинская помощь",
      draw: { shape: "rect", kind: "nested", colors: ["#1948a8", "#ffffff", "#d22d2d"] } },
    { key: "NC", name: "N над C",
      meaning: "Терплю бедствие, нужна немедленная помощь",
      draw: { shape: "double", kind: "nc", colors: [] } },
  ],
};
