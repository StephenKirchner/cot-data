#!/usr/bin/env python3
"""Fetch CFTC Commitments of Traders data for the report universe.

Writes data/noncomm.json (Legacy non-commercial) and data/spec.json (TFF
leveraged funds for financials + Disaggregated managed money for commodities),
each as compact weekly rows [date, code, open_interest, long, short, spread]
from START_DATE onward. Standard library only, so it runs on a bare GitHub
Actions runner. No API token is needed (CFTC FAQ #13).

Usage: python fetch_cot.py [--report fut|com] [--start YYYY-MM-DD]
"""
import argparse
import csv
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://publicreporting.cftc.gov/resource/"

# Socrata dataset ids and the position fields of the speculative category.
DATASETS = {
    ("legacy", "fut"): ("6dca-aqww", "noncomm_positions_long_all", "noncomm_positions_short_all", "noncomm_postions_spread_all"),
    ("legacy", "com"): ("jun7-fc8e", "noncomm_positions_long_all", "noncomm_positions_short_all", "noncomm_postions_spread_all"),
    ("tff",    "fut"): ("gpe5-46if", "lev_money_positions_long", "lev_money_positions_short", "lev_money_positions_spread"),
    ("tff",    "com"): ("yw9f-hn96", "lev_money_positions_long", "lev_money_positions_short", "lev_money_positions_spread"),
    ("disagg", "fut"): ("72hh-3qpy", "m_money_positions_long_all", "m_money_positions_short_all", "m_money_positions_spread"),
    ("disagg", "com"): ("kh3c-gbw2", "m_money_positions_long_all", "m_money_positions_short_all", "m_money_positions_spread"),
}

CATEGORIES = {
    "noncomm": {"label": "Non-commercial", "sources": {"legacy": "all"}},
    "spec":    {"label": "Leveraged funds / Managed money", "sources": {"tff": "tff", "disagg": "disagg"}},
}


def soda_csv(dataset_id, select, where, order, page_size=50000, retries=4):
    """Page through a SODA CSV query; returns list of dict rows."""
    rows, offset = [], 0
    while True:
        q = {"$select": select, "$where": where, "$order": order, "$limit": page_size, "$offset": offset}
        url = API + dataset_id + ".csv?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers={"User-Agent": "cot-positioning-pipeline (python urllib)"})
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    text = r.read().decode("utf-8")
                break
            except Exception as e:  # transient API hiccups
                if attempt == retries - 1:
                    raise
                time.sleep(3 * (attempt + 1))
        page = list(csv.DictReader(io.StringIO(text)))
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size


def fetch(dataset_key, report, codes, start):
    ds_id, f_long, f_short, f_spread = DATASETS[(dataset_key, report)]
    select = (f"report_date_as_yyyy_mm_dd as d, cftc_contract_market_code as c, open_interest_all as oi, "
              f"{f_long} as l, {f_short} as s, {f_spread} as sp")
    where = ("cftc_contract_market_code in (" + ",".join(f"'{c}'" for c in codes) + ") "
             f"AND report_date_as_yyyy_mm_dd >= '{start}T00:00:00.000'")
    out = []
    for r in soda_csv(ds_id, select, where, "d,c"):
        try:
            out.append([r["d"][:10], r["c"].strip(), int(float(r["oi"])), int(float(r["l"])),
                        int(float(r["s"])), int(float(r["sp"] or 0))])
        except (KeyError, ValueError) as e:
            print(f"skipping malformed row {r}: {e}", file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default="fut", choices=["fut", "com"])
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--out", default=str(HERE / "data"))
    a = ap.parse_args()

    universe = json.loads((HERE / "universe.json").read_text(encoding="utf-8"))
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for cat, spec in CATEGORIES.items():
        rows = []
        for ds_key, which in spec["sources"].items():
            codes = [u["code"] for u in universe if which == "all" or u["spec_source"] == which]
            got = fetch(ds_key, a.report, codes, a.start)
            print(f"{cat}: {ds_key}/{a.report} {len(got)} rows for {len(codes)} codes")
            rows.extend(got)
        rows.sort(key=lambda r: (r[1], r[0]))
        as_of = max(r[0] for r in rows) if rows else None
        payload = {
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "category": cat, "label": spec["label"], "report": a.report,
            "start": a.start, "as_of": as_of, "n_rows": len(rows),
            "fields": ["date", "code", "oi", "long", "short", "spread"],
            "rows": rows,
        }
        path = out_dir / f"{cat}.json"
        path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        print(f"wrote {path} ({path.stat().st_size // 1024} KB), as of {as_of}")


if __name__ == "__main__":
    main()
