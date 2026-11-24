# template-qa-kit

Validate, recompute and consolidate many Excel data-collection templates into one audited SQLite database.
Built as a small, reproducible reference for template-driven statistical surveys (SDG 4 style: enrolment by level, age and sex).

**All data in this repository is synthetic.** `tqk.demo` generates five fictional country workbooks with seeded, known defects, plus one corrupt file, so every rule can be tested end to end.

## What it does

1. **Read** every `*.xlsx` in a folder (cached cell values only, no macros executed). A corrupt file is logged, never fatal.
2. **Validate** with declarative rules (each returns auditable issue records):
   - `R00` unreadable workbook, `R01` schema/columns, `R02` non-numeric or negative values, `R03` duplicate keys,
   - `R04` total ≠ male + female, `R05` implausible age for the level (age-cohort check), `R06` year-on-year jump above 30 %, `R07` enrolment above 150 % of population.
3. **Recompute** indicators (net enrolment ratio for the official age group, gender parity index) so submitted values can be reconciled.
4. **Consolidate** accepted submissions into `consolidated.sqlite` (`enrolment`, `indicators`, `issues`, `run_log`) and write one Markdown **country review report** per file.
   Files with any `error` are rejected and returned to the country; `warning`s are kept for analyst review.

## Run

```bash
pip install -e ".[dev]"
python -c "from tqk.demo import make_demo; make_demo('examples/input')"
tqk examples/input --out examples/output
pytest
```

Expected on the demo set: 6 files, 2 accepted (one clean, one with warnings only), 4 rejected.

## Design notes

- Rules are plain functions over DataFrames: adding a rule means one function and one test.
- Thresholds (`AGE_BANDS`, `JUMP_THRESHOLD`, `TOL`) are module constants so a survey cycle can override them.
- Every run writes `run_summary.json` and a `run_log` table, so a consolidation can be reproduced and audited.
- Translation of template labels and a simple web front end are natural next steps and are intentionally out of scope here.

MIT licence.
