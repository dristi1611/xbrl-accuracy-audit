# How accurate is India's machine-readable results data?

When a listed company files its quarterly results, do the machine-readable XBRL figures match the company's own PDF? Where they don't, why not?

Data firms and banks load XBRL straight into their databases, so a wrong unit or sign in the XBRL reaches every analyst downstream. This project reconciles the XBRL and PDF versions of Q2 FY27 (July to September 2026) results for a random sample of NSE-listed companies. It sorts every gap by root cause and logs each one as an exception.

**Status:** checks 1 to 3 run on all 40 companies. Every extracted PDF value is either confirmed by an XBRL figure or checked by eye. Publishing on 13 Dec 2026.

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

**Profit before tax and associates.** The SEBI XBRL taxonomy adds the share of profit of associates and joint ventures *after* tax, so XBRL `ProfitBeforeTax` excludes it. 24 of the 39 consolidated PDFs put it above profit before tax. For those, check 1 adds the XBRL associates figure back before comparing (`presentation` table). This is a difference in definition, not an error.

## Results (40 companies)

### Check 1: XBRL vs PDF, Q2 FY27

**15 of 78 statements** (9 of 40 companies) had at least one XBRL figure that did not match the company's own PDF. 1,221 of 1,288 comparisons matched exactly. Every one of the 67 exceptions was traced to a cause:

| Company | Size | What differs | Category |
|---|---|---|---|
| Coal India | Large | Q2 XBRL filed as "Half Yearly": no Jul–Sep quarter figures, standalone or consolidated (17 values). Half-year figures match. | missing |
| Emami | Small | Same pattern (17 values). Last year's Q2 was filed as "Quarterly". | missing |
| Vedanta Power | Small | Same pattern (16 values). | missing |
| Firstsource | Small | XBRL revenue includes the PDF's separate "other operating income, net" line. | wrong line |
| ACC | Small | XBRL revenue includes the PDF's separate "government grants" line (₹23 crore). | wrong line |
| Mahindra & Mahindra | Large | XBRL revenue includes the PDF's separate "income from investments in subsidiaries, associates and JVs" line (₹1,804 crore standalone). | wrong line |
| Welspun Living | Small | Consolidated XBRL EPS is the PDF's EPS *before* exceptional items (1.86 vs 1.80 for the quarter). | wrong line |
| Tech Mahindra | Large | Consolidated half-year: share of associates (₹-43 million) tagged as an exceptional item. PBT agrees. | wrong line |
| Afcons | Small | Consolidated half-year EPS in the XBRL (4.59) is the standalone figure; the PDF shows 1.94. | standalone and consolidated swapped |

What the pattern says:
- **"Half Yearly" in a quarterly filing is the biggest single cause.** 6 of 79 Q2 FY27 XBRL files (3 companies) carry only April–September figures. A database that reads the quarter from the XBRL gets nothing for these companies. Laurus Labs made the same mistake in Q2 FY26 and fixed it by revision 92 days later (check 2).
- **3 of the 5 "wrong line" cases come from the taxonomy, not the filer.** The SEBI taxonomy has only two income lines, `RevenueFromOperations` and `OtherIncome`. When a PDF prints a third income line, the XBRL has to fold it into one of them, so XBRL revenue differs from printed revenue even though total income agrees. Anyone using XBRL revenue for these companies is using a different number from the one the company reports.
- **By size:** 6 of 10 small companies had an exception, 3 of 15 large and 0 of 15 mid. The sample is too small to say this holds in general.

### Check 2: revisions

8 revised XBRL files from 4 companies across the three quarters downloaded (`output/check2_revisions.csv`). Adani Ports, Prestige and Rubicon filed revisions within 20 minutes of the original, with no stated reason and no changed facts. Laurus Labs revised both Q2 FY26 files 92 days later ("incorrect selection of Reporting Type"). The original consolidated file was "Half Yearly", and the original standalone file is truncated, invalid XML as NSE serves it (checked with three downloads).

### Check 3: restatements

Q1 FY27 and Q2 FY26 XBRL as first filed, compared with the "preceding quarter" and "same quarter last year" columns of the Q2 FY27 PDF. 1,157 of 1,255 comparisons agree (10 of them within rounding). The 98 exceptions (16 companies):

- **Restated, with the reason given in the PDF (10 companies, 69 values).** Mergers: Adani Ports, JSW Steel and Maruti Suzuki. Discontinued operations re-presented: L&T Technology Services, Swiggy and United Spirits. A JV's accounting-policy change: Grasim. A bonus issue (EPS only): Trent. Regrouping: ACC and Coal India. Coal India's reconciliation lists "previously reported" figures that equal the first-filed XBRL exactly (consolidated Q2 FY26 revenue ₹30,187 crore, now ₹36,553 crore).
- **The same tagging pattern as check 1 (5 companies, 13 values).** ACC, Firstsource, M&M and TI India fold a third income line into revenue or other income, and Tech Mahindra tags associates as exceptional in Q2 FY26 as well. These are recurring habits, not one-off slips.
- **Missing (15 values).** Laurus Labs' first-filed Q2 FY26 XBRL had no quarter figures (see check 2).
- **Unexplained (1 value).** Afcons' Q2 FY26 consolidated EPS was filed as 2.86 and now shows as 2.85, with no note.

A database that stores the first-filed XBRL and never re-reads it holds the old figures for these 10 restated companies. That is expected, but users need to know about it.

The full list with a note for each exception is in `output/error_log.csv`. Every comparison is in `output/check1_results.csv` and `output/check3_results.csv`.

Also noted:
- Emami's PDF uses an EBITDA layout, where "Total Expenses" excludes finance costs and depreciation. The comparable total is derived by adding them back (noted in `data/pdf_extract/EMAMILTD.csv`).
- Power Grid's PBT is before the regulatory deferral account movement; net profit and EPS include it. L&T Technology Services, Swiggy and United Spirits print PBT for continuing operations only. Net profit and EPS include discontinued operations, as the XBRL does.
- Gallantt Ispat's PDF has no standalone statement, and its standalone and consolidated XBRL are nearly identical. Its standalone XBRL is not compared.
- Vedanta Power and VISL have no Q2 FY26 filing (listed after demergers), so their year-ago comparison does not apply.

## Pilot-week findings

Results PDFs are not part of the integrated filing record. They come from the board-meeting outcome or financial-results announcement on the same exchange, filed a few hours before the XBRL.

Answered during week 1 (23 to 29 Nov 2026):

1. Are the NSE and BSE copies of the same filing identical? _TBD_
2. Does the NSE site block scripted downloads? From outside a browser, yes: plain scripted requests are refused. Inside a normal browser session, NSE's own listing feeds (`/api/integrated-filing-results`, `/api/corporate-announcements`) return every filing with its file links and timestamps. That is how the pilot file list in `data/download_log_pilot.csv` was built.
3. How does the XBRL mark units (the rounding field and the decimals attribute)? Every XBRL value is in full rupees. `LevelOfRounding` (Crores, Lakhs or Millions in the pilot) records the unit the company reports in, and each fact's `decimals` attribute records its precision (-5 = to the nearest ₹1 lakh). The parser reads the raw .xml, not the web view.
4. How are revised filings listed, and does the original stay visible? A revision is a separate row marked "Revision" with its own timestamp and an optional remarks field. The original stays listed next to it.
5. How does each company sign exceptional items, and where does the share of associates and joint ventures sit? The PDFs differ. Some print a loss in brackets and add it (Adani Ports), some print it as a positive number and subtract it (Welspun), and some label the column "net expense/(income)" (Firstsource). The XBRL always stores a loss as a negative number, and the extracted PDF figures use that convention. Associates: 6 of 9 consolidated PDFs put the share above profit before tax. CONCOR adds it after tax, as the XBRL taxonomy does. Ajanta and Firstsource show no associate amounts (see Checks).
6. Time per company in the pilot, and the resulting full-run size (40 or 30): download, parsing and checks are scripted. The remaining hand work is checking each AI-extracted PDF value by eye. The pilot eye check took under 45 minutes per company, so the full run covers 40.

## How AI was used

- An AI tool (Claude) wrote the first draft of the scripts and SQL. I reviewed, ran and committed every file and can explain each step.
- An AI tool (Claude) read the results tables from the PDFs into `data/pdf_extract/*.csv`, with the page number for every row. For native PDFs it read the text layer; for scanned ones, page images. All 390 arithmetic checks pass (78 statements).
- Pilot (10 companies): the 282 values that exactly match the XBRL are confirmed by an independent source. The other 362 got a second read (`output/eye_check_list.csv`, column `claude_second_read`) and my eye check (`checked_by_eye`).
- Full run (30 more companies): 1,794 of 1,952 values match an XBRL figure in check 1 or check 3. The other 158 got a second read (85 by a fresh text or OCR read that found each value on the right row and in the right column, 73 by re-reading the page image) and my eye check on 24 Nov 2026 (`output/eye_check_list_full.csv`, columns `claude_second_read` and `checked_by_eye`). Neither found a correction. 18 statements were first read by an automatic text pass. All of them were then compared with the page image, and 7 needed a correction: a value cut short, a column shifted, EPS before exceptional items taken instead of after, continuing-operations profit taken instead of total, and an after-tax associates line read with the wrong sign. The arithmetic checks could not catch these because they all sit below PBT. The XBRL comparison caught 6, and the page-image check caught 1. That is why every unconfirmed value still gets a check by eye.
- An AI tool proposed the category and note for each exception. Each was verified against the raw XBRL and the PDF.

## Data and limits

- Public data only: exchange filings and company websites. Each figure keeps its filing link and filing date.
- Results describe this sample. A gap between two versions of a figure is a data-quality finding, not a statement that any company acted wrongly.

## Layout

```
scripts/   draw_sample.py, parse_xbrl.py, check_pdf_arithmetic.py, load.py, run_check1.py, run_check2.py,
           run_check3.py, build_error_log.py, build_eye_check_list.py
sql/       schema.sql, check1_xbrl_vs_pdf.sql, check3_restatements.sql (check 2 compares XML files directly)
data/      index_lists/, sample.csv, download_log_pilot.csv, download_log_full.csv, tag_map.csv, pdf_extract/,
           raw/ (XBRL .xml; PDFs linked in the download logs)
output/    check1_*.csv, check2_revisions.csv, check3_*.csv, error_log.csv, pdf_arithmetic_checks.csv,
           eye_check_list.csv (pilot), eye_check_list_full.csv (full run)

Rebuild everything:
  python scripts/parse_xbrl.py && python scripts/check_pdf_arithmetic.py && python scripts/load.py
  python scripts/run_check1.py && python scripts/run_check2.py && python scripts/run_check3.py
  python scripts/build_error_log.py && python scripts/build_eye_check_list.py
```
