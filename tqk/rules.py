"""Declarative validation rules. Every rule returns a list of Issue dicts so results are auditable."""
from __future__ import annotations

import pandas as pd

# Plausible single-year-of-age bands per level (illustrative, configurable per survey cycle).
AGE_BANDS = {"ISCED1": (5, 14), "ISCED2": (10, 18), "ISCED3": (13, 22)}
ENTRY_AGE = {"ISCED1": 6, "ISCED2": 12, "ISCED3": 15}
JUMP_THRESHOLD = 0.30       # year-on-year change flagged above 30 %
GPI_BOUNDS = (0.7, 1.3)
TOL = 0.5                    # rounding tolerance for total = male + female

REQUIRED_COLS = ["year", "level", "age", "sex", "enrolment"]


def _issue(rule, severity, country, msg, **ctx):
    return {"rule": rule, "severity": severity, "country": country, "message": msg, **ctx}


def r01_structure(df: pd.DataFrame, country: str):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    return [_issue("R01", "error", country, f"missing columns: {missing}")] if missing else []


def r02_values(df, country):
    out = []
    bad = df[pd.to_numeric(df["enrolment"], errors="coerce").isna() & df["enrolment"].notna()]
    for _, r in bad.iterrows():
        out.append(_issue("R02", "error", country, f"non-numeric enrolment '{r['enrolment']}'", year=r["year"], level=r["level"], age=r["age"]))
    num = pd.to_numeric(df["enrolment"], errors="coerce")
    for _, r in df[num < 0].iterrows():
        out.append(_issue("R02", "error", country, "negative enrolment", year=r["year"], level=r["level"], age=r["age"]))
    return out


def r03_duplicates(df, country):
    dup = df[df.duplicated(["year", "level", "age", "sex"], keep=False)]
    return [_issue("R03", "error", country, "duplicate key", year=r["year"], level=r["level"], age=r["age"]) for _, r in dup.drop_duplicates(["year", "level", "age", "sex"]).iterrows()]


def r04_totals(df, country):
    out = []
    piv = df.pivot_table(index=["year", "level", "age"], columns="sex", values="enrolment", aggfunc="sum")
    if {"M", "F", "T"} <= set(piv.columns):
        diff = (piv["T"] - piv["M"] - piv["F"]).abs()
        for (y, l, a), d in diff[diff > TOL].items():
            out.append(_issue("R04", "error", country, f"total != male + female (diff {d:.0f})", year=y, level=l, age=a))
    return out


def r05_age_band(df, country):
    out = []
    for lvl, (lo, hi) in AGE_BANDS.items():
        sub = df[(df["level"] == lvl) & (df["enrolment"] > 0)]
        for _, r in sub[(sub["age"] < lo) | (sub["age"] > hi)].iterrows():
            out.append(_issue("R05", "warning", country, f"{lvl} enrolment at implausible age {r['age']} (band {lo}-{hi})", year=r["year"], level=lvl, age=r["age"]))
    return out


def r06_year_jump(df, country):
    out = []
    t = df[df["sex"] == "T"].groupby(["level", "year"])["enrolment"].sum().sort_index()
    for lvl in t.index.get_level_values(0).unique():
        s = t.loc[lvl].sort_index()
        ch = s.pct_change()
        for y, c in ch[ch.abs() > JUMP_THRESHOLD].items():
            out.append(_issue("R06", "warning", country, f"{lvl} total changed {c:+.0%} vs previous year", year=y, level=lvl))
    return out


def r07_population(df, pop, country):
    out = []
    if pop is None or pop.empty:
        return [_issue("R07", "warning", country, "no population sheet; ratio checks skipped")]
    m = df[df["sex"] == "T"].merge(pop[pop["sex"] == "T"], on=["year", "age"], how="left", suffixes=("", "_pop"))
    for _, r in m[m["population"].notna() & (m["enrolment"] > m["population"] * 1.5)].iterrows():
        out.append(_issue("R07", "error", country, f"enrolment {r['enrolment']:.0f} > 150% of population {r['population']:.0f}", year=r["year"], level=r["level"], age=r["age"]))
    return out


def run_all(df: pd.DataFrame, pop: pd.DataFrame | None, country: str):
    """Run every rule. Non-numeric cells are reported (R02) and then dropped from numeric checks."""
    issues = r01_structure(df, country)
    if issues:  # cannot continue safely without the schema
        return issues
    raw = df.copy()
    issues += r02_values(raw, country)
    df = raw.copy()
    df["enrolment"] = pd.to_numeric(df["enrolment"], errors="coerce")
    df = df.dropna(subset=["enrolment"])
    return (issues + r03_duplicates(df, country) + r04_totals(df, country) + r05_age_band(df, country)
            + r06_year_jump(df, country) + r07_population(df, pop, country))
