"""
Turn check 1 and check 3 exceptions into output/error_log.csv and the error_log table.

Every exception was investigated by hand against the PDF and the raw XBRL.
REVIEW below is the record of that investigation: one category per pattern
(category list fixed in the README before results were seen) and a one-line
note saying what the gap is. Describe, don't accuse: these notes say how two
versions of a figure differ, not that anyone acted wrongly.

Run from the repository root, after run_check1.py and run_check3.py:
    python scripts/build_error_log.py
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TAXONOMY_NOTE = ("The SEBI taxonomy has only RevenueFromOperations and OtherIncome for income, so a third income line printed separately in the PDF has to be merged into one of them in the XBRL. ")

# Check 1. (symbol, line_item or '*') -> (category, note). Most specific key wins.
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
        "Half-year figures match the PDF. Same quarter last year was filed as 'Quarterly'."),
    ("FSL", "revenue_from_operations"): (
        "wrong_line",
        TAXONOMY_NOTE +
        "XBRL RevenueFromOperations equals the PDF's revenue plus its separate line 'Other operating income, net' "
        "(a negative amount). The gap equals that line exactly, and total income agrees. In the consolidated "
        "file, the segment section (SegmentRevenueFromOperations) carries the PDF revenue figure."),
    ("WELSPUNLIV", "basic_eps"): (
        "wrong_line",
        "XBRL basic EPS (1.86 quarter, 3.55 half-year) equals the PDF's 'Basic EPS before exceptional items'. "
        "The PDF's EPS after exceptional items (Rs 7.16 crore flood loss) is 1.80 and 3.49. "
        "Consolidated only; the standalone XBRL carries the after-exceptional EPS."),
    ("VEDPOWER", "*"): (
        "missing",
        "Q2 FY27 XBRL filed with TypeOfReportingPeriod 'Half Yearly' (standalone and consolidated): "
        "Apr-Sep figures only, so no Jul-Sep quarter value exists in the XBRL. The PDF reports the quarter. "
        "Half-year figures match the PDF. The company has no Q2 FY26 filing to compare with (listed after its demerger)."),
    ("ACC", "revenue_from_operations"): (
        "wrong_line",
        TAXONOMY_NOTE +
        "XBRL RevenueFromOperations equals the PDF's revenue plus its separate line 'Government grants including "
        "duty credits/refunds' (Rs 23 crore quarter, Rs 41 crore half-year). The gap equals that line exactly, "
        "and total income agrees. Standalone and consolidated."),
    ("M&M", "revenue_from_operations"): (
        "wrong_line",
        TAXONOMY_NOTE +
        "XBRL RevenueFromOperations equals the PDF's revenue plus its separate line 'Income from investments "
        "related to subsidiaries, associates and joint ventures' (standalone Rs 1,804.46 crore quarter, consolidated "
        "Rs 38.15 crore). The gap equals that line exactly, and total income agrees."),
    ("AFCONS", "basic_eps"): (
        "standalone_consolidated_swapped",
        "Consolidated XBRL half-year basic EPS is 4.59, which is the standalone half-year EPS. The consolidated PDF "
        "shows 1.94 (Rs 71.39 crore profit). Consolidated half-year profit in the XBRL is correct; only EPS differs."),
    ("TECHM", "*"): (
        "wrong_line",
        "Consolidated half-year: the share of associates and joint ventures (Rs -43 million) is tagged as "
        "ExceptionalItemsBeforeTax, and the associates tag is 0. The PDF shows nil exceptional items and the -43 "
        "as share of associates. Profit before tax agrees (Rs 43,380 million)."),
}


# Check 3. (symbol, column_period or '*', line_item or '*') -> (category, note). Most specific key wins.
# preceding_quarter = Apr-Jun 2026 (vs Q1 FY27 XBRL); same_quarter_last_year = Jul-Sep 2025 (vs Q2 FY26 XBRL).
MERGER = "The PDF marks these comparatives as restated for an amalgamation ({}); the XBRL holds the figures as first published."
REVIEW3 = {
    ("ACC", "preceding_quarter", "revenue_from_operations"): (
        "wrong_line", TAXONOMY_NOTE + "Same pattern as Q2 FY27: Q1 FY27 XBRL revenue includes the government grants line (Rs 18 crore)."),
    ("ACC", "same_quarter_last_year", "*"): (
        "restated", "The PDF regroups Q2 FY26 (coal cost reclassified, note 10), which raises revenue and expenses by about Rs 73 crore "
        "with no effect on profit. The Q2 FY26 XBRL also has the government grants line (Rs 36 crore) inside revenue."),
    ("ADANIPORTS", "same_quarter_last_year", "*"): (
        "restated", MERGER.format("Adani Harbour Services into APSEZ, appointed date 1 Jul 2025") + " The PDF prints a reconciliation."),
    ("AFCONS", "same_quarter_last_year", "basic_eps"): (
        "unexplained", "Q2 FY26 consolidated EPS was filed as 2.86; the Q2 FY27 PDF shows 2.85. No note explains the 0.01 change."),
    ("COALINDIA", "same_quarter_last_year", "*"): (
        "restated", "The PDF regroups Q2 FY26 and prints a reconciliation whose 'previously reported' figures equal the first-filed XBRL "
        "(e.g. consolidated revenue Rs 30,186.70 crore, profit Rs 4,262.64 crore). Consolidated revenue rose by Rs 6,366 crore and profit fell "
        "by Rs 95 crore. Standalone is regrouped too (revenue and expenses up Rs 4.6 crore, profit unchanged). The reconciliation's own EPS table shows 21.19 for the quarter, which is the half-year figure."),
    ("FSL", "*", "revenue_from_operations"): (
        "wrong_line", TAXONOMY_NOTE + "Same pattern as Q2 FY27: the XBRL revenue includes 'Other operating income, net'."),
    ("GRASIM", "same_quarter_last_year", "*"): (
        "restated", "Q2 FY26 consolidated is marked 'Restated (refer note 3)': a joint venture's accounting-policy adoption changed the "
        "share of JV profit by Rs 78 crore. Revenue and expenses are unchanged."),
    ("JSWSTEEL", "*", "*"): (
        "restated", MERGER.format("standalone, both comparative quarters marked 'Restated pursuant to merger'")),
    ("LAURUSLABS", "same_quarter_last_year", "*"): (
        "missing", "The first-filed Q2 FY26 XBRL has no Jul-Sep quarter: consolidated was filed as 'Half Yearly', and the standalone file "
        "NSE serves is truncated, invalid XML. Both were replaced by a revision 92 days later (see check 2)."),
    ("LTTS", "same_quarter_last_year", "*"): (
        "restated", "Q2 FY26 is re-presented for a discontinued operation: the PDF shows continuing operations only down to PBT, "
        "so revenue, expenses and PBT are lower than first filed. Net profit (continuing plus discontinued) agrees, "
        "consolidated exactly and standalone within Rs 1 million."),
    ("M&M", "*", "revenue_from_operations"): (
        "wrong_line", TAXONOMY_NOTE + "Same pattern as Q2 FY27: the XBRL revenue includes 'Income from investments related to subsidiaries, associates and JVs'."),
    ("MARUTI", "same_quarter_last_year", "*"): (
        "restated", MERGER.format("Suzuki Motor Gujarat into Maruti Suzuki, appointed date 1 Apr 2025; standalone")),
    ("SWIGGY", "same_quarter_last_year", "*"): (
        "restated", "Q2 FY26 standalone is re-presented for a discontinued operation (loss of Rs 918 crore shown separately). "
        "Revenue, expenses and PBT in the PDF are continuing operations only; net profit still agrees."),
    ("TECHM", "same_quarter_last_year", "*"): (
        "wrong_line", "Same pattern as Q2 FY27 half-year: Q2 FY26 consolidated XBRL tags the share of associates (Rs -28 million) "
        "as an exceptional item. PBT agrees."),
    ("TIINDIA", "same_quarter_last_year", "other_income"): (
        "wrong_line", TAXONOMY_NOTE + "Q2 FY26 XBRL other income includes the 'Fair value gain on CCPS in subsidiary' line (Rs 2.40 crore) "
        "that the Q2 FY27 PDF prints separately."),
    ("TRENT", "same_quarter_last_year", "basic_eps"): (
        "restated", "Q2 FY26 EPS restated for a bonus issue (share capital Rs 35.55 crore to Rs 53.32 crore). Profit agrees."),
    ("UNITDSPR", "same_quarter_last_year", "*"): (
        "restated", "Q2 FY26 consolidated is re-presented for a discontinued operation: PBT is continuing operations only and "
        "other income and expenses move by Rs 4-7 crore. EPS differs by 0.01."),
}


def review(symbol, line_item):
    return REVIEW.get((symbol, line_item)) or REVIEW.get((symbol, "*")) or ("unexplained", "NOT YET REVIEWED")


def review3(symbol, column, line_item):
    for key in ((symbol, column, line_item), (symbol, column, "*"), (symbol, "*", line_item), (symbol, "*", "*")):
        if key in REVIEW3:
            return REVIEW3[key]
    return ("unexplained", "NOT YET REVIEWED")


def main():
    con = sqlite3.connect(ROOT / "data" / "audit.db")
    out = []
    for check, src, fn in (("xbrl_vs_pdf", "check1_exceptions.csv", lambda r: review(r["symbol"], r["line_item"])),
                           ("restatement", "check3_exceptions.csv",
                            lambda r: review3(r["symbol"], r["column_period"], r["line_item"]))):
        with open(ROOT / "output" / src, newline="") as f:
            rows = list(csv.DictReader(f))
        con.execute("DELETE FROM error_log WHERE check_name = ?", (check,))
        for r in rows:
            category, note = fn(r)
            cid = con.execute("SELECT company_id FROM companies WHERE symbol = ?", (r["symbol"],)).fetchone()[0]
            con.execute(
                """INSERT INTO error_log (company_id, check_name, basis, line_item, column_period,
                                          value_a_inr, value_b_inr, category, note)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cid, check, r["basis"], r["line_item"], r["column_period"],
                 float(r["xbrl_inr"]) if r["xbrl_inr"] else None, float(r["pdf_inr"]), category, note))
            out.append({"symbol": r["symbol"], "size_group": r["size_group"], "check": check,
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
    for o in unreviewed:
        print("  ", o["check"], o["symbol"], o["basis"], o["column_period"], o["line_item"])


if __name__ == "__main__":
    main()
