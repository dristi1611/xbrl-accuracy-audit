-- Check 3: restatements. Do the comparative columns in the Q2 FY27 PDF agree
-- with the XBRL the company filed for those periods at the time?
--
--   PDF 'preceding_quarter' (Apr-Jun 2026)      vs  Q1 FY27 XBRL, first filed
--   PDF 'same_quarter_last_year' (Jul-Sep 2025) vs  Q2 FY26 XBRL, first filed
--
-- A gap here means the figure changed between the two filings (a restatement,
-- a re-presentation for a merger, demerger or discontinued business, or a
-- regrouping), or that one of the two versions is wrong. Each gap is read
-- against the PDF's own notes before it gets a category.
--
-- Tolerance, PBT adjustment and status rules are the same as check 1.

WITH pdf AS (
    SELECT f.company_id, f.basis, g.line_item, g.column_period, g.value_inr, g.tolerance_inr, g.note
    FROM figures g JOIN filings f ON f.filing_id = g.filing_id
    WHERE f.source = 'pdf' AND f.quarter = 'Q2FY27'
      AND g.column_period IN ('preceding_quarter', 'same_quarter_last_year')
),
xbrl AS (
    -- the earlier filings' own 'current_quarter' column, relabelled to the PDF column it should match
    SELECT f.company_id, f.basis, g.line_item,
           CASE f.quarter WHEN 'Q1FY27' THEN 'preceding_quarter' ELSE 'same_quarter_last_year' END AS column_period,
           g.value_inr, g.tolerance_inr
    FROM figures g JOIN filings f ON f.filing_id = g.filing_id
    WHERE f.source = 'xbrl' AND f.quarter IN ('Q1FY27', 'Q2FY26') AND f.is_revision = 0
      AND g.column_period = 'current_quarter'
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
-- companies with no filing at all for the period are 'not applicable', not missing
WHERE EXISTS (SELECT 1 FROM filings f WHERE f.company_id = (SELECT company_id FROM companies WHERE symbol = j.symbol)
              AND f.source = 'xbrl' AND f.basis = j.basis
              AND f.quarter = CASE j.column_period WHEN 'preceding_quarter' THEN 'Q1FY27' ELSE 'Q2FY26' END)
ORDER BY j.symbol, j.basis, j.column_period, j.line_item;
