"""Read one workbook into tidy DataFrames. Works on cached cell values and never executes macros."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

DATA_SHEET, POP_SHEET, META_SHEET = "Enrolment", "Population", "Meta"


def _sheet_df(ws) -> pd.DataFrame:
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return pd.DataFrame()
    head = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
    return pd.DataFrame([r for r in rows[1:] if any(c is not None for c in r)], columns=head)


def read_workbook(path: str | Path) -> dict:
    """Return {'country','survey_year','data','pop','source'}; raises ValueError with a clear message on bad files."""
    path = Path(path)
    try:
        wb = load_workbook(path, data_only=True, read_only=False)
    except Exception as e:  # corrupt / not an xlsx
        raise ValueError(f"{path.name}: cannot open workbook ({e.__class__.__name__})") from e
    if DATA_SHEET not in wb.sheetnames:
        raise ValueError(f"{path.name}: sheet '{DATA_SHEET}' not found (has {wb.sheetnames})")
    meta = {}
    if META_SHEET in wb.sheetnames:
        for k, v in wb[META_SHEET].iter_rows(min_row=1, max_col=2, values_only=True):
            if k:
                meta[str(k).strip().lower()] = v
    data = _sheet_df(wb[DATA_SHEET])
    pop = _sheet_df(wb[POP_SHEET]) if POP_SHEET in wb.sheetnames else None
    return {
        "country": str(meta.get("country", path.stem)).strip(),
        "survey_year": meta.get("survey_year"),
        "data": data,
        "pop": pop,
        "source": path.name,
    }
