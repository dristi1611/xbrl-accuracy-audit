"""
Build data/audit.db (SQLite) from the files the other scripts produce.

Inputs:
  data/sample.csv              companies (pilot rows only for now)
  data/download_log_pilot.csv  link and exchange timestamp for every file
  data/xbrl_filings.csv        one row per XBRL file (from parse_xbrl.py)
  data/xbrl_figures.csv        the 9 line items from each XBRL file
  data/pdf_extract/*.csv       the same line items read from each results PDF
  data/pdf_presentation.csv    where each PDF puts the share of associates

Every amount is stored twice: as reported (in the filing's own unit) and in
rupees (value_inr). EPS stays in rupees per share. Each figure also carries a
tolerance: half of one unit as printed, converted to rupees. A gap within that
tolerance is rounding, not an error.

Run from the repository root:
    python scripts/load.py
"""

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "audit.db"
DATA = ROOT / "data"

RUPEES_PER_UNIT = {"rupees": 1, "thousands": 1e3, "lakhs": 1e5, "millions": 1e6, "crores": 1e7}
XBRL_UNIT = {"Rupees": "rupees", "Thousands": "thousands", "Lakhs": "lakhs", "Millions": "millions", "Crores": "crores"}
PDF_PERIODS = ["current_quarter", "preceding_quarter", "same_quarter_last_year", "current_half_year"]
NINE = {"revenue_from_operations", "other_income", "total_income", "total_expenses", "exceptional_items",
        "share_of_associates_jv", "profit_before_tax", "net_profit", "basic_eps"}


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def decimals(s):
    return len(s.split(".")[1]) if "." in s else 0


def main():
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    con.executescript((ROOT / "sql" / "schema.sql").read_text())

    # Companies. File names drop '&' from symbols (GVT&D -> GVTD), so key on that.
    company_id = {}
    for r in read(DATA / "sample.csv"):
        if r["pilot"] != "Y":
            continue
        cur = con.execute(
            "INSERT INTO companies (symbol, company_name, isin, industry, size_group, pilot) VALUES (?,?,?,?,?,?)",
            (r["symbol"], r["company_name"], r["isin"], r["industry"], r["size_group"], r["pilot"]))
        company_id[r["symbol"].replace("&", "")] = cur.lastrowid

    log = {r["local_file"]: r for r in read(DATA / "download_log_pilot.csv")}

    def filing_date(file):
        d = log[file]["exchange_datetime"][:11]           # e.g. 28-Oct-2026
        from datetime import datetime
        return datetime.strptime(d.title(), "%d-%b-%Y").date().isoformat()

    # XBRL filings and figures
    filing_id = {}
    for r in read(DATA / "xbrl_filings.csv"):
        unit = XBRL_UNIT[r["level_of_rounding"]]
        cur = con.execute(
            """INSERT INTO filings (company_id, source, exchange, basis, quarter, is_revision,
                                    unit_reported, filing_date, link, local_file)
               VALUES (?, 'xbrl', 'NSE', ?, ?, ?, ?, ?, ?, ?)""",
            (company_id[r["symbol"]], r["basis"], r["quarter"], int(r["submission"] == "revision"),
             unit, filing_date(r["file"]), log[r["file"]]["link"], "data/raw/" + r["file"]))
        filing_id[r["file"]] = (cur.lastrowid, unit)

    for r in read(DATA / "xbrl_figures.csv"):
        fid, unit = filing_id[r["file"]]
        v = float(r["value_inr"])
        is_eps = r["line_item"] == "basic_eps"
        con.execute(
            """INSERT INTO figures (filing_id, line_item, column_period, value_reported, value_inr,
                                   tolerance_inr, extracted_by, checked_by_eye)
               VALUES (?,?,?,?,?,?, 'xbrl_parser', 0)""",   # read by code; the eye check applies to PDF figures
            (fid, r["line_item"], r["column_period"],
             v if is_eps else v / RUPEES_PER_UNIT[unit], v,
             None if r["decimals"] in (None, "", "INF") else 0.5 * 10 ** -int(r["decimals"])))

    # PDF filings and figures: one filing row per company and basis, pointing at the results PDF
    for path in sorted((DATA / "pdf_extract").glob("*.csv")):
        rows = read(path)
        for basis in sorted({r["basis"] for r in rows}):
            first = next(r for r in rows if r["basis"] == basis)
            sym, unit = first["symbol"], first["unit"]
            pdf_file = f"{sym}_Q2FY27_results.pdf"
            cur = con.execute(
                """INSERT INTO filings (company_id, source, exchange, basis, quarter, is_revision,
                                        unit_reported, filing_date, link, local_file)
                   VALUES (?, 'pdf', 'NSE', ?, 'Q2FY27', 0, ?, ?, ?, ?)""",
                (company_id[sym], basis, unit, filing_date(pdf_file), log[pdf_file]["link"], "data/raw/" + pdf_file))
            fid = cur.lastrowid
            amounts = [r for r in rows if r["basis"] == basis and r["line_item"] in NINE]
            amt_dec = max(decimals(r[p]) for r in amounts if r["line_item"] != "basic_eps" for p in PDF_PERIODS)
            for r in amounts:
                is_eps = r["line_item"] == "basic_eps"
                dec = max(decimals(r[p]) for p in PDF_PERIODS) if is_eps else amt_dec
                scale = 1 if is_eps else RUPEES_PER_UNIT[unit]
                for p in PDF_PERIODS:
                    v = float(r[p])
                    con.execute(
                        """INSERT INTO figures (filing_id, line_item, column_period, value_reported, value_inr,
                                               tolerance_inr, extracted_by, checked_by_eye, note)
                           VALUES (?,?,?,?,?,?, 'ai_pdf', 0, ?)""",
                        (fid, r["line_item"], p, v, round(v * scale, 2), 0.5 * 10 ** -dec * scale,
                         f"page {r['page']}" + (f"; {r['note']}" if r["note"] else "")))

    # Mark PDF figures checked by eye, from the ticked eye-check list. (The other PDF figures
    # are confirmed by an exact match with the XBRL, an independent source; see check 1.)
    eye = DATA.parent / "output" / "eye_check_list.csv"
    if eye.exists():
        for r in read(eye):
            if r["checked_by_eye"].startswith("Y"):
                con.execute(
                    """UPDATE figures SET checked_by_eye = 1
                       WHERE extracted_by = 'ai_pdf' AND line_item = ? AND column_period = ?
                         AND filing_id IN (SELECT f.filing_id FROM filings f JOIN companies c USING (company_id)
                                           WHERE f.source = 'pdf' AND c.symbol = ? AND f.basis = ?)""",
                    (r["line_item"], r["column_period"], r["symbol"], r["basis"]))

    for r in read(DATA / "pdf_presentation.csv"):
        con.execute("INSERT INTO presentation VALUES (?,?,?)",
                    (company_id[r["symbol"]], r["basis"], int(r["associates_in_pbt"])))

    con.commit()
    for t in ("companies", "filings", "figures", "presentation"):
        print(f"{t:13} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:5} rows")
    con.close()


if __name__ == "__main__":
    main()
