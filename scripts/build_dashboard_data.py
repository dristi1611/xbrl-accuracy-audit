"""
Tables for the Power BI dashboard (dashboard/):

  dashboard/exceptions.csv   one row per exception (from output/error_log.csv), with readable labels
  dashboard/statements.csv   one row per statement and check, with a 1/0 flag for "has an exception",
                             so the dashboard can show shares as well as counts

Run from the repository root, after build_error_log.py:
    python scripts/build_dashboard_data.py
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard"

CHECK = {"xbrl_vs_pdf": "Check 1: XBRL vs PDF", "restatement": "Check 3: restatement"}
CATEGORY = {"missing": "Missing", "wrong_line": "Wrong line", "restated": "Restated",
            "standalone_consolidated_swapped": "Standalone/consolidated swapped", "unexplained": "Unexplained",
            "rounding": "Rounding", "wrong_scale_or_unit": "Wrong scale or unit", "sign_flipped": "Sign flipped"}
LINE = {"revenue_from_operations": "Revenue from operations", "other_income": "Other income",
        "total_income": "Total income", "total_expenses": "Total expenses",
        "share_of_associates_jv": "Share of associates/JVs", "exceptional_items": "Exceptional items",
        "profit_before_tax": "Profit before tax", "net_profit": "Net profit", "basic_eps": "Basic EPS"}
PERIOD = {"current_quarter": "Jul-Sep 2026 quarter", "current_half_year": "Apr-Sep 2026 half-year",
          "preceding_quarter": "Apr-Jun 2026 quarter", "same_quarter_last_year": "Jul-Sep 2025 quarter"}
SIZE = {"Large": "Large (Nifty 50)", "Mid": "Mid (Midcap 150)", "Small": "Small (Smallcap 250)"}


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write(name, rows):
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(exist_ok=True)
    names = {r["symbol"]: r["company_name"] for r in read(ROOT / "data" / "sample.csv")}

    exc = []
    for r in read(ROOT / "output" / "error_log.csv"):
        x, p = r["xbrl_inr"], r["pdf_inr"]
        eps = r["line_item"] == "basic_eps"
        exc.append({"statement_key": f'{r["symbol"]}|{r["basis"].title()}|{CHECK[r["check"]]}',
                    "company": names[r["symbol"]], "symbol": r["symbol"], "size_group": SIZE[r["size_group"]],
                    "check": CHECK[r["check"]], "basis": r["basis"].title(), "line_item": LINE[r["line_item"]],
                    "period": PERIOD[r["column_period"]], "category": CATEGORY[r["category"]],
                    "xbrl_value": "" if not x else (float(x) if eps else round(float(x) / 1e7, 2)),
                    "pdf_value": float(p) if eps else round(float(p) / 1e7, 2),
                    "unit": "Rs per share" if eps else "Rs crore",
                    "note": r["note"]})
    write("exceptions.csv", exc)

    flagged = {}
    for r in exc:
        flagged[r["statement_key"]] = flagged.get(r["statement_key"], 0) + 1
    stm, seen = [], set()
    for check, src in (("xbrl_vs_pdf", "check1_results.csv"), ("restatement", "check3_results.csv")):
        for r in read(ROOT / "output" / src):
            k = (r["symbol"], r["basis"].title(), CHECK[check])
            if k in seen:
                continue
            seen.add(k)
            n = flagged.get("|".join(k), 0)
            stm.append({"statement_key": "|".join(k), "company": names[r["symbol"]], "symbol": r["symbol"], "size_group": SIZE[r["size_group"]],
                        "check": CHECK[check], "basis": r["basis"].title(),
                        "has_exception": int(n > 0), "exceptions": n})
    write("statements.csv", stm)
    print(f"{len(exc)} exceptions, {len(stm)} statement rows "
          f"({sum(s['has_exception'] for s in stm if s['check'].startswith('Check 1'))} with a check-1 exception)")


if __name__ == "__main__":
    main()
