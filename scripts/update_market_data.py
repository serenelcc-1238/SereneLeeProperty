#!/usr/bin/env python3
"""
Weekly market data refresh for sereneleeproperty.com/market-map.html

Pulls two official datasets and writes:
  data/market-data.json      quarterly totals for the map, filters and charts
  data/hdb/index.json        every street and block with a resale deal in the last 3 years
  data/hdb/<town>.json       those resale deals, by street and block (for "Check my block")
  data/hdb/million.json      every resale of $1,000,000 or more in the same 36 months
  data/ura/projects.json     every private project with a deal in the last 5 years
  data/ura/d<NN>.json        those deals, by project (for "Check my condo")

Sources:
  1. HDB resale transactions (data.gov.sg, no key needed)
  2. URA private residential transactions (URA Data Service, needs URA_ACCESS_KEY)

If one source fails, the previous files for that source are kept and the
script exits with code 2 so the GitHub run shows a warning, but the site
still gets whatever did refresh.

Standard library only, so nothing needs installing.
"""
import csv, glob, io, json, math, os, re, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
SGT = timezone(timedelta(hours=8))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")

HDB_DATASET = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"  # Resale flat prices, Jan-2017 onwards
URA_TOKEN_URL = "https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1"
URA_DATA_URL = "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Transaction&batch={}"
HDB_DETAIL_MONTHS = 36  # block lookup covers the last 3 years

# Map frame used by the page's SVG (lng 103.6-104.1, lat 1.15-1.48 -> 1000 x 660)
X0, X1, Y0, Y1, W, H = 103.6, 104.1, 1.15, 1.48, 1000, 660
TENGAH = [257, 236]
# Fallback bubble positions (from the Oct 2026 pull) for weeks when a district has no coordinates
DIST_POS = {"10":[424,336],"11":[466,315],"12":[509,306],"13":[543,287],"14":[588,323],"15":[606,346],"16":[686,307],"17":[732,239],"18":[690,239],"19":[576,215],"20":[475,237],"21":[347,283],"22":[238,273],"23":[317,217],"24":[257,236],"25":[390,93],"26":[465,184],"27":[469,91],"28":[544,180],"01":[503,400],"02":[485,410],"03":[444,382],"04":[444,436],"05":[344,354],"06":[490,377],"07":[516,360],"08":[510,335],"09":[478,360]}
DIST_POS["24"] = TENGAH

# URA Master Plan planning regions for each HDB town
HDB_REGION = {
    "BISHAN": "Central", "BUKIT MERAH": "Central", "BUKIT TIMAH": "Central", "CENTRAL AREA": "Central",
    "GEYLANG": "Central", "KALLANG/WHAMPOA": "Central", "MARINE PARADE": "Central", "QUEENSTOWN": "Central",
    "TOA PAYOH": "Central",
    "BEDOK": "East", "PASIR RIS": "East", "TAMPINES": "East",
    "SEMBAWANG": "North", "WOODLANDS": "North", "YISHUN": "North",
    "ANG MO KIO": "North-East", "HOUGANG": "North-East", "PUNGGOL": "North-East", "SENGKANG": "North-East",
    "SERANGOON": "North-East",
    "BUKIT BATOK": "West", "BUKIT PANJANG": "West", "CHOA CHU KANG": "West", "CLEMENTI": "West",
    "JURONG EAST": "West", "JURONG WEST": "West", "TENGAH": "West",
}
# Flat type -> one-letter code used in the JSON
FT_CODE = {"1 ROOM": "1", "2 ROOM": "2", "3 ROOM": "3", "4 ROOM": "4", "5 ROOM": "5",
           "EXECUTIVE": "E", "MULTI-GENERATION": "M", "MULTI GENERATION": "M"}
# URA property type -> C (condo / apartment), E (executive condo), L (landed, incl. strata landed)
PT_CODE = {"Condominium": "C", "Apartment": "C", "Executive Condominium": "E"}


def get(url, headers=None, tries=3):
    h = {"User-Agent": UA}
    h.update(headers or {})
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode("utf-8", "replace").replace("\n", " ")
            if i == tries - 1 or e.code in (401, 403):
                raise RuntimeError(f"HTTP {e.code} from {url.split('?')[0]}: {body}") from None
            print(f"  retry {i+1} after HTTP {e.code}")
            time.sleep(5 * (i + 1))
        except Exception as e:
            if i == tries - 1:
                raise
            print(f"  retry {i+1} after error: {e}")
            time.sleep(5 * (i + 1))


def as_json(raw):
    """URA's file is mostly UTF-8 but can carry an older-encoded accented letter in a project name."""
    try:
        return json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return json.loads(raw.decode("cp1252", "replace"))


def qlabel(year, q):
    return f"{year} Q{q}"


def qkey(year, month):
    return year, (month - 1) // 3 + 1


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    os.replace(tmp, path)


def months_back(ym, n):
    y, m = int(ym[:4]), int(ym[5:7])
    t = y * 12 + (m - 1) - (n - 1)
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


# ---------------------------------------------------------------- HDB
def hdb_rows():
    base = f"https://api-open.data.gov.sg/v1/public/api/datasets/{HDB_DATASET}"
    init = json.loads(get(base + "/initiate-download"))
    url = (init.get("data") or {}).get("url")
    for _ in range(15):
        if url:
            break
        time.sleep(3)
        poll = json.loads(get(base + "/poll-download"))
        url = (poll.get("data") or {}).get("url")
    if not url:
        raise RuntimeError("data.gov.sg did not return a download link")
    text = get(url).decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def build_hdb(rows, now=None):
    if len(rows) < 100000:
        raise RuntimeError(f"HDB file looks too small ({len(rows)} rows)")
    now = now or datetime.now(SGT)

    agg, aggft, months = {}, {}, set()
    for r in rows:
        y, m = int(r["month"][:4]), int(r["month"][5:7])
        months.add(r["month"])
        qq = qkey(y, m)
        price = float(r["resale_price"])
        a = agg.setdefault((r["town"], qq), [0, 0.0]); a[0] += 1; a[1] += price
        ft = FT_CODE.get(r["flat_type"].upper(), "M")
        b = aggft.setdefault((r["town"], ft, qq), [0, 0.0]); b[0] += 1; b[1] += price

    first, last = min(months), max(months)
    ly, lm = int(last[:4]), int(last[5:7])
    lq = qkey(ly, lm)
    quarters = [(y, q) for y in range(2017, ly + 1) for q in range(1, 5) if (y, q) <= lq]
    partial = qkey(now.year, now.month) == lq  # quarter not finished yet

    def series(get_cell):
        n, p = [], []
        for qq in quarters:
            c = get_cell(qq)
            n.append(c[0] if c else 0)
            p.append(round(c[1] / c[0] / 1000) if c else 0)
        return n, p

    towns = {}
    for t in sorted({k[0] for k in agg}):
        n, p = series(lambda qq: agg.get((t, qq)))
        ft = {}
        for code in ["1", "2", "3", "4", "5", "E", "M"]:
            fn, fp = series(lambda qq: aggft.get((t, code, qq)))
            if any(fn):
                ft[code] = {"n": fn, "p": fp}
        towns[t] = {"n": n, "p": p, "region": HDB_REGION.get(t, ""), "ft": ft, "file": slug(t)}

    # Block detail: last 36 months, grouped town -> street -> block
    since = months_back(last, HDB_DETAIL_MONTHS)
    detail, models = {}, {}
    for r in rows:
        if r["month"] < since:
            continue
        mi = models.setdefault(r["flat_model"], len(models))
        storey = int(r["storey_range"][:2])
        row = [r["month"], FT_CODE.get(r["flat_type"].upper(), "M"), storey,
               round(float(r["floor_area_sqm"]), 1), mi, int(r["lease_commence_date"]), round(float(r["resale_price"]))]
        detail.setdefault(r["town"], {}).setdefault(r["street_name"], {}).setdefault(r["block"], []).append(row)
    model_list = [m for m, _ in sorted(models.items(), key=lambda kv: kv[1])]
    index = {}
    for t, streets in detail.items():
        for st, blocks in streets.items():
            for b in blocks.values():
                b.sort(key=lambda x: x[0], reverse=True)
            index.setdefault(st, [t, []])[1].extend(sorted(blocks))
    files = {slug(t): {"town": t, "since": since, "models": model_list, "streets": streets}
             for t, streets in detail.items()}
    # Million-dollar resale flats (price >= $1,000,000) in the same 36-month window, newest first.
    mill = []
    for t, streets in detail.items():
        for st, blocks in streets.items():
            for blk, deals in blocks.items():
                for d in deals:
                    if d[6] >= 1_000_000:
                        mill.append([d[0], t, blk, st, d[1], d[2], d[3], model_list[d[4]], d[5], d[6]])
    mill.sort(key=lambda x: (x[0], x[9]), reverse=True)
    files["million"] = {"since": since, "last_month": last, "threshold": 1_000_000,
                        "fields": ["month", "town", "block", "street", "flat_type", "storey_from", "sqm", "model", "lease_start", "price"],
                        "deals": mill}
    yr = last[:4]
    this_year = [d for d in mill if d[0][:4] == yr]
    by_month = {}
    for d in mill:
        by_month[d[0]] = by_month.get(d[0], 0) + 1
    files["million-summary"] = {"since": since, "last_month": last, "year": yr, "year_count": len(this_year),
                                "by_month": by_month, "top": sorted(this_year, key=lambda x: -x[9])[:5]}

    summary = {
        "status": "ok",
        "fetched": now.isoformat(timespec="minutes"),
        "records": len(rows),
        "first_month": first,
        "last_month": last,
        "quarters": [qlabel(*q) for q in quarters],
        "last_partial": partial,
        "detail_since": since,
        "towns": towns,
    }
    return summary, index, files


# ---------------------------------------------------------------- URA
def svy21_to_svg(e, n):
    lng = 103.8333333 + (e - 28001.642) / (111320 * math.cos(math.radians(1.3666667)))
    lat = 1.3666667 + (n - 38744.572) / 110574
    return [round((lng - X0) / (X1 - X0) * W), round((Y1 - lat) / (Y1 - Y0) * H)]


def ura_projects(key):
    tok = as_json(get(URA_TOKEN_URL, {"AccessKey": key}))
    token = tok.get("Result")
    if not token:
        raise RuntimeError(f"URA token request failed: {tok.get('Message') or tok}")
    projects = []
    for b in range(1, 5):
        j = as_json(get(URA_DATA_URL.format(b), {"AccessKey": key, "Token": token}))
        if j.get("Status") != "Success":
            raise RuntimeError(f"URA batch {b} failed: {j.get('Message')}")
        projects += j.get("Result") or []
    return projects


def build_ura(projects, now=None, min_projects=1000):
    if len(projects) < min_projects:
        raise RuntimeError(f"URA returned too few projects ({len(projects)})")
    now = now or datetime.now(SGT)

    agg, aggx, cen, qs, txs = {}, {}, {}, set(), 0
    detail, plist = {}, {}
    for p in projects:
        seg = p.get("marketSegment") or ""
        pname, street = (p.get("project") or "").strip(), (p.get("street") or "").strip()
        for t in p.get("transaction") or []:
            txs += 1
            mm, yy = int(t["contractDate"][:2]), 2000 + int(t["contractDate"][2:])
            qq = qkey(yy, mm)
            qs.add(qq)
            d = t["district"]
            s = int(t["typeOfSale"]) - 1  # 0 new sale, 1 sub sale, 2 resale
            u = int(t.get("noOfUnits") or 1)
            pt = PT_CODE.get(t.get("propertyType"), "L")
            agg.setdefault(d, {}).setdefault(qq, [0, 0, 0])[s] += u
            aggx.setdefault(d, {}).setdefault(f"{seg}|{pt}", {}).setdefault(qq, [0, 0, 0])[s] += u
            if p.get("x") and p.get("y"):
                c = cen.setdefault(d, [0.0, 0.0, 0])
                c[0] += float(p["x"]); c[1] += float(p["y"]); c[2] += 1
            key = f"{pname}|{street}"
            ym = f"{yy:04d}-{mm:02d}"
            detail.setdefault(d, {}).setdefault(key, []).append(
                [ym, s + 1, round(float(t["area"]), 1), t.get("floorRange") or "-",
                 round(float(t["price"])), u, pt])
            info = plist.setdefault((d, key), {"seg": seg, "pt": {}, "ten": t.get("tenure") or "", "n": 0, "last": ""})
            info["pt"][pt] = info["pt"].get(pt, 0) + u
            info["n"] += 1
            info["last"] = max(info["last"], ym)

    lo, hi = min(qs), max(qs)
    quarters = [(y, q) for y in range(lo[0], hi[0] + 1) for q in range(1, 5) if lo <= (y, q) <= hi]
    districts = {}
    for d in sorted(agg):
        c = cen.get(d)
        pos = svy21_to_svg(c[0] / c[2], c[1] / c[2]) if c else DIST_POS.get(d, TENGAH)
        x = {k: [[v.get(qq, [0, 0, 0])[s] for qq in quarters] for s in range(3)] for k, v in sorted(aggx[d].items())}
        districts[d] = {"c": pos, "n": [[agg[d].get(qq, [0, 0, 0])[s] for qq in quarters] for s in range(3)], "x": x}

    def short_tenure(s):
        s = s.lower()
        if s.startswith("freehold"):
            return "Freehold"
        m = re.match(r"(\d+) yrs lease commencing from (\d+)", s)
        return f"{m.group(1)}-yr from {m.group(2)}" if m else s[:24]

    index = []
    for (d, key), info in sorted(plist.items(), key=lambda kv: kv[0][1]):
        name, street = key.split("|", 1)
        main_pt = max(info["pt"].items(), key=lambda kv: kv[1])[0]
        index.append([name, street, d, info["seg"], main_pt, short_tenure(info["ten"]), info["n"], info["last"]])
    for rows in (r for dd in detail.values() for r in dd.values()):
        rows.sort(key=lambda x: x[0], reverse=True)
    files = {f"d{d}": v for d, v in detail.items()}

    summary = {
        "status": "ok",
        "fetched": now.isoformat(timespec="minutes"),
        "records": txs,
        "projects": len(projects),
        "quarters": [qlabel(*q) for q in quarters],
        "districts": districts,
    }
    return summary, index, files


# ---------------------------------------------------------------- main
def replace_folder(folder, index_name, index, files):
    """Write the new files, then remove files from last week that no longer exist."""
    path = os.path.join(ROOT, folder)
    write_json(os.path.join(path, index_name), index)
    keep = {index_name}
    for name, obj in files.items():
        write_json(os.path.join(path, name + ".json"), obj)
        keep.add(name + ".json")
    for f in glob.glob(os.path.join(path, "*.json")):
        if os.path.basename(f) not in keep:
            os.remove(f)


def main():
    out_path = os.path.join(ROOT, "market-data.json")
    try:
        old = json.load(open(out_path))
    except Exception:
        old = {}
    out = dict(old)
    problems = []

    print("Fetching HDB resale data...")
    try:
        summary, index, files = build_hdb(hdb_rows())
        replace_folder("hdb", "index.json", index, files)
        out["hdb"] = summary
        print(f"  ok: {summary['records']} records, last month {summary['last_month']}, {len(index)} streets")
    except Exception as e:
        problems.append(f"HDB: {e}")
        if "hdb" in out:
            out["hdb"]["status"] = "stale"

    key = os.environ.get("URA_ACCESS_KEY", "").strip()
    print("Fetching URA private transactions...")
    if not key:
        problems.append("URA: URA_ACCESS_KEY secret is not set")
        if "ura" in out:
            out["ura"]["status"] = "stale"
    else:
        try:
            summary, index, files = build_ura(ura_projects(key))
            replace_folder("ura", "projects.json", index, files)
            out["ura"] = summary
            print(f"  ok: {summary['records']} records, {len(index)} projects, "
                  f"quarters {summary['quarters'][0]} to {summary['quarters'][-1]}")
        except Exception as e:
            problems.append(f"URA: {e}")
            if "ura" in out:
                out["ura"]["status"] = "stale"

    if "hdb" not in out and "ura" not in out:
        print("Nothing fetched and no previous data. Stopping.")
        print("\n".join(problems))
        sys.exit(1)

    out["generated"] = datetime.now(SGT).isoformat(timespec="minutes")
    write_json(out_path, out)
    print(f"Wrote {out_path}")

    if problems:
        print("::warning::" + " | ".join(problems))
        sys.exit(2)


if __name__ == "__main__":
    main()
