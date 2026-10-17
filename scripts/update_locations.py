#!/usr/bin/env python3
"""
Weekly location refresh (OneMap, Singapore Land Authority) for sereneleeproperty.com

Adds coordinates and nearest MRT/LRT stations to every HDB block and private
project that the Market Map already knows about (data/hdb/index.json and
data/ura/projects.json, written by update_market_data.py).

Writes:
  data/geo/stations.json          every MRT/LRT station: [name, line codes, lat, lng]
  data/geo/hdb/<town>.json        "STREET|BLK"  -> [lat, lng, postal, [[station_idx, metres], x3]]
  data/geo/ura/d<NN>.json         "NAME|STREET" -> [lat, lng, postal, [[station_idx, metres], x3]]
  data/geo/near/<station>.json    HDB blocks and private projects within 1 km of that station
  data/geo/misses.json            addresses OneMap could not find (retried after 90 days)

Only addresses not geocoded before are looked up, so after the first run
(about an hour for ~13,000 addresses) a weekly run takes a few minutes.
Distances are straight-line ("as the crow flies"), not walking routes.

Uses the public OneMap search API (no account or key needed).
Standard library only.
"""
import glob, json, math, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
GEO = os.path.join(ROOT, "geo")
SGT = timezone(timedelta(hours=8))
SEARCH = "https://www.onemap.gov.sg/api/common/elastic/search?{}"
UA = "sereneleeproperty.com location refresh"
PAUSE = 0.27            # OneMap allows 250 calls a minute; stay under it
NEAR_RADIUS = 1000      # metres kept in data/geo/near/*.json
MISS_RETRY_DAYS = 90
MAX_LOOKUPS = int(os.environ.get("MAX_LOOKUPS", "40000"))
# Stop looking up new addresses after this many minutes so the run always saves
# what it found before the GitHub job time limit; the next run continues.
TIME_BUDGET_MIN = float(os.environ.get("TIME_BUDGET_MIN", "240"))
T0 = time.time()

# HDB data uses abbreviated street names; OneMap search works best with full words.
EXPAND = {"AVE": "AVENUE", "DR": "DRIVE", "ST": "STREET", "RD": "ROAD", "CRES": "CRESCENT",
          "CTRL": "CENTRAL", "NTH": "NORTH", "STH": "SOUTH", "UPP": "UPPER", "BT": "BUKIT",
          "JLN": "JALAN", "LOR": "LORONG", "KG": "KAMPONG", "PL": "PLACE", "TER": "TERRACE",
          "CL": "CLOSE", "HTS": "HEIGHTS", "C'WEALTH": "COMMONWEALTH", "TG": "TANJONG",
          "MKT": "MARKET", "GDNS": "GARDENS", "GDN": "GARDEN", "PK": "PARK", "ST.": "SAINT"}
ABBR = {v: k for k, v in EXPAND.items() if k != "ST."}
ABBR["SAINT"] = "ST."

calls = 0


def now():
    return datetime.now(SGT)


def get(params, tries=5):
    global calls
    if calls >= MAX_LOOKUPS:
        raise RuntimeError("lookup budget used up for this run")
    if (time.time() - T0) / 60 > TIME_BUDGET_MIN:
        raise RuntimeError("time budget used up for this run; the next run carries on")
    url = SEARCH.format(urllib.parse.urlencode(params))
    for i in range(tries):
        try:
            calls += 1
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.load(r)
            time.sleep(PAUSE)
            return data
        except urllib.error.HTTPError as e:
            wait = 30 if e.code == 429 else 5 * (i + 1)
            print(f"  HTTP {e.code}, waiting {wait}s", flush=True)
            time.sleep(wait)
        except Exception as e:  # network blip
            print(f"  {e}, retrying", flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"OneMap kept failing for {params}")


def search(term, page=1):
    return get({"searchVal": term, "returnGeom": "Y", "getAddrDetails": "Y", "pageNum": page})


def norm_road(s):
    words = re.sub(r"[^A-Z0-9'. ]+", " ", s.upper()).split()
    return " ".join(ABBR.get(w, w) for w in words).replace(".", "")


def full_street(s):
    return " ".join(EXPAND.get(w, w) for w in s.upper().split())


def tight(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def dist_m(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------- stations
STATION_RE = re.compile(r"^(.+?) (MRT|LRT) STATION(?: \(([^)]*)\))?$")


def fetch_stations():
    found = {}
    for kind in ("MRT STATION", "LRT STATION"):
        page, pages = 1, 1
        while page <= pages:
            d = search(kind, page)
            pages = int(d.get("totalNumPages") or 1)
            for r in d.get("results", []):
                for label in (r.get("BUILDING", ""), r.get("SEARCHVAL", "")):
                    m = STATION_RE.match(label.strip().upper())
                    if m and "EXIT" not in label.upper():
                        name = f"{m.group(1).title()} {m.group(2)}"
                        s = found.setdefault(name, {"codes": set(), "pts": []})
                        if m.group(3):
                            s["codes"].update(c.strip() for c in re.split(r"[/,]", m.group(3)) if c.strip())
                        s["pts"].append((float(r["LATITUDE"]), float(r["LONGITUDE"])))
                        break
            page += 1
    stations = []
    for name, s in sorted(found.items()):
        if not s["codes"]:
            continue  # shops/kiosks named after a station, e.g. "Burger King Woodlands MRT Station"
        lat = sum(p[0] for p in s["pts"]) / len(s["pts"])
        lng = sum(p[1] for p in s["pts"]) / len(s["pts"])
        stations.append([name, " / ".join(sorted(s["codes"])), round(lat, 6), round(lng, 6)])
    return stations


# ---------------------------------------------------------------- geocoding
def geocode_block(blk, street):
    want = tight(norm_road(street))
    d = search(f"{blk} {full_street(street)}")
    res = [r for r in d.get("results", []) if r.get("BLK_NO", "").upper() == blk.upper()]
    best = [r for r in res if tight(norm_road(r.get("ROAD_NAME", ""))) == want] or res[:1]
    if not best:
        return None
    r = best[0]
    return [round(float(r["LATITUDE"]), 6), round(float(r["LONGITUDE"]), 6), r.get("POSTAL", "")]


def geocode_project(name, street):
    want_road = tight(street)
    if not name.upper().startswith("LANDED HOUSING") and len(tight(name)) >= 3:
        d = search(name)
        res = d.get("results", [])
        n = tight(name)
        best = ([r for r in res if n in tight(r.get("BUILDING", "")) and tight(r.get("ROAD_NAME", "")) == want_road]
                or [r for r in res if n in tight(r.get("BUILDING", ""))])
        if best:
            r = best[0]
            return [round(float(r["LATITUDE"]), 6), round(float(r["LONGITUDE"]), 6), r.get("POSTAL", "")]
    # Fall back to the street itself (landed estates, unnamed projects)
    d = search(street)
    res = [r for r in d.get("results", []) if tight(r.get("ROAD_NAME", "")) == want_road]
    if res:
        lat = sum(float(r["LATITUDE"]) for r in res) / len(res)
        lng = sum(float(r["LONGITUDE"]) for r in res) / len(res)
        return [round(lat, 6), round(lng, 6), ""]
    return None


def nearest3(pt, stations):
    ds = sorted((round(dist_m(pt, (s[2], s[3]))), i) for i, s in enumerate(stations))
    return [[i, m] for m, i in ds[:3]]


def main():
    started = now()
    os.makedirs(GEO, exist_ok=True)
    hdb_index = load(os.path.join(ROOT, "hdb", "index.json"), {})
    projects = load(os.path.join(ROOT, "ura", "projects.json"), [])
    if not hdb_index and not projects:
        print("No market data yet; run update_market_data.py first.")
        return 1

    print("Fetching MRT/LRT stations…", flush=True)
    old_st = load(os.path.join(GEO, "stations.json"), {}).get("stations", [])
    try:
        stations = fetch_stations()
    except Exception as e:
        print(f"Station refresh failed ({e}); keeping last list.")
        stations = old_st
    if len(stations) < 100:
        print(f"Only {len(stations)} stations found; keeping last list.")
        stations = old_st or stations
    if not stations:
        return 1
    print(f"  {len(stations)} stations")

    misses = load(os.path.join(GEO, "misses.json"), {})
    cutoff = (now() - timedelta(days=MISS_RETRY_DAYS)).strftime("%Y-%m-%d")
    misses = {k: v for k, v in misses.items() if v >= cutoff}
    today = now().strftime("%Y-%m-%d")
    budget_hit = False

    # Existing coordinates (any file), so only new addresses are looked up
    hdb_geo, ura_geo = {}, {}
    for p in glob.glob(os.path.join(GEO, "hdb", "*.json")):
        hdb_geo[os.path.basename(p)[:-5]] = load(p, {})
    for p in glob.glob(os.path.join(GEO, "ura", "d*.json")):
        ura_geo[os.path.basename(p)[1:-5]] = load(p, {})

    # ---- HDB blocks
    todo = 0
    for street, (town, blocks) in hdb_index.items():
        g = hdb_geo.setdefault(slug(town), {})
        for blk in blocks:
            key = f"{street}|{blk}"
            if key in g or ("H|" + key) in misses or budget_hit:
                continue
            todo += 1
            try:
                pt = geocode_block(blk, street)
            except RuntimeError as e:
                print(f"Stopping HDB lookups: {e}")
                budget_hit = True
                continue
            if pt:
                g[key] = pt
            else:
                misses["H|" + key] = today
            if todo % 250 == 0:
                print(f"  HDB {todo} looked up ({calls} calls)", flush=True)
    print(f"HDB: {todo} new blocks looked up")

    # ---- Private projects
    todo = 0
    for p in projects:
        name, street, d = p[0], p[1], p[2]
        g = ura_geo.setdefault(d, {})
        key = f"{name}|{street}"
        if key in g or ("P|" + key) in misses or budget_hit:
            continue
        todo += 1
        try:
            pt = geocode_project(name, street)
        except RuntimeError as e:
            print(f"Stopping project lookups: {e}")
            budget_hit = True
            continue
        if pt:
            g[key] = pt
        else:
            misses["P|" + key] = today
        if todo % 250 == 0:
            print(f"  Projects {todo} looked up ({calls} calls)", flush=True)
    print(f"Private: {todo} new projects looked up")

    # ---- Nearest stations (recomputed every run, so new stations are picked up)
    near = {i: {"hdb": [], "pte": []} for i in range(len(stations))}
    pmeta = {(p[0], p[1]): p for p in projects}
    for town_slug, g in hdb_geo.items():
        for key, v in g.items():
            v[:] = v[:3] + [nearest3(v, stations)]
            street, blk = key.split("|", 1)
            for i, m in v[3]:
                if m <= NEAR_RADIUS:
                    near[i]["hdb"].append([hdb_index.get(street, [town_slug.upper()])[0], street, blk, m])
        save(os.path.join(GEO, "hdb", f"{town_slug}.json"), g)
    for d, g in ura_geo.items():
        for key, v in g.items():
            v[:] = v[:3] + [nearest3(v, stations)]
            name, street = key.split("|", 1)
            meta = pmeta.get((name, street))
            for i, m in v[3]:
                if m <= NEAR_RADIUS:
                    near[i]["pte"].append([name, street, d, m, meta[4] if meta else "", meta[5] if meta else ""])
        save(os.path.join(GEO, "ura", f"d{d}.json"), g)

    for p in glob.glob(os.path.join(GEO, "near", "*.json")):
        os.remove(p)
    for i, s in enumerate(stations):
        n = near[i]
        n["hdb"].sort(key=lambda r: r[3])
        n["pte"].sort(key=lambda r: r[3])
        save(os.path.join(GEO, "near", f"{slug(s[0])}.json"), {"station": s, **n})

    save(os.path.join(GEO, "stations.json"), {
        "source": "OneMap, Singapore Land Authority",
        "fetched": started.strftime("%Y-%m-%dT%H:%M+08:00"),
        "stations": stations,
    })
    save(os.path.join(GEO, "misses.json"), misses)
    nh = sum(len(g) for g in hdb_geo.values())
    np_ = sum(len(g) for g in ura_geo.values())
    print(f"Done: {nh} HDB blocks, {np_} private projects, {len(stations)} stations, "
          f"{len(misses)} not found, {calls} OneMap calls.")
    return 2 if budget_hit else 0


if __name__ == "__main__":
    sys.exit(main())
