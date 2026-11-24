"""Generate SYNTHETIC country templates (no real data) with seeded, known defects for testing."""
from __future__ import annotations

import random
from pathlib import Path

from openpyxl import Workbook

LEVELS = {"ISCED1": (6, 11), "ISCED2": (12, 14), "ISCED3": (15, 17)}


def _book(path: Path, country: str, defects: set[str], seed: int):
    rnd = random.Random(seed)
    wb = Workbook()
    meta = wb.active
    meta.title = "Meta"
    meta.append(["country", country])
    meta.append(["survey_year", 2026])
    en = wb.create_sheet("Enrolment")
    en.append(["year", "level", "age", "sex", "enrolment"])
    po = wb.create_sheet("Population")
    po.append(["year", "age", "sex", "population"])
    for year in (2023, 2024, 2025):
        for lvl, (a0, a1) in LEVELS.items():
            for age in range(a0, a1 + 1):
                pop_m = rnd.randint(18000, 22000)
                pop_f = rnd.randint(18000, 22000)
                m = int(pop_m * rnd.uniform(0.85, 0.97))
                f = int(pop_f * rnd.uniform(0.85, 0.97))
                for sex, v, p in (("M", m, pop_m), ("F", f, pop_f), ("T", m + f, pop_m + pop_f)):
                    en.append([year, lvl, age, sex, v])
                    po.append([year, age, sex, p])
    if "negative" in defects:
        en.append([2025, "ISCED1", 7, "M", -40])
    if "bad_total" in defects:
        en.append([2025, "ISCED2", 13, "M", 100])
        en.append([2025, "ISCED2", 13, "F", 100])
        en.append([2025, "ISCED2", 13, "T", 999])
    if "text" in defects:
        en.append([2024, "ISCED3", 16, "F", "n/a"])
    if "old_age" in defects:
        en.append([2025, "ISCED1", 30, "T", 12])
    if "jump" in defects:  # +50 % on M and F; T is recomputed so totals stay consistent
        rows = [r for r in en.iter_rows(min_row=2) if r[0].value == 2025 and r[1].value == "ISCED3"]
        by_age = {}
        for r in rows:
            if r[3].value in ("M", "F"):
                r[4].value = int(r[4].value * 1.5)
                by_age[r[2].value] = by_age.get(r[2].value, 0) + r[4].value
        for r in rows:
            if r[3].value == "T":
                r[4].value = by_age[r[2].value]
    if "dup" in defects:
        en.append([2023, "ISCED1", 6, "M", 5])
    wb.save(path)


def make_demo(folder: str | Path) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    plan = {"Aland": set(), "Borduria": {"negative", "bad_total"}, "Carpania": {"old_age", "jump"},
            "Dalmara": {"text"}, "Eldoria": {"dup"}}
    for i, (c, d) in enumerate(plan.items()):
        _book(folder / f"{c}_MYDT.xlsx", c, d, seed=i)
    (folder / "Broken_MYDT.xlsx").write_bytes(b"not a workbook")
    return folder
