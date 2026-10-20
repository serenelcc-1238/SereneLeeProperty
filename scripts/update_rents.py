#!/usr/bin/env python3
"""
Refresh HDB median rents (whole-flat rentals) from data.gov.sg.

Dataset: "Median Rent by Town and Flat Type" (HDB), quarterly. HDB publishes each
quarter's figures about 4 weeks after the quarter ends (e.g. Q2 on 24 Jul 2026),
and data.gov.sg is updated the same day. This runs every Monday in the market-data
workflow, so a new quarter reaches the site within a week of release.

Writes data/rents.json:
  {"quarter": "2026-Q2", "fetched": "...", "source": "...",
   "towns": {"WOODLANDS": {"3": 2600, "4": 3100, ...}, ...},
   "prev_year": {...same shape, the quarter one year earlier...}}

HDB leaves a cell blank ("na" or "-") when a town and flat type had too few
rentals that quarter; those are simply left out. If the download fails, the
previous file is kept and the script exits with code 2 (a warning, not a failure).
Standard library only.
"""
import csv, io, json, os, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
OUT = os.path.join(ROOT, "rents.json")
DATASET = "d_23000a00c52996c55106084ed0339566"
PAGE = f"https://data.gov.sg/datasets/{DATASET}/view"
SGT = timezone(timedelta(hours=8))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
TOWN_ALIAS = {"CENTRAL": "CENTRAL AREA"}  # rent file name -> resale file name
FT = {"1-RM": "1", "2-RM": "2", "3-RM": "3", "4-RM": "4", "5-RM": "5", "EXEC": "E"}


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            if i == tries - 1:
                raise
            print(f"  retry after {e}", flush=True)
            time.sleep(5 * (i + 1))


def rows():
    base = f"https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET}"
    url = (json.loads(get(base + "/initiate-download")).get("data") or {}).get("url")
    for _ in range(15):
        if url:
            break
        time.sleep(3)
        url = (json.loads(get(base + "/poll-download")).get("data") or {}).get("url")
    if not url:
        raise RuntimeError("data.gov.sg did not return a download link")
    return list(csv.DictReader(io.StringIO(get(url).decode("utf-8-sig"))))


def build(rs):
    by_q = {}
    for r in rs:
        q = (r.get("quarter") or "").strip()
        town = (r.get("town") or "").strip().upper()
        town = TOWN_ALIAS.get(town, town)
        ft = FT.get((r.get("flat_type") or "").strip().upper())
        v = (r.get("median_rent") or "").strip().replace(",", "")
        if not (q and town and ft) or not v.replace(".", "").isdigit():
            continue
        by_q.setdefault(q, {}).setdefault(town, {})[ft] = int(float(v))
    if not by_q:
        raise RuntimeError("no rent figures found in the file")
    latest = max(by_q)
    y, n = latest.split("-Q")
    prev = f"{int(y) - 1}-Q{n}"
    if sum(len(v) for v in by_q[latest].values()) < 50:
        raise RuntimeError(f"{latest} looks incomplete")
    return {
        "quarter": latest,
        "label": f"Q{n} {y}",
        "fetched": datetime.now(SGT).strftime("%Y-%m-%dT%H:%M+08:00"),
        "source": "HDB, Median Rent by Town and Flat Type (data.gov.sg)",
        "url": PAGE,
        "towns": by_q[latest],
        "prev_year": by_q.get(prev, {}),
    }


def main():
    try:
        data = build(rows())
    except Exception as e:
        print(f"Rents not refreshed ({e}); keeping the previous file.")
        return 2
    old = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            old = json.load(f)
    if old.get("quarter") == data["quarter"] and old.get("towns") == data["towns"]:
        print(f"Rents unchanged ({data['label']}).")
        return 0
    with open(OUT, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"Rents updated to {data['label']}: {len(data['towns'])} towns.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
