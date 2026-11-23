# How accurate is India's machine-readable results data?

When a listed company files its quarterly results, do the machine-readable XBRL figures match the company's own PDF? Where they don't, why not?

Data firms and banks load XBRL straight into their databases, so a wrong unit or sign in the XBRL reaches every analyst downstream. This project reconciles the XBRL and PDF versions of Q2 FY27 (July to September 2026) results for a random sample of NSE-listed companies. It sorts every gap by root cause and logs each one as an exception.

**Status:** in progress. The pilot on 10 companies is done (results below). The full run of 40 companies is next. Publishing on 13 Dec 2026.

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

Before check 1, `scripts/check_pdf_arithmetic.py` tests every extracted PDF statement: revenue plus other income must equal total income, and total income minus expenses (plus associates and exceptional items where shown) must equal profit before tax. A failure means an extraction slip, not a finding.

**Tolerance.** A gap is rounding if it is no more than half of one printed unit, whichever of the PDF and XBRL is coarser. A PDF in crores to 2 decimals allows ₹0.005 crore (₹50,000). A PDF in whole crores allows ₹0.5 crore.

**Profit before tax and associates.** The SEBI XBRL taxonomy adds the share of profit of associates and joint ventures *after* tax, so XBRL `ProfitBeforeTax` excludes it. Six of the nine consolidated pilot PDFs put it above profit before tax. For those, check 1 adds the XBRL associates figure back before comparing (`presentation` table). This is a difference in definition, not an error.

## Pilot results (10 companies, check 1)

In this sample, **7 of 19 Q2 FY27 statements** (4 of 10 companies) had at least one XBRL figure that did not match the company's own PDF. 282 of 322 comparisons matched exactly. The 40 exceptions come from four filings:

| Company | Size | What differs | Category |
|---|---|---|---|
| Coal India | Large | Q2 XBRL filed as "Half Yearly": no Jul–Sep quarter figures at all, standalone or consolidated (17 values). Half-year figures match. | missing |
| Emami | Small | Same pattern: "Half Yearly" XBRL with no quarter figures (17 values). Half-year figures match. Last year's Q2 was filed as "Quarterly". | missing |
| Firstsource | Small | XBRL revenue includes the PDF's separate "other operating income, net" line. The gap equals that line exactly, and total income agrees. | wrong line |
| Welspun Living | Small | Consolidated XBRL EPS is the PDF's EPS *before* exceptional items (1.86 vs 1.80 for the quarter). | wrong line |

The full list is in `output/error_log.csv`, and every comparison is in `output/check1_results.csv`. These are pilot numbers on 10 companies. The full run covers 40.

Also noted:
- Adani Ports filed a revised Q1 FY27 XBRL two minutes after the original, with no remarks. All 114 consolidated and 77 standalone facts are identical between the two files.
- Emami's PDF uses an EBITDA layout, where "Total Expenses" excludes finance costs and depreciation. The comparable total is derived by adding them back (noted in `data/pdf_extract/EMAMILTD.csv`).

## Pilot-week findings

Results PDFs are not part of the integrated filing record. They come from the board-meeting outcome or financial-results announcement on the same exchange, filed a few hours before the XBRL.

Answered during week 1 (23 to 29 Nov 2026):

1. Are the NSE and BSE copies of the same filing identical? _TBD_
2. Does the NSE site block scripted downloads? From outside a browser, yes: plain scripted requests are refused. Inside a normal browser session, NSE's own listing feeds (`/api/integrated-filing-results`, `/api/corporate-announcements`) return every filing with its file links and timestamps. That is how the pilot file list in `data/download_log_pilot.csv` was built.
3. How does the XBRL mark units (the rounding field and the decimals attribute)? Every XBRL value is in full rupees. `LevelOfRounding` (Crores, Lakhs or Millions in the pilot) records the unit the company reports in, and each fact's `decimals` attribute records its precision (-5 = to the nearest ₹1 lakh). The parser reads the raw .xml, not the web view.
4. How are revised filings listed, and does the original stay visible? A revision is a separate row marked "Revision" with its own timestamp and an optional remarks field. The original stays listed next to it.
5. How does each company sign exceptional items, and where does the share of associates and joint ventures sit? The PDFs differ. Some print a loss in brackets and add it (Adani Ports), some print it as a positive number and subtract it (Welspun), and some label the column "net expense/(income)" (Firstsource). The XBRL always stores a loss as a negative number, and the extracted PDF figures use that convention. Associates: 6 of 9 consolidated PDFs put the share above profit before tax. CONCOR adds it after tax, as the XBRL taxonomy does. Ajanta and Firstsource show no associate amounts (see Checks).
6. Time per company in the pilot, and the resulting full-run size (40 or 30): download, parsing and checks are scripted. The remaining hand work is checking each AI-extracted PDF value by eye (about 70 values per company). Time per company: _TBD after the eye check_.

## How AI was used

- An AI tool (Claude) wrote the first draft of the scripts and SQL. I reviewed, ran and committed every file and can explain each step.
- An AI tool (Claude) read the results tables from the PDFs, from page images for scanned or OCR'd PDFs and from the text layer for native ones, into `data/pdf_extract/*.csv`, with the page number for every row. All 95 arithmetic checks pass. The 282 values that exactly match the XBRL are confirmed by an independent source. The other 362 got a second read: 212 by a fresh OCR pass that found each value in the right row, and the rest by re-reading the page image or text layer (`output/eye_check_list.csv`, column `claude_second_read`). The second read found no corrections. My own eye check is recorded in the `checked_by_eye` column.
- An AI tool proposed the category and note for each exception. Each was verified against the raw XBRL and the PDF.

## Data and limits

- Public data only: exchange filings and company websites. Each figure keeps its filing link and filing date.
- Results describe this sample. A gap between two versions of a figure is a data-quality finding, not a statement that any company acted wrongly.

## Layout

```
scripts/   draw_sample.py, parse_xbrl.py, check_pdf_arithmetic.py, load.py, run_check1.py, build_error_log.py
sql/       schema.sql, check1_xbrl_vs_pdf.sql (check2, check3 to come)
data/      index_lists/, sample.csv, download_log_pilot.csv, tag_map.csv, pdf_extract/, raw/ (XBRL .xml; PDFs linked in the download log)
output/    check1_results.csv, check1_exceptions.csv, error_log.csv, pdf_arithmetic_checks.csv

Rebuild everything:  python scripts/parse_xbrl.py && python scripts/check_pdf_arithmetic.py && python scripts/load.py && python scripts/run_check1.py && python scripts/build_error_log.py
```
