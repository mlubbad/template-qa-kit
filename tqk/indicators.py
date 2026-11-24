"""Recompute indicators from raw template data so submitted values can be reconciled."""
from __future__ import annotations

import pandas as pd

from .rules import AGE_BANDS, ENTRY_AGE


def net_enrolment_ratio(df: pd.DataFrame, pop: pd.DataFrame, level: str) -> pd.DataFrame:
    """Adjusted-style ratio: enrolled children of official primary age (entry age .. entry age + 5) / population of that age group."""
    lo = ENTRY_AGE[level]
    hi = lo + 5
    e = df[(df["level"] == level) & (df["sex"] == "T") & df["age"].between(lo, hi)].groupby("year")["enrolment"].sum()
    p = pop[(pop["sex"] == "T") & pop["age"].between(lo, hi)].groupby("year")["population"].sum()
    out = pd.concat({"enrolled": e, "population": p}, axis=1).dropna()
    out["ner_pct"] = (100 * out["enrolled"] / out["population"]).round(2)
    return out.reset_index().assign(level=level)


def parity_index(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """Gender parity index = female / male total enrolment, per year."""
    s = df[(df["level"] == level) & df["sex"].isin(["M", "F"])].groupby(["year", "sex"])["enrolment"].sum().unstack()
    s["gpi"] = (s["F"] / s["M"]).round(3)
    return s.reset_index().assign(level=level)[["year", "level", "gpi"]]


def all_indicators(df: pd.DataFrame, pop: pd.DataFrame | None, country: str) -> pd.DataFrame:
    parts = []
    for lvl in AGE_BANDS:
        if pop is not None and not pop.empty:
            n = net_enrolment_ratio(df, pop, lvl).rename(columns={"ner_pct": "value"})[["year", "level", "value"]]
            parts.append(n.assign(indicator="NER_pct"))
        g = parity_index(df, lvl).rename(columns={"gpi": "value"})
        parts.append(g.assign(indicator="GPI"))
    out = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["year", "level", "value", "indicator"])
    return out.assign(country=country)
