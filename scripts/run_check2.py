"""
Check 2: revisions. For every XBRL filing that was revised, compare the original
with the revision fact by fact and record what changed.

A "fact" is one tagged value in one context (period/dimension). We compare:
  - all facts in the file (how much of the filing changed at all), and
  - the 9 line items used in check 1, for the plain quarter and half-year contexts.
Also recorded: hours between original and revision, the company's stated reason
(from the exchange listing), and the reporting-period type before and after.

Output: output/check2_revisions.csv (one row per revised filing).

Run from the repository root:
    python scripts/run_check2.py
"""

import csv
from datetime import datetime
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RECOVER = etree.XMLParser(huge_tree=True, recover=True)
XBRLI = "{http://www.xbrl.org/2003/instance}"


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def facts(path):
    """All facts keyed by (tag, context period + dimensions), so context ids that differ don't matter."""
    root = etree.parse(str(path), RECOVER).getroot()
    ctx = {}
    for c in root.iter(XBRLI + "context"):
        per = "|".join(x.text.strip() for x in c.iter() if etree.QName(x).localname in ("startDate", "endDate", "instant") and x.text)
        dims = "|".join(sorted(etree.tostring(m, method="text", encoding="unicode").strip() + "@" + (m.get("dimension") or "")
                               for m in c.iter() if etree.QName(m).localname in ("explicitMember", "typedMember")))
        ctx[c.get("id")] = per + "#" + dims
    out = {}
    for el in root:
        if isinstance(el.tag, str) and el.get("contextRef"):
            out[(etree.QName(el).localname, ctx.get(el.get("contextRef"), "?"))] = (el.text or "").strip()
    return out


def when(s):
    return datetime.strptime(s.strip().title(), "%d-%b-%Y %H:%M:%S")


def main():
    log = {r["local_file"]: r for n in ("download_log_pilot.csv", "download_log_full.csv") for r in read(ROOT / "data" / n)}
    xf = {r["file"]: r for r in read(ROOT / "data" / "xbrl_filings.csv")}
    tag_map = {r["xbrl_tag"]: r["line_item"] for r in read(ROOT / "data" / "tag_map.csv")}

    rows = []
    for rev_file in sorted(f for f in log if f.endswith("_revision.xml")):
        orig_file = rev_file.replace("_revision.xml", "_original.xml")
        a, b = facts(RAW / orig_file), facts(RAW / rev_file)
        changed = [k for k in set(a) | set(b) if a.get(k) != b.get(k)]
        added = [k for k in b if k not in a]
        removed = [k for k in a if k not in b]
        changed_items = sorted({tag_map[t] for t, _ in changed if t in tag_map})
        hours = (when(log[rev_file]["exchange_datetime"]) - when(log[orig_file]["exchange_datetime"])).total_seconds() / 3600
        sym, quarter, basis, _ = rev_file[:-4].rsplit("_", 3)
        rows.append({
            "symbol": sym, "quarter": quarter, "basis": basis,
            "original_filed": log[orig_file]["exchange_datetime"], "revision_filed": log[rev_file]["exchange_datetime"],
            "hours_later": round(hours, 1),
            "stated_reason": log[rev_file].get("revision_remarks", "") or "(none given)",
            "original_valid_xml": xf[orig_file]["well_formed"],
            "reporting_type_before": xf[orig_file]["type_of_reporting_period"] or "(unreadable)",
            "reporting_type_after": xf[rev_file]["type_of_reporting_period"],
            "periods_before": xf[orig_file]["periods_found"], "periods_after": xf[rev_file]["periods_found"],
            "facts_original": len(a), "facts_revision": len(b),
            "facts_changed_or_added_or_removed": len(changed), "facts_added": len(added), "facts_removed": len(removed),
            "line_items_changed": ";".join(changed_items) or "none",
        })

    out = ROOT / "output" / "check2_revisions.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['symbol']:10} {r['quarter']} {r['basis'][:4]} +{r['hours_later']:>7}h  facts changed {r['facts_changed_or_added_or_removed']:>4} "
              f"(added {r['facts_added']}, removed {r['facts_removed']})  type {r['reporting_type_before']} -> {r['reporting_type_after']}  "
              f"items: {r['line_items_changed']}  reason: {r['stated_reason'][:60]}")


if __name__ == "__main__":
    main()
