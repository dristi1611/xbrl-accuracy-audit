-- Check 1: XBRL vs PDF, Q2 FY27.
--
-- One row per company x basis x line item x period (quarter and half-year),
-- starting from the PDF so that a figure missing from the XBRL still shows up.
--
-- Tolerance: half of one printed unit, the larger of the PDF's and the XBRL's.
-- Example: a PDF in crores to 2 decimals allows Rs 0.005 crore = Rs 50,000.
--
-- Profit before tax: the SEBI taxonomy adds the share of associates/JVs after
-- tax, so XBRL ProfitBeforeTax excludes it. Where the company's PDF puts that
-- share above PBT (table presentation), we add it back to the XBRL figure
-- before comparing. This is a difference in definition, not an error.
--
-- Status (decided by these rules before looking at any result):
--   match            identical
--   rounding         gap within tolerance
--   missing_in_xbrl  no XBRL fact for this line and period
--   sign_flipped     same size, opposite sign
--   scale_x<k>       one value is the other times a power of 10 (k)
--   gap              anything else: to be investigated by hand

WITH pdf AS (
    SELECT f.company_id, f.basis, g.line_item, g.column_period, g.value_inr, g.tolerance_inr, g.note
    FROM figures g JOIN filings f ON f.filing_id = g.filing_id
    WHERE f.source = 'pdf' AND f.quarter = 'Q2FY27'
      AND g.column_period IN ('current_quarter', 'current_half_year')
),
xbrl AS (
    SELECT f.company_id, f.basis, g.line_item, g.column_period, g.value_inr, g.tolerance_inr
    FROM figures g JOIN filings f ON f.filing_id = g.filing_id
    WHERE f.source = 'xbrl' AND f.quarter = 'Q2FY27' AND f.is_revision = 0
),
xbrl_comparable AS (
    -- XBRL figures put on the same footing as the PDF (PBT adjustment only)
    SELECT x.company_id, x.basis, x.line_item, x.column_period,
           x.value_inr
             + CASE WHEN x.line_item = 'profit_before_tax' AND COALESCE(pr.associates_in_pbt, 0) = 1
                    THEN COALESCE(a.value_inr, 0) ELSE 0 END AS value_inr,
           x.tolerance_inr,
           CASE WHEN x.line_item = 'profit_before_tax' AND COALESCE(pr.associates_in_pbt, 0) = 1
                THEN 1 ELSE 0 END AS pbt_adjusted
    FROM xbrl x
    LEFT JOIN presentation pr ON pr.company_id = x.company_id AND pr.basis = x.basis
    LEFT JOIN xbrl a ON a.company_id = x.company_id AND a.basis = x.basis
                    AND a.column_period = x.column_period AND a.line_item = 'share_of_associates_jv'
),
factors(k) AS (VALUES (10), (100), (1000), (100000), (1000000), (10000000)),
joined AS (
    SELECT c.symbol, c.size_group, p.basis, p.line_item, p.column_period,
           x.value_inr AS xbrl_inr, p.value_inr AS pdf_inr,
           x.value_inr - p.value_inr AS gap_inr,
           MAX(p.tolerance_inr, COALESCE(x.tolerance_inr, 0)) AS tol_inr,
           COALESCE(x.pbt_adjusted, 0) AS pbt_adjusted,
           p.note AS pdf_note
    FROM pdf p
    JOIN companies c ON c.company_id = p.company_id
    LEFT JOIN xbrl_comparable x ON x.company_id = p.company_id AND x.basis = p.basis
                               AND x.line_item = p.line_item AND x.column_period = p.column_period
)
SELECT j.*,
       CASE
         WHEN xbrl_inr IS NULL THEN 'missing_in_xbrl'
         WHEN gap_inr = 0 THEN 'match'
         WHEN ABS(gap_inr) <= tol_inr THEN 'rounding'
         WHEN pdf_inr <> 0 AND ABS(xbrl_inr + pdf_inr) <= tol_inr THEN 'sign_flipped'
         WHEN EXISTS (SELECT 1 FROM factors
                      WHERE ABS(xbrl_inr - pdf_inr * k) <= tol_inr * k
                         OR ABS(pdf_inr - xbrl_inr * k) <= tol_inr) AND pdf_inr <> 0
           THEN 'scale_x' || (SELECT k FROM factors
                              WHERE ABS(xbrl_inr - pdf_inr * k) <= tol_inr * k
                                 OR ABS(pdf_inr - xbrl_inr * k) <= tol_inr LIMIT 1)
         ELSE 'gap'
       END AS status
FROM joined j
ORDER BY j.symbol, j.basis, j.column_period, j.line_item;
