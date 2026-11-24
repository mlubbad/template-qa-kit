import sqlite3

import pandas as pd

from tqk import indicators, rules
from tqk.demo import make_demo
from tqk.pipeline import process_folder


def _issues(db, country):
    with sqlite3.connect(db) as c:
        return pd.read_sql("select * from issues where country=?", c, params=(country,))


def test_end_to_end(tmp_path):
    src = make_demo(tmp_path / "in")
    s = process_folder(src, tmp_path / "out")
    assert s["files"] == 6
    # Aland (clean) and Carpania (warnings only) are accepted; Borduria, Dalmara, Eldoria and the corrupt file are rejected.
    assert s["accepted"] == 2
    assert s["rejected"] == 4


def test_clean_country_has_no_issues(tmp_path):
    process_folder(make_demo(tmp_path / "in"), tmp_path / "out")
    assert _issues(tmp_path / "out" / "consolidated.sqlite", "Aland").empty


def test_known_defects_detected(tmp_path):
    process_folder(make_demo(tmp_path / "in"), tmp_path / "out")
    db = tmp_path / "out" / "consolidated.sqlite"
    assert {"R02", "R04"} <= set(_issues(db, "Borduria")["rule"])
    assert {"R05", "R06"} <= set(_issues(db, "Carpania")["rule"])
    assert "R02" in set(_issues(db, "Dalmara")["rule"])
    assert "R03" in set(_issues(db, "Eldoria")["rule"])


def test_unreadable_file_reported_not_fatal(tmp_path):
    process_folder(make_demo(tmp_path / "in"), tmp_path / "out")
    with sqlite3.connect(tmp_path / "out" / "consolidated.sqlite") as c:
        r = pd.read_sql("select * from issues where rule='R00'", c)
    assert len(r) == 1 and "Broken" in r.iloc[0]["country"]


def test_rejected_countries_not_consolidated(tmp_path):
    process_folder(make_demo(tmp_path / "in"), tmp_path / "out")
    with sqlite3.connect(tmp_path / "out" / "consolidated.sqlite") as c:
        got = set(pd.read_sql("select distinct country from enrolment", c)["country"])
    assert "Borduria" not in got and "Aland" in got


def test_gpi_and_ner():
    df = pd.DataFrame({"year": [2025] * 3, "level": ["ISCED1"] * 3, "age": [6, 6, 6], "sex": ["M", "F", "T"], "enrolment": [90, 100, 190]})
    pop = pd.DataFrame({"year": [2025] * 3, "age": [6, 6, 6], "sex": ["M", "F", "T"], "population": [100, 100, 200]})
    assert indicators.parity_index(df, "ISCED1").iloc[0]["gpi"] == 1.111
    assert indicators.net_enrolment_ratio(df, pop, "ISCED1").iloc[0]["ner_pct"] == 95.0


def test_missing_columns_stops_cleanly():
    out = rules.run_all(pd.DataFrame({"year": [1]}), None, "X")
    assert out and out[0]["rule"] == "R01"
