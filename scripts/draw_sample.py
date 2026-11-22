"""
Draw the random company sample for the XBRL accuracy audit.

What it does, step by step:
  1. Reads the three NSE index constituent lists (downloaded from niftyindices.com)
     from data/index_lists/.
  2. Removes financial companies (banks, NBFCs, insurers and the rest of the
     "Financial Services" industry). They file results in a different format,
     so their line items can't be compared with everyone else's.
  3. For each size group, shuffles the remaining companies with a fixed seed
     (2026) and takes the target number plus 5 spares.
  4. Saves the result to data/sample.csv.

Why a fixed seed: anyone can rerun this script on the same three files and get
exactly the same companies. That answers the interview question "did you pick
companies you expected to have errors?" - no, a random draw picked them.

Why we sort before shuffling: the order of rows in the downloaded file could
change between downloads. Sorting by symbol first means the draw depends only
on WHICH companies are in the index, not on how the file happens to be ordered.

Run from the repository root:
    python scripts/draw_sample.py
"""

import csv
import random
from pathlib import Path

SEED = 2026
SPARES_PER_GROUP = 5

# Each size group: the index it is drawn from, the file name, how many to pick,
# and how many of those go into the week-1 pilot.
GROUPS = [
    # (size_group, index name,            file name,                  target, pilot)
    ("Large", "Nifty 50",            "ind_nifty50list.csv",          15, 4),
    ("Mid",   "Nifty Midcap 150",    "ind_niftymidcap150list.csv",   15, 3),
    ("Small", "Nifty Smallcap 250",  "ind_niftysmallcap250list.csv", 10, 3),
]

# The exclusion rule. NSE files tag every company with one industry; we drop the
# whole "Financial Services" industry. This also drops a few companies that file
# in the normal format (exchanges, depositories, brokers), but it is one simple
# rule that needs no judgement company by company. Stated in the README.
EXCLUDED_INDUSTRIES = {"Financial Services"}

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "data" / "index_lists"
OUTPUT_FILE = ROOT / "data" / "sample.csv"


def read_index_list(path):
    """Read one constituent CSV and return a list of dicts with clean keys."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    # Column names in the NSE files: Company Name, Industry, Symbol, Series, ISIN Code.
    # Strip stray spaces so a small format change doesn't break the script.
    clean = []
    for row in rows:
        row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
        clean.append({
            "company_name": row["Company Name"],
            "industry": row["Industry"],
            "symbol": row["Symbol"],
            "isin": row["ISIN Code"],
        })
    return clean


def main():
    output_rows = []
    print(f"Seed: {SEED}\n")

    for size_group, index_name, file_name, target, pilot in GROUPS:
        companies = read_index_list(INPUT_DIR / file_name)
        kept = [c for c in companies if c["industry"] not in EXCLUDED_INDUSTRIES]
        dropped = len(companies) - len(kept)

        # Sort, then shuffle with a group-specific generator seeded with 2026.
        kept.sort(key=lambda c: c["symbol"])
        rng = random.Random(SEED)
        rng.shuffle(kept)

        needed = target + SPARES_PER_GROUP
        drawn = kept[:needed]

        for order, c in enumerate(drawn, start=1):
            output_rows.append({
                "size_group": size_group,
                "index_name": index_name,
                "draw_order": order,
                "role": "main" if order <= target else "spare",
                "pilot": "Y" if order <= pilot else "N",
                "symbol": c["symbol"],
                "company_name": c["company_name"],
                "industry": c["industry"],
                "isin": c["isin"],
            })

        print(f"{index_name}: {len(companies)} listed, {dropped} financial removed, "
              f"{len(kept)} eligible -> {target} main + {SPARES_PER_GROUP} spares "
              f"(first {pilot} are the pilot)")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(output_rows[0].keys()))
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\nSaved {len(output_rows)} rows to {OUTPUT_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
