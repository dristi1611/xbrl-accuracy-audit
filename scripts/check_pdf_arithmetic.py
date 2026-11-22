"""
Arithmetic checks on the figures extracted from the results PDFs.

AI extraction can slip a digit. These identities must hold inside every
statement, so a failure points at an extraction error (or a genuine error in
the PDF itself, which is rare and worth a note):

  A. revenue + other income (+ other operating income, where a company prints
     that extra line) = total income
  B. total income - total expenses + share of associates/JVs (if the PDF puts
     it above PBT) + exceptional items = profit before tax

Check B is also how we learn where each company puts the share of associates:
we try both placements and record the one that adds up. The result goes to
data/pdf_presentation.csv, which check 1 uses.

Run from the repository root:
    python scripts/check_pdf_arithmetic.py
"""

import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACT = ROOT / "data" / "pdf_extract"
OUT_CHECKS = ROOT / "output" / "pdf_arithmetic_checks.csv"
OUT_PRESENTATION = ROOT / "data" / "pdf_presentation.csv"

PERIODS = ["current_quarter", "preceding_quarter", "same_quarter_last_year", "current_half_year"]


def decimals(s):
    return len(s.split(".")[1]) if "." in s else 0


def main():
    statements = defaultdict(dict)   # (symbol, basis) -> line_item -> {period: value}
    precision = defaultdict(int)     # (symbol, basis) -> max decimals printed on amounts
    for path in sorted(EXTRACT.glob("*.csv")):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                key = (row["symbol"], row["basis"])
                statements[key][row["line_item"]] = {p: float(row[p]) for p in PERIODS}
                if row["line_item"] != "basic_eps":
                    precision[key] = max(precision[key], *(decimals(row[p]) for p in PERIODS))

    checks, presentation = [], []
    for (symbol, basis), s in sorted(statements.items()):
        tol = 0.5 * 10 ** -precision[(symbol, basis)] * 3   # three rounded numbers can add up to 1.5 units
        zero = {p: 0.0 for p in PERIODS}
        other_op = s.get("other_operating_income", zero)
        assoc = s.get("share_of_associates_jv", zero)
        exc = s.get("exceptional_items", zero)

        fits = {True: 0, False: 0}
        for p in PERIODS:
            a = s["revenue_from_operations"][p] + other_op[p] + s["other_income"][p] - s["total_income"][p]
            checks.append([symbol, basis, p, "A_income_adds_up", round(a, 4), abs(a) <= tol])
            for included in (True, False):
                b = (s["total_income"][p] - s["total_expenses"][p] + exc[p]
                     + (assoc[p] if included else 0) - s["profit_before_tax"][p])
                if abs(b) <= tol:
                    fits[included] += 1

        # Placement that makes check B pass in all four columns. A company with
        # no associate amounts fits both; record 0 (nothing to add back).
        if basis == "consolidated" and any(assoc[p] for p in PERIODS):
            in_pbt = fits[True] == len(PERIODS)
            ok = fits[True] == len(PERIODS) or fits[False] == len(PERIODS)
        else:
            in_pbt = False
            ok = fits[False] == len(PERIODS)
        presentation.append([symbol, basis, int(in_pbt)])
        checks.append([symbol, basis, "all", "B_pbt_adds_up", "", ok])

    OUT_CHECKS.parent.mkdir(exist_ok=True)
    with open(OUT_CHECKS, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "basis", "column_period", "check", "difference", "passed"])
        w.writerows(checks)
    with open(OUT_PRESENTATION, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "basis", "associates_in_pbt"])
        w.writerows(presentation)

    failed = [c for c in checks if not c[5]]
    print(f"{len(statements)} statements, {len(checks)} checks, {len(failed)} failed")
    for c in failed:
        print("  FAILED:", c)


if __name__ == "__main__":
    main()
