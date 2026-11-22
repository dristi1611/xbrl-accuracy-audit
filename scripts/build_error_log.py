"""
Turn check 1 exceptions into output/error_log.csv and the error_log table.

Every exception was investigated by hand against the PDF and the raw XBRL.
REVIEW below is the record of that investigation: one category per pattern
(category list fixed in the README before results were seen) and a one-line
note saying what the gap is. Describe, don't accuse: these notes say how two
versions of a figure differ, not that anyone acted wrongly.

Run from the repository root, after run_check1.py:
    python scripts/build_error_log.py
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (symbol, line_item or '*') -> (category, note). Most specific key wins.
REVIEW = {
    ("COALINDIA", "*"): (
        "missing",
        "Q2 FY27 XBRL filed with TypeOfReportingPeriod 'Half Yearly': it holds Apr-Sep figures only, "
        "so no Jul-Sep quarter value exists in the XBRL. The PDF reports the quarter. "
        "Half-year figures match the PDF. Same quarter last year was filed as 'Quarterly'."),
    ("EMAMILTD", "*"): (
        "missing",
        "Q2 FY27 XBRL filed with TypeOfReportingPeriod 'Half Yearly': it holds Apr-Sep figures only, "
        "so no Jul-Sep quarter value exists in the XBRL. The PDF reports the quarter. "
        "Half-year figures match the PDF."),
    ("FSL", "revenue_from_operations"): (
        "wrong_line",
        "XBRL RevenueFromOperations equals the PDF's revenue plus its separate line 'Other operating income, net' "
        "(a negative amount). The gap equals that line exactly, and total income agrees. The same XBRL file's "
        "segment section (SegmentRevenueFromOperations) carries the PDF revenue figure."),
    ("WELSPUNLIV", "basic_eps"): (
        "wrong_line",
        "XBRL basic EPS (1.86 quarter, 3.55 half-year) equals the PDF's 'Basic EPS before exceptional items'. "
        "The PDF's EPS after exceptional items (Rs 7.16 crore flood loss) is 1.80 and 3.49. "
        "Consolidated only; the standalone XBRL carries the after-exceptional EPS."),
}


def review(symbol, line_item):
    return REVIEW.get((symbol, line_item)) or REVIEW.get((symbol, "*")) or ("unexplained", "NOT YET REVIEWED")


def main():
    with open(ROOT / "output" / "check1_exceptions.csv", newline="") as f:
        rows = list(csv.DictReader(f))

    con = sqlite3.connect(ROOT / "data" / "audit.db")
    con.execute("DELETE FROM error_log WHERE check_name = 'xbrl_vs_pdf'")
    out = []
    for r in rows:
        category, note = review(r["symbol"], r["line_item"])
        cid = con.execute("SELECT company_id FROM companies WHERE symbol = ?", (r["symbol"],)).fetchone()[0]
        con.execute(
            """INSERT INTO error_log (company_id, check_name, basis, line_item, column_period,
                                      value_a_inr, value_b_inr, category, note)
               VALUES (?, 'xbrl_vs_pdf', ?, ?, ?, ?, ?, ?, ?)""",
            (cid, r["basis"], r["line_item"], r["column_period"],
             float(r["xbrl_inr"]) if r["xbrl_inr"] else None, float(r["pdf_inr"]), category, note))
        out.append({"symbol": r["symbol"], "size_group": r["size_group"], "check": "xbrl_vs_pdf",
                    "basis": r["basis"], "line_item": r["line_item"], "column_period": r["column_period"],
                    "xbrl_inr": r["xbrl_inr"], "pdf_inr": r["pdf_inr"], "status": r["status"],
                    "category": category, "note": note})
    con.commit()

    with open(ROOT / "output" / "error_log.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    unreviewed = [o for o in out if o["note"] == "NOT YET REVIEWED"]
    print(f"{len(out)} exceptions logged, {len(unreviewed)} not yet reviewed")


if __name__ == "__main__":
    main()
