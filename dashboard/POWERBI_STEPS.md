# Building the Power BI dashboard

One page, built on two tables in this folder. About 45 minutes in Power BI Desktop (free, Windows).

- `exceptions.csv`: one row per exception (165), with company, size group, check, basis, line item, period, category, the XBRL and PDF values and a note.
- `statements.csv`: one row per statement and check (156), with `has_exception` = 1 or 0. This is what turns counts into shares.

Both are rebuilt by `python scripts/build_dashboard_data.py`.

## 1. Load the data (5 min)

1. Open Power BI Desktop, then **Home → Get data → Text/CSV**, and pick `dashboard/statements.csv`. Click **Load**.
2. Do the same for `dashboard/exceptions.csv`.
3. In **Table view**, check the types: `has_exception` and `exceptions` should be whole numbers. `xbrl_value` and `pdf_value` should be decimal numbers (blank XBRL values are fine).

## 2. Link the tables (2 min)

1. Open **Model view** (the third icon on the left).
2. Drag `statement_key` from `statements` onto `statement_key` in `exceptions`.
3. It should show **one-to-many** (1 on `statements`, * on `exceptions`) with a **single** cross-filter direction. Click **OK**.

Now a slicer on `statements` (size group, check, basis) filters both tables.

## 3. Add three measures (5 min)

Select the `exceptions` table, then **Home → New measure**, and enter each line:

```
Exceptions = COUNTROWS(exceptions)
Companies affected = DISTINCTCOUNT(exceptions[symbol])
Share of statements with an exception = DIVIDE(SUM(statements[has_exception]), COUNTROWS(statements))
```

Format the last one as a percentage: select it, then **Measure tools → %**, with 0 decimals.

## 4. Build the page (25 min)

Leave the top strip for the title and slicers. Then build:

| Visual | Fields | Settings |
|---|---|---|
| **Title** (Insert → Text box) | "XBRL vs PDF: Q2 FY27, 40 NSE companies" | 18 pt bold |
| **Slicers ×4** in one row along the top | `statements[check]`, `statements[size_group]`, `statements[basis]`, `exceptions[category]` | Style: Dropdown. Check slicer: single select, set to "Check 1: XBRL vs PDF" |
| **Card** | `Share of statements with an exception` | Title: "Statements with an exception" |
| **Card** | `Exceptions` | Title: "Exceptions (figures)" |
| **Card** | `Companies affected` | |
| **Clustered bar chart** | Y-axis `statements[size_group]`, X-axis `Share of statements with an exception` | Title: "Share of statements with an exception, by size group". Data labels on |
| **Clustered bar chart** | Y-axis `exceptions[category]`, X-axis `Companies affected` | Title: "Companies affected, by cause". Sort by value, descending |
| **Clustered bar chart** | Y-axis `exceptions[line_item]`, X-axis `Exceptions` | Title: "Exceptions by line item" |
| **Table** (bottom, full width) | `company`, `basis`, `line_item`, `period`, `category`, `xbrl_value`, `pdf_value`, `unit`, `note` | Turn on word wrap for `note` |

Keep it plain: one colour for all bars (the default blue is fine), no 3D, no pie charts. Light gridlines only.

## 5. Check it against the numbers (3 min)

With the check slicer on **Check 1** and nothing else selected, you should see:

- Statements with an exception: **19%** (15 of 78)
- Exceptions: **67**
- Companies affected: **9**
- By size group: Large **17%**, Mid **0%**, Small **53%**

With the check slicer on **Check 3**: exceptions **98**, companies affected **16**.

If a number differs, the usual causes are a missing relationship (step 2) or `has_exception` loaded as text (step 1).

## 6. Save and take two screenshots (5 min)

1. **File → Save as** `dashboard/xbrl_audit.pbix`.
2. Screenshot 1: the whole page with Check 1 selected. Use **Win + Shift + S** and save it as `dashboard/screenshot_check1.png`.
3. Screenshot 2: Check 1, with the size group slicer on Small and one row of the table selected. Save it as `dashboard/screenshot_small_caps.png`.
4. Add the three files to the repository: upload them on GitHub (**Add file → Upload files** in the `dashboard` folder) or put them in Drive.
