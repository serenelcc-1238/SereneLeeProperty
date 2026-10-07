#!/usr/bin/env python3
"""
Weekly market data refresh for sereneleeproperty.com/market-map.html

Pulls two official datasets and writes data/market-data.json:
  1. HDB resale transactions (data.gov.sg, no key needed)
  2. URA private residential transactions (URA Data Service, needs URA_ACCESS_KEY)

If one source fails, the previous figures for that source are kept and the
script exits with code 2 so the GitHub run shows a warning, but the site
still gets whatever did refresh.

Standard library only, so nothing needs installing.
"""
import csv, io, json, math, os, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "market-data.json")
SGT = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (compatible; sereneleeproperty-market-map/1.0)"

HDB_DATASET = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"  # Resale flat prices, Jan-2017 onwards
URA_TOKEN_URL = "https://eservice.ura.gov.sg/uraDataService/insertNewToken/v1"
URA_DATA_URL = "https://eservice.ura.gov.sg/uraDataService/invokeUraDS/v1?service=PMI_Resi_Transaction&batch={}"

# Map frame used by the page's SVG (lng 103.6-104.1, lat 1.15-1.48 -> 1000 x 660)
X0, X1, Y0, Y1, W, H = 103.6, 104.1, 1.15, 1.48, 1000, 660
TENGAH = [257, 236]  # fallback position for D24, whose projects carry no coordinates


def get(url, headers=None, tries=3):
    h = {"User-Agent": UA}
    h.update(headers or {})
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=180) as r:
                return r.read()
        except Exception as e:
            if i == tries - 1:
                raise
            print(f"  retry {i+1} after error: {e}")
            time.sleep(5 * (i + 1))


def qlabel(year, q):
    return f"{year} Q{q}"


def qkey(year, month):
    return year, (month - 1) // 3 + 1


# ---------------------------------------------------------------- HDB
def fetch_hdb():
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
    rows = list(csv.DictReader(io.StringIO(text)))
    if len(rows) < 100000:
        raise RuntimeError(f"HDB file looks too small ({len(rows)} rows)")

    agg = {}
    months = set()
    for r in rows:
        y, m = int(r["month"][:4]), int(r["month"][5:7])
        months.add(r["month"])
        k = (r["town"], qkey(y, m))
        a = agg.setdefault(k, [0, 0.0])
        a[0] += 1
        a[1] += float(r["resale_price"])

    first, last = min(months), max(months)
    ly, lm = int(last[:4]), int(last[5:7])
    lq = qkey(ly, lm)
    quarters = [(y, q) for y in range(2017, ly + 1) for q in range(1, 5) if (y, q) <= lq]
    now = datetime.now(SGT)
    partial = qkey(now.year, now.month) == lq  # quarter not finished yet

    towns = {}
    for t in sorted({k[0] for k in agg}):
        n, p = [], []
        for qq in quarters:
            c = agg.get((t, qq))
            n.append(c[0] if c else 0)
            p.append(round(c[1] / c[0] / 1000) if c else 0)
        towns[t] = {"n": n, "p": p}
    return {
        "status": "ok",
        "fetched": now.isoformat(timespec="minutes"),
        "records": len(rows),
        "first_month": first,
        "last_month": last,
        "quarters": [qlabel(*q) for q in quarters],
        "last_partial": partial,
        "towns": towns,
    }


# ---------------------------------------------------------------- URA
def svy21_to_svg(e, n):
    lng = 103.8333333 + (e - 28001.642) / (111320 * math.cos(math.radians(1.3666667)))
    lat = 1.3666667 + (n - 38744.572) / 110574
    return [round((lng - X0) / (X1 - X0) * W), round((Y1 - lat) / (Y1 - Y0) * H)]


def fetch_ura(key):
    tok = json.loads(get(URA_TOKEN_URL, {"AccessKey": key}))
    token = tok.get("Result")
    if not token:
        raise RuntimeError(f"URA token request failed: {tok.get('Message') or tok}")
    projects = []
    for b in range(1, 5):
        j = json.loads(get(URA_DATA_URL.format(b), {"AccessKey": key, "Token": token}))
        if j.get("Status") != "Success":
            raise RuntimeError(f"URA batch {b} failed: {j.get('Message')}")
        projects += j.get("Result") or []
    if len(projects) < 1000:
        raise RuntimeError(f"URA returned too few projects ({len(projects)})")

    agg, cen, qs, txs = {}, {}, set(), 0
    for p in projects:
        for t in p.get("transaction") or []:
            txs += 1
            mm, yy = int(t["contractDate"][:2]), 2000 + int(t["contractDate"][2:])
            qq = qkey(yy, mm)
            qs.add(qq)
            d = t["district"]
            s = int(t["typeOfSale"]) - 1  # 0 new sale, 1 sub sale, 2 resale
            u = int(t.get("noOfUnits") or 1)
            agg.setdefault(d, {}).setdefault(qq, [0, 0, 0])[s] += u
            if p.get("x") and p.get("y"):
                c = cen.setdefault(d, [0.0, 0.0, 0])
                c[0] += float(p["x"]); c[1] += float(p["y"]); c[2] += 1

    lo, hi = min(qs), max(qs)
    quarters = [(y, q) for y in range(lo[0], hi[0] + 1) for q in range(1, 5) if lo <= (y, q) <= hi]
    districts = {}
    for d in sorted(agg):
        c = cen.get(d)
        pos = svy21_to_svg(c[0] / c[2], c[1] / c[2]) if c else TENGAH
        districts[d] = {"c": pos, "n": [[agg[d].get(qq, [0, 0, 0])[s] for qq in quarters] for s in range(3)]}
    return {
        "status": "ok",
        "fetched": datetime.now(SGT).isoformat(timespec="minutes"),
        "records": txs,
        "projects": len(projects),
        "quarters": [qlabel(*q) for q in quarters],
        "districts": districts,
    }


# ---------------------------------------------------------------- main
def main():
    try:
        old = json.load(open(OUT))
    except Exception:
        old = {}
    out = dict(old)
    problems = []

    print("Fetching HDB resale data...")
    try:
        out["hdb"] = fetch_hdb()
        print(f"  ok: {out['hdb']['records']} records, last month {out['hdb']['last_month']}")
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
            out["ura"] = fetch_ura(key)
            print(f"  ok: {out['ura']['records']} records, quarters {out['ura']['quarters'][0]} to {out['ura']['quarters'][-1]}")
        except Exception as e:
            problems.append(f"URA: {e}")
            if "ura" in out:
                out["ura"]["status"] = "stale"

    if "hdb" not in out and "ura" not in out:
        print("Nothing fetched and no previous data. Stopping.")
        print("\n".join(problems))
        sys.exit(1)

    out["generated"] = datetime.now(SGT).isoformat(timespec="minutes")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print(f"Wrote {OUT}")

    if problems:
        print("::warning::" + " | ".join(problems))
        sys.exit(2)


if __name__ == "__main__":
    main()
