"""
Read every integrated-filing XBRL file in data/raw/ and write the 9 line items
to data/xbrl_figures.csv, plus one row per file to data/xbrl_filings.csv.

How an XBRL results file is organised (learned in pilot week):
  - Each number is a "fact": a tag (e.g. RevenueFromOperations), a value, and a
    contextRef pointing to a "context" that says which period it belongs to.
  - Values are always in full rupees. The filing's own unit (Crores, Lakhs,
    Millions) is a separate text field, LevelOfRounding. The "decimals"
    attribute on each fact says how precisely it was reported (-5 = to the
    nearest lakh, i.e. 2 decimals in crores).
  - A Q2 file normally has two plain (non-dimensional) duration contexts:
    the quarter (Jul-Sep) and the half-year (Apr-Sep). A Q1 file has one,
    which is both the quarter and the year-to-date.
  - Contexts with a "segment" or "scenario" are breakdowns (segments, expense
    details). We skip them: the 9 line items live in the plain contexts.

File names come from the download step: SYMBOL_QUARTER_BASIS_SUBMISSION.xml,
e.g. ADANIPORTS_Q2FY27_consolidated_original.xml.

Run from the repository root:
    python scripts/parse_xbrl.py
"""

import csv
from datetime import date
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
TAG_MAP = ROOT / "data" / "tag_map.csv"
OUT_FIGURES = ROOT / "data" / "xbrl_figures.csv"
OUT_FILINGS = ROOT / "data" / "xbrl_filings.csv"

XBRLI = "{http://www.xbrl.org/2003/instance}"
# Some standalone files carry large embedded attachments; huge_tree lets lxml read them.
PARSER = etree.XMLParser(huge_tree=True)


def localname(el):
    return etree.QName(el).localname


def months_between(start, end):
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    return (e.year - s.year) * 12 + (e.month - s.month) + 1


def plain_duration_contexts(root):
    """Return {context_id: (start, end)} for contexts with no dimensions."""
    out = {}
    for ctx in root.iter(XBRLI + "context"):
        if ctx.find(".//" + XBRLI + "segment") is not None or ctx.find(".//" + XBRLI + "scenario") is not None:
            continue
        start = ctx.find(".//" + XBRLI + "startDate")
        end = ctx.find(".//" + XBRLI + "endDate")
        if start is not None and end is not None:
            out[ctx.get("id")] = (start.text.strip(), end.text.strip())
    return out


def column_period(start, end):
    """Label a period the same way the schema does."""
    n = months_between(start, end)
    if n == 3:
        return "current_quarter"
    if n == 6:
        return "current_half_year"
    return f"other_{n}m"


def first_text(root, name):
    for el in root.iter():
        if isinstance(el.tag, str) and localname(el) == name:
            return (el.text or "").strip()
    return ""


def main():
    tag_to_item = {}
    with open(TAG_MAP, newline="") as f:
        for row in csv.DictReader(f):
            tag_to_item[row["xbrl_tag"]] = row["line_item"]

    figures, filings = [], []
    for path in sorted(RAW.glob("*.xml")):
        symbol, quarter, basis, submission = path.stem.rsplit("_", 3)
        root = etree.parse(str(path), PARSER).getroot()
        contexts = plain_duration_contexts(root)

        filings.append({
            "file": path.name,
            "symbol": symbol,
            "quarter": quarter,
            "basis": basis,
            "submission": submission,
            "level_of_rounding": first_text(root, "LevelOfRounding"),
            "type_of_reporting_period": first_text(root, "TypeOfReportingPeriod"),
            "nature_of_report": first_text(root, "NatureOfReportStandaloneConsolidated"),
            "periods_found": ";".join(column_period(s, e) for s, e in sorted(set(contexts.values()))),
        })

        for el in root:
            if not isinstance(el.tag, str):
                continue
            item = tag_to_item.get(localname(el))
            ctx = el.get("contextRef")
            if item is None or ctx not in contexts:
                continue
            start, end = contexts[ctx]
            figures.append({
                "file": path.name,
                "symbol": symbol,
                "quarter": quarter,
                "basis": basis,
                "submission": submission,
                "line_item": item,
                "column_period": column_period(start, end),
                "period_start": start,
                "period_end": end,
                "value_inr": (el.text or "").strip(),   # full rupees (EPS: rupees per share)
                "decimals": el.get("decimals"),
                "xbrl_tag": localname(el),
            })

    for out, rows in ((OUT_FIGURES, figures), (OUT_FILINGS, filings)):
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    print(f"{len(filings)} XBRL files -> {len(figures)} figures")
    print(f"Wrote {OUT_FIGURES.relative_to(ROOT)} and {OUT_FILINGS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
