#!/usr/bin/env python3
"""
HDB block facts from data.gov.sg "HDB Property Information" (HDB, monthly):
top floor, year completed and the number of flats of each type in every block.

Writes data/hdb-blocks.json:
  {"fetched": "...", "source": "...", "url": "...",
   "blocks": {"WOODLANDS DR 50": {"898B": [maxFloor, yearCompleted, town, {"3": n, "4": n, ...}]}}}
Flat-type keys: 1, 2, 3, 4, 5, E (executive), M (multi-generation), S (studio / 2-room flexi).
Used by the door-knock log (block set-up) and available to the site.
If the download fails, the old file is kept and the script exits 2. Standard library only.
"""
import csv, io, json, os, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "hdb-blocks.json")
DATASET = "d_17f5382f26140b1fdae0ba2ef6239d2f"
UA = "Mozilla/5.0 (compatible; sereneleeproperty-bot)"
COLS = {"1room_sold": "1", "2room_sold": "2", "3room_sold": "3", "4room_sold": "4", "5room_sold": "5",
        "exec_sold": "E", "multigen_sold": "M", "studio_apartment_sold": "S",
        "1room_rental": "1", "2room_rental": "2", "3room_rental": "3", "other_room_rental": None}


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
                return r.read()
        except Exception as e:
            if i == tries - 1:
                raise
            print("  retry after", e, flush=True)
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
        raise RuntimeError("no download link")
    return list(csv.DictReader(io.StringIO(get(url).decode("utf-8-sig"))))


def main():
    try:
        rs = rows()
    except Exception as e:
        print("Block info not refreshed:", e)
        return 2
    out = {}
    for r in rs:
        if (r.get("residential") or "").strip().upper() != "Y":
            continue
        st = (r.get("street") or "").strip().upper()
        blk = (r.get("blk_no") or "").strip().upper()
        if not st or not blk:
            continue
        mix = {}
        for col, k in COLS.items():
            v = (r.get(col) or "0").strip()
            if k and v.isdigit() and int(v):
                mix[k] = mix.get(k, 0) + int(v)
        try:
            mf = int(float(r.get("max_floor_lvl") or 0))
        except ValueError:
            mf = 0
        yr = (r.get("year_completed") or "").strip()
        out.setdefault(st, {})[blk] = [mf, int(yr) if yr.isdigit() else None,
                                      (r.get("bldg_contract_town") or "").strip(), mix]
    if sum(len(v) for v in out.values()) < 5000:
        print("Block info looks incomplete; keeping the old file.")
        return 2
    data = {"fetched": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M+08:00"),
            "source": "HDB, HDB Property Information (data.gov.sg)",
            "url": f"https://data.gov.sg/datasets/{DATASET}/view", "blocks": out}
    with open(OUT, "w") as f:
        json.dump(data, f, separators=(",", ":"), sort_keys=True)
    print("Blocks:", sum(len(v) for v in out.values()), "streets:", len(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
