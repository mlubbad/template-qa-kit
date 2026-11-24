"""Folder of workbooks -> validated, consolidated SQLite database + per-country review reports."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import indicators, reader, rules


def process_folder(src: str | Path, out: str | Path) -> dict:
    src, out = Path(src), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "reports").mkdir(exist_ok=True)
    enrol, inds, issues, log = [], [], [], []
    for f in sorted(src.glob("*.xlsx")):
        if f.name.startswith("~$"):
            continue
        try:
            wb = reader.read_workbook(f)
        except ValueError as e:
            issues.append({"rule": "R00", "severity": "error", "country": f.stem, "message": str(e)})
            log.append({"file": f.name, "status": "unreadable"})
            continue
        c = wb["country"]
        iss = rules.run_all(wb["data"], wb["pop"], c)
        for i in iss:
            i["source"] = f.name
        issues += iss
        has_err = any(i["severity"] == "error" for i in iss)
        log.append({"file": f.name, "country": c, "rows": len(wb["data"]), "errors": sum(i["severity"] == "error" for i in iss),
                    "warnings": sum(i["severity"] == "warning" for i in iss), "status": "rejected" if has_err else "accepted"})
        if not has_err:
            d = wb["data"].assign(country=c, source=f.name)
            d["enrolment"] = pd.to_numeric(d["enrolment"], errors="coerce")
            enrol.append(d)
            inds.append(indicators.all_indicators(d, wb["pop"], c))
        _write_report(out / "reports" / f"{c}.md", c, f.name, iss, has_err)
    enrol_df = pd.concat(enrol, ignore_index=True) if enrol else pd.DataFrame()
    ind_df = pd.concat(inds, ignore_index=True) if inds else pd.DataFrame()
    iss_df = pd.DataFrame(issues)
    with sqlite3.connect(out / "consolidated.sqlite") as con:
        enrol_df.to_sql("enrolment", con, if_exists="replace", index=False)
        ind_df.to_sql("indicators", con, if_exists="replace", index=False)
        iss_df.to_sql("issues", con, if_exists="replace", index=False)
        pd.DataFrame(log).to_sql("run_log", con, if_exists="replace", index=False)
    summary = {"run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "files": len(log),
               "accepted": sum(l["status"] == "accepted" for l in log), "rejected": sum(l["status"] != "accepted" for l in log),
               "issues": len(issues), "rows_consolidated": len(enrol_df)}
    (out / "run_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def _write_report(path: Path, country: str, fname: str, issues: list[dict], rejected: bool) -> None:
    lines = [f"# Country review: {country}", f"Source: `{fname}`", f"Decision: **{'REJECTED, return to country' if rejected else 'ACCEPTED'}**", ""]
    if not issues:
        lines.append("No issues found.")
    for sev in ("error", "warning"):
        sub = [i for i in issues if i["severity"] == sev]
        if sub:
            lines += [f"## {sev.title()}s ({len(sub)})"] + [f"- `{i['rule']}` {i['message']}" + (f" (year {i.get('year')}, {i.get('level')}, age {i.get('age')})" if i.get("year") else "") for i in sub] + [""]
    path.write_text("\n".join(lines), encoding="utf-8")
