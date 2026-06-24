"""Тесты решателя задач T-V-M-D-C, включая границу 0°/360°."""
import importlib.util
import sys
from pathlib import Path

BASE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("nav_tasks", BASE / "nav_tasks.py")
nt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nt)

fails = []


def t(name, cond):
    if not cond:
        fails.append(name)


# угловой допуск вокруг 0/360
t("answer 359 принимает 0", nt.NavTask("x", "", 359, "").check("0"))
t("answer 0 принимает 359", nt.NavTask("x", "", 0, "").check("359"))
t("answer 0 принимает 360", nt.NavTask("x", "", 0, "").check("360"))
t("answer 10 НЕ принимает 20", not nt.NavTask("x", "", 10, "").check("20"))
t("answer 90 принимает 90", nt.NavTask("x", "", 90, "").check("90"))
t("answer 90 принимает 91 (±1)", nt.NavTask("x", "", 90, "").check("91"))
t("answer 90 НЕ принимает 92", not nt.NavTask("x", "", 90, "").check("92"))
t("нечисло отклоняется", not nt.NavTask("x", "", 90, "").check("abc"))
t("запятая как точка", nt.NavTask("x", "", 90, "").check("90,5"))

# angle_diff корректность
t("angle_diff(359,1)=2", abs(nt.angle_diff(359, 1) - 2) < 1e-9)
t("angle_diff(10,350)=20", abs(nt.angle_diff(10, 350) - 20) < 1e-9)

# база задач валидна
t("50 задач", len(nt.TASKS) == 50)
t("10 со звёздочкой", len(nt.starred_tasks()) == 10)
t("все answer в 0..359", all(0 <= x.answer < 360 for x in nt.TASKS))
t("id уникальны", len({x.id for x in nt.TASKS}) == 50)
# каждая задача решается своим же ответом
t("self-consistency", all(x.check(str(x.answer)) for x in nt.TASKS))

if fails:
    sys.stdout.buffer.write(("НЕ ПРОЙДЕНО:\n" + "\n".join(" - " + f for f in fails) + "\n").encode("utf-8", "replace"))
    sys.exit(1)
print("OK: nav tests passed")
