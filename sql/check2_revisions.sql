-- Check 2: revisions. For every revised XBRL filing, what changed against the
-- original it replaces, how long after, and what reason the company gave?
--
-- One row per revised filing. Line-item comparison covers the 9 line items for
-- the quarter and half-year (the same figures as check 1). A figure counts as
-- changed when both versions have it and they differ by more than the coarser
-- tolerance; added when only the revision has it; removed when only the original has it.
--
-- scripts/run_check2.py goes further and compares every fact in the two XML files
-- (all tags, all contexts); its output is output/check2_revisions.csv.

WITH pairs AS (
    SELECT r.filing_id AS revision_id, o.filing_id AS original_id,
           c.symbol, c.size_group, r.quarter, r.basis,
           o.filed_at AS original_filed, r.filed_at AS revision_filed,
           ROUND((julianday(r.filed_at) - julianday(o.filed_at)) * 24, 1) AS hours_later,
           COALESCE(r.revision_remarks, '(none given)') AS stated_reason,
           COALESCE(o.reporting_type, '(unreadable)') AS reporting_type_before,
           r.reporting_type AS reporting_type_after,
           o.well_formed AS original_valid_xml
    FROM filings r
    JOIN filings o   ON o.filing_id = r.revises_filing_id
    JOIN companies c ON c.company_id = r.company_id
    WHERE r.source = 'xbrl' AND r.is_revision = 1
),
compared AS (
    -- full outer join of the two versions' figures, done as a union of both sides
    SELECT p.revision_id, a.line_item, a.column_period,
           a.value_inr AS before_inr, b.value_inr AS after_inr,
           MAX(COALESCE(a.tolerance_inr, 0.005), COALESCE(b.tolerance_inr, 0.005)) AS tol   -- EPS: half a paisa
    FROM pairs p
    JOIN figures a      ON a.filing_id = p.original_id
    LEFT JOIN figures b ON b.filing_id = p.revision_id
                       AND b.line_item = a.line_item AND b.column_period = a.column_period
    UNION ALL
    SELECT p.revision_id, b.line_item, b.column_period, NULL, b.value_inr, COALESCE(b.tolerance_inr, 0.005)
    FROM pairs p
    JOIN figures b ON b.filing_id = p.revision_id
    WHERE NOT EXISTS (SELECT 1 FROM figures a
                      WHERE a.filing_id = p.original_id
                        AND a.line_item = b.line_item AND a.column_period = b.column_period)
)
SELECT p.symbol, p.size_group, p.quarter, p.basis,
       p.original_filed, p.revision_filed, p.hours_later, p.stated_reason,
       p.reporting_type_before, p.reporting_type_after, p.original_valid_xml,
       SUM(x.before_inr IS NOT NULL AND x.after_inr IS NOT NULL
           AND ABS(x.before_inr - x.after_inr) > x.tol)            AS figures_changed,
       SUM(x.before_inr IS NULL)                                    AS figures_added,
       SUM(x.after_inr IS NULL)                                     AS figures_removed,
       SUM(x.before_inr IS NOT NULL AND x.after_inr IS NOT NULL
           AND ABS(x.before_inr - x.after_inr) <= x.tol)            AS figures_unchanged,
       COALESCE(GROUP_CONCAT(DISTINCT CASE WHEN x.before_inr IS NULL OR x.after_inr IS NULL
                                             OR ABS(x.before_inr - x.after_inr) > x.tol
                                           THEN x.line_item END), 'none') AS line_items_affected
FROM pairs p
LEFT JOIN compared x ON x.revision_id = p.revision_id
GROUP BY p.revision_id
ORDER BY p.symbol, p.quarter, p.basis;
