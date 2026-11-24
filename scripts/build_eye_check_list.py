"""
List the PDF values that no XBRL figure confirms, for a check by eye.

A PDF value counts as confirmed when check 1 or check 3 found an XBRL figure
equal to it (status match or rounding): two independent sources agree.
Every other extracted value (exceptions, extra income lines, comparatives with
no XBRL filing to compare) goes on the list with its page and note.

Pilot companies were checked by eye on 23 Nov 2026 (output/eye_check_list.csv),
so this list covers the other 30 companies.

Run from the repository root, after run_check1.py and run_check3.py:
    python scripts/build_eye_check_list.py
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLS = ["current_quarter", "preceding_quarter", "same_quarter_last_year", "current_half_year"]


def main():
    pilot = {r["symbol"].replace("&", "") for r in csv.DictReader(open(ROOT / "data" / "sample.csv"))
             if r["pilot"] == "Y" and r["role"] == "main"}
    confirmed = set()
    for name in ("check1_results.csv", "check3_results.csv"):
        for r in csv.DictReader(open(ROOT / "output" / name)):
            if r["status"] in ("match", "rounding"):
                confirmed.add((r["symbol"].replace("&", ""), r["basis"], r["line_item"], r["column_period"]))

    # keep ticks already recorded in an earlier version of the list
    listfile = ROOT / "output" / "eye_check_list_full.csv"
    ticked = {}
    if listfile.exists():
        for r in csv.DictReader(open(listfile)):
            ticked[(r["symbol"], r["basis"], r["line_item"], r["column_period"], r["value_as_printed"])] = r["checked_by_eye"]

    out, total = [], 0
    for path in sorted((ROOT / "data" / "pdf_extract").glob("*.csv")):
        for r in csv.DictReader(open(path)):
            if r["symbol"] in pilot:
                continue
            for col in COLS:
                total += 1
                if (r["symbol"], r["basis"], r["line_item"], col) in confirmed:
                    continue
                out.append({"symbol": r["symbol"], "basis": r["basis"], "line_item": r["line_item"],
                            "column_period": col, "value_as_printed": r[col], "unit": r["unit"],
                            "page": r["page"], "how_read": r["note"],
                            "checked_by_eye": ticked.get((r["symbol"], r["basis"], r["line_item"], col, r[col]), "")})

    with open(listfile, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"{total} values extracted; "
          f"{total - len(out)} confirmed by XBRL, {len(out)} to check by eye ({len({o['symbol'] for o in out})} companies)")


if __name__ == "__main__":
    main()
