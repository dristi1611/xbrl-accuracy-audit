-- Schema for the XBRL accuracy audit (SQLite).
--
-- Three core tables, one row per thing:
--   companies : one row per company in the sample
--   filings   : one row per file (an XBRL file or a PDF; standalone or consolidated; original or revised)
--   figures   : one row per number we read out of a file
-- plus error_log: one row per gap a check flags, with the category we gave it after checking by hand.
--
-- Every value is stored twice: as reported (in the filing's own unit) and converted
-- to rupees (value_inr). All comparisons use value_inr, so a filing in lakhs can be
-- compared with one in crores.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    company_id    INTEGER PRIMARY KEY,
    symbol        TEXT NOT NULL UNIQUE,          -- NSE symbol, e.g. TATASTEEL
    company_name  TEXT NOT NULL,
    isin          TEXT,
    industry      TEXT,
    size_group    TEXT NOT NULL CHECK (size_group IN ('Large', 'Mid', 'Small')),
    pilot         TEXT NOT NULL DEFAULT 'N' CHECK (pilot IN ('Y', 'N'))
);

CREATE TABLE IF NOT EXISTS filings (
    filing_id         INTEGER PRIMARY KEY,
    company_id        INTEGER NOT NULL REFERENCES companies(company_id),
    source            TEXT NOT NULL CHECK (source IN ('xbrl', 'pdf')),
    exchange          TEXT CHECK (exchange IN ('NSE', 'BSE', 'IR')),   -- IR = company's own website
    basis             TEXT NOT NULL CHECK (basis IN ('standalone', 'consolidated')),
    quarter           TEXT NOT NULL,             -- the quarter the filing reports: 'Q2FY27', 'Q1FY27', 'Q2FY26'
    is_revision       INTEGER NOT NULL DEFAULT 0 CHECK (is_revision IN (0, 1)),
    revises_filing_id INTEGER REFERENCES filings(filing_id),           -- for a revision: the filing it replaces
    revision_remarks  TEXT,                      -- the company's own explanation, copied as written
    unit_reported     TEXT NOT NULL CHECK (unit_reported IN ('rupees', 'thousands', 'lakhs', 'millions', 'crores')),
    filing_date       TEXT NOT NULL,             -- YYYY-MM-DD
    link              TEXT NOT NULL,             -- where the file was downloaded from
    local_file        TEXT                       -- path under data/raw/
);

-- Rupees per reported unit, so conversions are written once, here.
CREATE TABLE IF NOT EXISTS units (
    unit_reported  TEXT PRIMARY KEY,
    rupees_per_unit REAL NOT NULL
);
INSERT OR IGNORE INTO units VALUES
    ('rupees',    1),
    ('thousands', 1000),
    ('lakhs',     100000),
    ('millions',  1000000),
    ('crores',    10000000);

CREATE TABLE IF NOT EXISTS figures (
    figure_id       INTEGER PRIMARY KEY,
    filing_id       INTEGER NOT NULL REFERENCES filings(filing_id),
    line_item       TEXT NOT NULL CHECK (line_item IN (
                        'revenue_from_operations',
                        'other_income',
                        'total_income',
                        'total_expenses',
                        'exceptional_items',
                        'share_of_associates_jv',     -- consolidated only
                        'profit_before_tax',
                        'net_profit',
                        'basic_eps')),
    column_period   TEXT NOT NULL CHECK (column_period IN (
                        'current_quarter',            -- e.g. Jul-Sep 2026
                        'preceding_quarter',          -- Apr-Jun 2026 (PDF only)
                        'same_quarter_last_year',     -- Jul-Sep 2025 (PDF only)
                        'current_half_year',          -- Apr-Sep 2026
                        'previous_half_year',         -- Apr-Sep 2025 (PDF only)
                        'previous_year')),            -- FY26 (PDF only)
    value_reported  REAL,                        -- as printed, in the filing's unit (EPS in rupees per share)
    value_inr       REAL,                        -- converted to rupees (EPS left as is)
    tolerance_inr   REAL,                        -- half of one printed unit, in rupees (rounding allowance)
    extracted_by    TEXT NOT NULL CHECK (extracted_by IN ('xbrl_parser', 'ai_pdf', 'hand')),
    checked_by_eye  INTEGER NOT NULL DEFAULT 0 CHECK (checked_by_eye IN (0, 1)),
    note            TEXT,
    UNIQUE (filing_id, line_item, column_period)
);

-- Where each company's PDF puts the share of associates/JVs. The SEBI XBRL
-- taxonomy adds it after tax, so XBRL ProfitBeforeTax excludes it. If the PDF
-- adds it above PBT, check 1 adds it back to the XBRL figure before comparing.
CREATE TABLE IF NOT EXISTS presentation (
    company_id        INTEGER NOT NULL REFERENCES companies(company_id),
    basis             TEXT NOT NULL,
    associates_in_pbt INTEGER NOT NULL CHECK (associates_in_pbt IN (0, 1)),
    PRIMARY KEY (company_id, basis)
);

CREATE TABLE IF NOT EXISTS error_log (
    error_id        INTEGER PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(company_id),
    check_name      TEXT NOT NULL CHECK (check_name IN ('xbrl_vs_pdf', 'revision', 'restatement')),
    basis           TEXT NOT NULL,
    line_item       TEXT NOT NULL,
    column_period   TEXT NOT NULL,
    value_a_inr     REAL,                        -- XBRL value (check 1) or as first filed (check 3)
    value_b_inr     REAL,                        -- PDF value (check 1) or as shown a quarter later (check 3)
    category        TEXT CHECK (category IN (
                        'rounding', 'wrong_scale_or_unit', 'sign_flipped', 'wrong_line',
                        'standalone_consolidated_swapped', 'missing', 'restated', 'unexplained')),
    note            TEXT                         -- one line: what the gap is and why
);
