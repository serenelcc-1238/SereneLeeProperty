#!/usr/bin/env python3
"""
Weekly New Launches refresh for sereneleeproperty.com

Reads ERA's official New Launch listings (the same feed that powers
https://propertyportal.era.com.sg/new-launches) and rewrites:
  - new-launches.html  : every Singapore residential project now selling
                         (still under construction) or launching within
                         12 months, between the ERA:START / ERA:END markers
  - index.html         : "Latest Property Launches" = the 3 newest projects on
                         sale, between the same markers. Serene's own write-up
                         cards (scripts/home-pinned/*.html) compete by ERA launch
                         date, so they move down and drop off as newer launches arrive
  - both pages' "as of" dates (ERA-DATE markers)
  - data/new-launches.json : the cleaned list, for the record

Serene's own spotlight cards (data-pinned="true") sit OUTSIDE the markers,
so they are never touched and always stay first. A project that has a
pinned card is left out of the auto list so it doesn't appear twice.

CCR / RCR / OCR comes from URA's market segment for the project
(data/ura/projects.json, written by update_market_data.py). Projects with
no URA caveats yet (not launched) take their district's main segment.

If ERA cannot be reached or returns too few projects, nothing is changed
and the script exits 1. Standard library only.
"""
import html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
API = "https://propertyportal.era.com.sg/api/salesplus/new-launches/search"
ERA_PAGE = "https://propertyportal.era.com.sg/new-launches"
SGT = timezone(timedelta(hours=8))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
WA = "https://wa.me/6580868568?text="
MIN_PROJECTS = 15          # sanity floor: below this, assume the feed broke
UPCOMING_DAYS = 365        # show projects launching within the next 12 months

DISTRICT = {
    "01": "Raffles Place / Marina", "02": "Tanjong Pagar / Anson", "03": "Queenstown / Tiong Bahru",
    "04": "Telok Blangah / HarbourFront", "05": "Buona Vista / West Coast / Clementi",
    "06": "City Hall / Clarke Quay", "07": "Beach Road / Bugis", "08": "Little India / Farrer Park",
    "09": "Orchard / River Valley", "10": "Tanglin / Holland / Bukit Timah",
    "11": "Newton / Novena", "12": "Balestier / Toa Payoh", "13": "Macpherson / Braddell",
    "14": "Geylang / Eunos", "15": "Katong / Marine Parade", "16": "Bedok / Upper East Coast",
    "17": "Loyang / Changi", "18": "Tampines / Pasir Ris", "19": "Serangoon / Hougang / Punggol / Sengkang",
    "20": "Ang Mo Kio / Bishan / Thomson", "21": "Upper Bukit Timah / Clementi Park",
    "22": "Jurong / Boon Lay", "23": "Bukit Batok / Bukit Panjang / Choa Chu Kang",
    "24": "Lim Chu Kang / Tengah", "25": "Kranji / Woodlands", "26": "Mandai / Upper Thomson",
    "27": "Yishun / Sembawang", "28": "Seletar / Yio Chu Kang",
}
KEEP_UPPER = {"GLS", "TMW", "EC", "CDL", "UOL", "MCL", "CSC", "SL", "ZACD", "KSH", "TID", "JV", "II", "III", "IV"}


# ------------------------------------------------------------ fetch
def fetch_all():
    items, page = [], 1
    while page <= 10:
        body = json.dumps({"page": page, "pageSize": 100}).encode()
        req = urllib.request.Request(API, data=body, method="POST", headers={
            "User-Agent": UA, "Content-Type": "application/json", "Accept": "application/json",
            "Origin": "https://propertyportal.era.com.sg", "Referer": ERA_PAGE})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    j = json.loads(r.read().decode("utf-8", "replace"))
                break
            except urllib.error.HTTPError as e:
                msg = e.read()[:200].decode("utf-8", "replace")
                if attempt == 2 or e.code in (401, 403):
                    raise RuntimeError(f"ERA returned HTTP {e.code}: {msg}") from None
                time.sleep(5 * (attempt + 1))
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
        data = j.get("data") or []
        items += data
        total = j.get("totalCount") or 0
        if not data or len(items) >= total or len(data) < 90:
            break
        page += 1
    return items


# ------------------------------------------------------------ helpers
def norm(s):
    s = re.sub(r"\s*-\s*SINGAPORE$", "", (s or "").upper())
    return re.sub(r"[^A-Z0-9]", "", s.replace("@", "AT").replace("&", "AND"))


def smart_title(s):
    """Title-case ERA's ALL-CAPS names, keeping acronyms (CDL, GLS, TMW, 8@BT) in capitals."""
    s = re.sub(r"\s+", " ", (s or "").replace("\n", " ")).strip()
    s = re.sub(r"\s*-\s*SINGAPORE$", "", s, flags=re.I)
    if not s or not s.isupper():
        return s

    def fix(w):
        core = re.sub(r"[^A-Z]", "", w)
        if core in KEEP_UPPER or (core and core != "LTD" and not re.search(r"[AEIOUY]", core)):
            return w
        return re.sub(r"[A-Z]+", lambda m: m.group(0)[0] + m.group(0)[1:].lower(), w)
    return " ".join(fix(w) for w in s.split(" "))


def quarter(d):
    if not d:
        return None, None
    y, m = int(d[:4]), int(d[5:7])
    q = (m - 1) // 3 + 1
    return f"Q{q} {y}", f"{y}.{q}"


def money(v):
    return f"S${v:,.0f}"


def bedrooms(s):
    if not s:
        return ""
    vals = sorted({int(x) for x in str(s).split(",") if x.strip().isdigit()})
    if not vals:
        return ""
    studio = 0 in vals
    beds = [v for v in vals if v > 0]
    parts = []
    if studio:
        parts.append("Studio")
    if beds:
        parts.append(f"{beds[0]}–{beds[-1]} bedroom" if len(beds) > 1 else f"{beds[0]} bedroom")
    return " + ".join(parts) if studio and beds else "".join(parts)


def esc(s):
    return html.escape(str(s), quote=True)


# ------------------------------------------------------------ selection
def select(items, today):
    lim = (today + timedelta(days=UPCOMING_DAYS)).isoformat()
    t = today.isoformat()
    out = []
    for x in items:
        if x.get("country") != "SG" or x.get("propertyType") not in ("Condo", "Landed"):
            continue
        if x.get("isSoldOut") or not x.get("launchDate"):
            continue
        u = x.get("unitSummary") or {}
        launched = x["launchDate"] <= t
        if launched:
            if x.get("completionStatus") == "completed":
                continue
            avail = u.get("numberOfAvailableUnits")
            if avail is not None and avail <= 0:
                continue
            if avail is None and (u.get("numberOfSoldUnits") or 0) >= (x.get("numberOfUnits") or 1):
                continue
        elif x["launchDate"] > lim:
            continue
        x["_status"] = "selling" if launched else "upcoming"
        out.append(x)
    return out


def region_lookup():
    seg_by_name, dist_seg = {}, {}
    try:
        for p in json.load(open(os.path.join(ROOT, "data/ura/projects.json"))):
            seg_by_name.setdefault(norm(p[0]), p[3])
    except Exception as e:
        print(f"  note: URA project segments unavailable ({e})")
    try:
        md = json.load(open(os.path.join(ROOT, "data/market-data.json")))
        for d, v in md["ura"]["districts"].items():
            tot = {}
            for k, n in (v.get("x") or {}).items():
                tot[k.split("|")[0]] = tot.get(k.split("|")[0], 0) + sum(map(sum, n))
            if tot:
                dist_seg[d] = max(tot, key=tot.get)
    except Exception as e:
        print(f"  note: district segments unavailable ({e})")

    def region(x):
        n = norm(x.get("name"))
        if n in seg_by_name:
            return seg_by_name[n], "ura"
        d = (x.get("district") or "").lower().replace("d", "").zfill(2)
        return dist_seg.get(d, "OCR"), "district"
    return region


# ------------------------------------------------------------ rendering
def card(x, region, today, compact=False):
    u = x.get("unitSummary") or {}
    name = smart_title(x["name"])
    d = (x.get("district") or "").lower().replace("d", "").zfill(2)
    loc = f"D{d} {DISTRICT.get(d, '')}".strip()
    ten = x.get("tenureCategory") or ""
    ten_txt = {"freehold": "Freehold", "leasehold_999": "999-Yr Leasehold", "leasehold_99": "99-Yr Leasehold"}.get(ten, "Leasehold")
    ten_key = "freehold" if ten in ("freehold", "leasehold_999") else "leasehold"
    topq, topkey = quarter(x.get("top"))
    subs = u.get("propertySubTypes") or []
    ptype = "landed" if x.get("propertyType") == "Landed" else ("ec" if "Executive Condominium" in subs else "condo")
    ptype_txt = {"landed": "Landed", "ec": "Executive Condo", "condo": ""}[ptype]
    dev = smart_title(x.get("developer") or "")
    units = x.get("numberOfUnits")
    avail = u.get("numberOfAvailableUnits")
    selling = x["_status"] == "selling"
    ld = x["launchDate"]
    ldt = date.fromisoformat(ld)
    if selling:
        status = "Now Selling"
    elif (ldt - today).days <= 75:
        status = f"Launching {ldt.strftime('%-d %b')}" if ldt.day not in (28, 29, 30, 31) else f"Launching {ldt.strftime('%b %Y')}"
    else:
        status = f"Expected {quarter(ld)[0]}"
    price = (f"From {money(u['minPrice'])}" if u.get("minPrice") else "Pricing not yet released")
    psf = (f"${u['minPsf']:,.0f}–${u['maxPsf']:,.0f} psf" if u.get("minPsf") and u.get("maxPsf") else "")
    mix = bedrooms(u.get("bedroomTypes"))
    size = (f"{u['minArea']:,}–{u['maxArea']:,} sqft" if u.get("minArea") and u.get("maxArea") else "")
    meta1 = " &middot; ".join(filter(None, [esc(loc), ten_txt, esc(ptype_txt), f"TOP {topq}" if topq else "TOP to be advised"]))
    left = f"{avail:,} left" if (selling and avail is not None and units and avail < units) else ""
    meta2 = " &middot; ".join(filter(None, [f"Developer: {esc(dev)}" if dev else "", f"{units:,} units" if units else "", left]))
    detail = " &middot; ".join(filter(None, [mix, size, psf]))
    img = x.get("mainImage") or ""
    alt = f"{name} artist's impression"
    region_seg = region(x)[0]
    if selling:
        cta_txt, msg = "Enquire via WhatsApp", f"Hi Serene, I'd like to find out more about {name}."
    else:
        cta_txt, msg = "Register for VIP Preview", f"Hi Serene, I'd like to register for the VIP preview of {name}."
    href = WA + urllib.parse.quote(msg)
    if compact:  # homepage card
        return (f'      <div class="launch-card">\n'
                f'        <div class="launch-thumb"><img src="{esc(img)}" alt="{esc(alt)}" loading="lazy"><span class="launch-status">{esc(status)}</span></div>\n'
                f'        <div class="launch-body">\n'
                f'          <div class="launch-name">{esc(name)}</div>\n'
                f'          <div class="launch-meta">{esc(loc)} &middot; TOP {topq or "TBA"}</div>\n'
                f'          <div class="launch-price">{price}</div>\n'
                f'        </div>\n'
                f'      </div>\n')
    return (f'      <div class="launch-card" data-region="{region_seg}" data-tenure="{ten_key}" data-top="{topkey or "9999"}" '
            f'data-launch="{ld}" data-status="{x["_status"]}" data-ptype="{ptype}">\n'
            f'        <div class="launch-thumb"><img src="{esc(img)}" alt="{esc(alt)}" loading="lazy"><span class="launch-status">{esc(status)}</span></div>\n'
            f'        <div class="launch-body">\n'
            f'          <div class="launch-name">{esc(name)}</div>\n'
            f'          <div class="launch-meta">{meta1}</div>\n'
            f'          <div class="launch-meta" style="margin-top:-4px;">{meta2}</div>\n'
            f'          <div class="launch-price">{price}</div>\n'
            + (f'          <p class="launch-desc" style="font-size:.85rem;color:var(--muted);margin:6px 0 10px;">{detail}</p>\n' if detail else
               '          <p class="launch-desc" style="font-size:.85rem;color:var(--muted);margin:6px 0 10px;">Unit mix and prices to be announced at launch.</p>\n')
            + f'          <a href="{href}" target="_blank" rel="noopener" class="btn btn-gold btn-block">{cta_txt}</a>\n'
            f'        </div>\n'
            f'      </div>\n')


def replace_between(text, start, end, new, label):
    i, j = text.find(start), text.find(end)
    if i < 0 or j < 0 or j < i:
        raise RuntimeError(f"markers missing in {label}: {start} / {end}")
    return text[:i + len(start)] + new + text[j:]


HOME_PINNED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "home-pinned")
PIN_LEAD_DAYS = 30  # a write-up card may show up to 30 days before its launch (VIP preview period)


def home_pinned(items, today):
    """Serene's own homepage cards, each with the launch date ERA reports for it."""
    by_name = {norm(x.get("name") or ""): x for x in items}
    out = []
    if not os.path.isdir(HOME_PINNED_DIR):
        return out
    for f in sorted(os.listdir(HOME_PINNED_DIR)):
        if not f.endswith(".html"):
            continue
        raw = open(os.path.join(HOME_PINNED_DIR, f)).read()
        raw = re.sub(r"<!--.*?-->\s*", "", raw, flags=re.S)
        attr = lambda k: (re.search(rf'{k}="([^"]*)"', raw) or [None, ""])[1]
        x = by_name.get(norm(html.unescape(attr("data-era-name"))))
        if x is not None and x.get("isSoldOut"):
            continue
        ld = (x or {}).get("launchDate") or attr("data-launch")
        if not ld or ld > (today + timedelta(days=PIN_LEAD_DAYS)).isoformat():
            continue
        status = "Now Selling" if ld <= today.isoformat() else attr("data-prelaunch") or "Launching soon"
        html_card = raw.replace("{STATUS}", status)
        html_card = re.sub(r'data-launch="[^"]*"', f'data-launch="{ld}"', html_card)
        out.append({"launchDate": ld, "html": html_card.rstrip() + "\n", "name": attr("data-era-name")})
    return out


def pinned_names(page):
    names = set()
    for m in re.finditer(r'<div class="launch-card"[^>]*data-pinned="true"[^>]*>.*?<div class="launch-name">(.*?)</div>', page, re.S):
        names.add(norm(html.unescape(m.group(1))))
    return names


# ------------------------------------------------------------ main
def main(items=None, today=None):
    today = today or datetime.now(SGT).date()
    if items is None:
        print("Fetching ERA new launches...")
        items = fetch_all()
    print(f"  {len(items)} projects in ERA feed")
    chosen = select(items, today)
    if len(chosen) < MIN_PROJECTS:
        print(f"Only {len(chosen)} projects selected — feed looks wrong, leaving the site unchanged.")
        sys.exit(1)

    nl_path, ix_path = os.path.join(ROOT, "new-launches.html"), os.path.join(ROOT, "index.html")
    nl, ix = open(nl_path).read(), open(ix_path).read()
    pinned = pinned_names(nl)
    region = region_lookup()

    listing = [x for x in chosen if norm(x["name"]) not in pinned]
    sell = sorted((x for x in listing if x["_status"] == "selling"), key=lambda x: x["launchDate"], reverse=True)
    up = sorted((x for x in listing if x["_status"] == "upcoming"), key=lambda x: x["launchDate"])
    listing = sell + up  # same order the page shows by default
    stamp = today.strftime("%-d %b %Y")

    body = "\n" + "".join(card(x, region, today) for x in listing) + "      "
    nl = replace_between(nl, "<!-- ERA:START -->", "<!-- ERA:END -->", body, "new-launches.html")
    nl = re.sub(r"(<!-- ERA-DATE:START -->).*?(<!-- ERA-DATE:END -->)", rf"\g<1>{stamp}\g<2>", nl)
    nl = re.sub(r"(<!-- ERA-COUNT:START -->).*?(<!-- ERA-COUNT:END -->)",
                rf"\g<1>{len(sell)} projects now selling and {len(up)} coming soon\g<2>", nl)

    # Homepage: 3 newest on sale; Serene's write-up cards compete by launch date.
    pool = [{"launchDate": x["launchDate"], "html": card(x, region, today, compact=True), "name": x["name"]} for x in sell]
    pool += home_pinned(items, today)
    featured = sorted(pool, key=lambda c: c["launchDate"], reverse=True)[:3]
    ix = replace_between(ix, "<!-- ERA:START -->", "<!-- ERA:END -->",
                         "\n" + "".join(c["html"] for c in featured) + "      ", "index.html")
    ix = re.sub(r"(<!-- ERA-DATE:START -->).*?(<!-- ERA-DATE:END -->)", rf"\g<1>{stamp}\g<2>", ix)

    open(nl_path, "w").write(nl)
    open(ix_path, "w").write(ix)
    rec = [{"name": smart_title(x["name"]), "status": x["_status"], "district": x.get("district"),
            "region": region(x)[0], "region_source": region(x)[1], "launchDate": x["launchDate"], "top": x.get("top"),
            "tenure": x.get("tenureCategory"), "developer": smart_title(x.get("developer") or ""),
            "units": x.get("numberOfUnits"), "available": (x.get("unitSummary") or {}).get("numberOfAvailableUnits"),
            "minPrice": (x.get("unitSummary") or {}).get("minPrice"), "image": x.get("mainImage")} for x in listing]
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    json.dump({"source": ERA_PAGE, "retrieved": datetime.now(SGT).isoformat(timespec="minutes"),
               "pinned_skipped": sorted(pinned), "projects": rec},
              open(os.path.join(ROOT, "data/new-launches.json"), "w"), indent=1)
    print(f"Updated: {len(sell)} selling, {len(up)} upcoming; homepage featured: {', '.join(smart_title(x['name']) for x in featured)}")


if __name__ == "__main__":
    main()
