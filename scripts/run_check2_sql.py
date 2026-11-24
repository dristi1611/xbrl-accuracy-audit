"""
Run check 2 as SQL (sql/check2_revisions.sql) and write output/check2_revisions_sql.csv.
This is the line-item view; scripts/run_check2.py compares every fact in the XML files.

Run from the repository root, after load.py:
    python scripts/run_check2_sql.py
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    con = sqlite3.connect(ROOT / "data" / "audit.db")
    cur = con.execute((ROOT / "sql" / "check2_revisions.sql").read_text())
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    with open(ROOT / "output" / "check2_revisions_sql.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    for r in rows:
        d = dict(zip(cols, r))
        print(f"{d['symbol']:11}{d['quarter']} {d['basis'][:4]}  +{d['hours_later']:>7}h  changed {d['figures_changed']}, "
              f"added {d['figures_added']}, removed {d['figures_removed']}, unchanged {d['figures_unchanged']}  "
              f"{d['reporting_type_before']} -> {d['reporting_type_after']}")


if __name__ == "__main__":
    main()
