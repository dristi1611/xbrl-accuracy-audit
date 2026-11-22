# How accurate is India's machine-readable results data?

When a listed company files its quarterly results, do the machine-readable XBRL figures match the company's own PDF? Where they don't, why not?

Data firms and banks load XBRL straight into their databases, so a wrong unit or sign in the XBRL reaches every analyst downstream. This project reconciles the XBRL and PDF versions of Q2 FY27 (July to September 2026) results for a random sample of NSE-listed companies. It sorts every gap by root cause and logs each one as an exception.

**Status:** in progress. Week 1 is the pilot on 10 companies. Publishing on 13 Dec 2026.

## Sample

- 40 non-financial companies: 15 from the Nifty 50, 15 from the Nifty Midcap 150 and 10 from the Nifty Smallcap 250. The minimum is 30, decided before any results were seen.
- Drawn at random with a fixed seed (`random.seed(2026)`) by `scripts/draw_sample.py`. Run the script on the same index lists and you get the same companies.
- Excluded: the whole "Financial Services" industry as NSE tags it. Banks, NBFCs and insurers file results in a different format, so their line items don't compare with other companies'. Dropping the whole industry also removes a few exchanges and brokers that file in the normal format. The upside is one rule that needs no company-by-company judgement.
- 5 spare names per size group, used in draw order if a filing is missing.
- Index lists downloaded from niftyindices.com on 22 Nov 2026 (`data/index_lists/`). Eligible after exclusions: Nifty 50, 38 of 50; Midcap 150, 113 of 150; Smallcap 250, 213 of 251 (the list held 251 names on the download date).
- Pilot (week 1): the first 4 large, 3 mid and 3 small names in draw order (`pilot = Y` in `data/sample.csv`).

## Checks

Each check is a SQL query over the same tables (`sql/`). Every value is converted to rupees before comparing.

1. **XBRL vs PDF.** 9 line items for the quarter and the half-year, standalone and consolidated.
2. **Revisions.** Did a revised XBRL follow the original? Records the date and the company's stated reason.
3. **Restatement.** Last quarter's figures as first filed, compared with the "preceding 3 months" column a quarter later. The same comparison for the same quarter last year.

Every gap gets exactly one category: rounding, wrong scale or unit, sign flipped, wrong line, standalone and consolidated swapped, missing, restated or unexplained.

## Pilot-week findings

Answered during week 1 (23 to 29 Nov 2026):

1. Are the NSE and BSE copies of the same filing identical? _TBD_
2. Does the NSE site block scripted downloads? _TBD_
3. How does the XBRL mark units (the rounding field and the decimals attribute)? _TBD_
4. How are revised filings listed, and does the original stay visible? _TBD_
5. How does each company sign exceptional items, and where does the share of associates and joint ventures sit? _TBD_
6. Time per company in the pilot, and the resulting full-run size (40 or 30): _TBD_

## How AI was used

- An AI tool (Claude) wrote the first draft of the scripts and SQL. I reviewed, ran and committed every file and can explain each step.
- An AI tool extracted the results tables from the PDFs into CSV. Every extracted value was checked by eye against the PDF (`figures.checked_by_eye`). Arithmetic checks also run on each table (for example, revenue plus other income equals total income) to catch extraction slips.

## Data and limits

- Public data only: exchange filings and company websites. Each figure keeps its filing link and filing date.
- Results describe this sample. A gap between two versions of a figure is a data-quality finding, not a statement that any company acted wrongly.

## Layout

```
scripts/   draw_sample.py, download.py, parse_xbrl.py, load.py
sql/       schema.sql, check1_xbrl_vs_pdf.sql, check2_revisions.sql, check3_restatements.sql
data/      index_lists/, sample.csv, tag_map.csv, raw/ (filings), audit.db
output/    error_log.csv, charts, dashboard (.pbix) and screenshots
```
