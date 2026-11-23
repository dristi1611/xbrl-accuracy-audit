"""
Run check 3 (sql/check3_restatements.sql) against data/audit.db and write:
  output/check3_results.csv   every comparison with its status
  output/check3_exceptions.csv  only the rows that are not match/rounding

Run from the repository root:
    python scripts/run_check3.py
"""

import csv
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    con = sqlite3.connect(ROOT / "data" / "audit.db")
    cur = con.execute((ROOT / "sql" / "check3_restatements.sql").read_text())
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    for name, subset in (("check3_results.csv", rows),
                         ("check3_exceptions.csv", [r for r in rows if r["status"] not in ("match", "rounding")])):
        with open(out / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(subset)

    print(f"{len(rows)} comparisons")
    for status, n in Counter(r["status"] for r in rows).most_common():
        print(f"  {status:16} {n}")


if __name__ == "__main__":
    main()
