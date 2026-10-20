#!/usr/bin/env python3
"""
One page per new launch in ERA's feed: /new-launch/<slug>.

Built weekly (called from build_town_pages.py) from:
  data/new-launches.json   ERA new launch listings (scripts/update_new_launches.py)
  data/ura/*.json          URA caveats: developer sales so far, nearby resale condos
  data/geo/*               OneMap locations: nearest MRT, nearest HDB town
  data/market-data.json    HDB town medians (for the upgrader comparison)

Projects that leave the feed (sold out or completed) lose their page on the next build.
Serene's rule (19 Oct 2026): no starting price for projects already selling, because
balance units sell at a different range; ask Serene for available units and prices.
"""
import glob, html, json, math, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "new-launch")
SITE = "https://sereneleeproperty.com"
SQFT = 10.7639
COMP_M = 1000
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DISTRICT = {
    "01": "Raffles Place, Marina", "02": "Tanjong Pagar, Chinatown", "03": "Queenstown, Tiong Bahru", "04": "Sentosa, Harbourfront",
    "05": "Pasir Panjang, Clementi", "06": "City Hall, Clarke Quay", "07": "Bugis, Beach Road", "08": "Little India, Farrer Park",
    "09": "Orchard, River Valley", "10": "Bukit Timah, Holland", "11": "Novena, Newton", "12": "Balestier, Toa Payoh",
    "13": "Macpherson, Potong Pasir", "14": "Geylang, Eunos", "15": "Katong, Marine Parade", "16": "Bedok, Upper East Coast",
    "17": "Loyang, Changi", "18": "Tampines, Pasir Ris", "19": "Serangoon, Hougang, Punggol", "20": "Bishan, Ang Mo Kio",
    "21": "Upper Bukit Timah, Clementi Park", "22": "Jurong, Boon Lay", "23": "Bukit Panjang, Choa Chu Kang", "24": "Lim Chu Kang, Tengah",
    "25": "Kranji, Woodlands", "26": "Upper Thomson, Springleaf", "27": "Yishun, Sembawang", "28": "Seletar, Yio Chu Kang",
}
TENURE = {"freehold": "Freehold", "leasehold_999": "999-year leasehold", "leasehold_99": "99-year leasehold"}
PTYPE = {"condo": "Condominium", "ec": "Executive condominium", "landed": "Landed"}

esc = lambda s: html.escape(str(s), quote=True)
money = lambda v: f"${round(v):,}"


def load(p):
    with open(os.path.join(D, p)) as f:
        return json.load(f)


def title(s):
    return re.sub(r"(^|[\s/(])(\w)", lambda m: m.group(1) + m.group(2).upper(), s.lower())


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def med(a):
    s = sorted(a)
    n = len(s)
    return 0 if not n else (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2)


def ym(s):
    return f"{MON[int(s[5:7]) - 1]} {s[:4]}"


def dmy(s):
    y, m, d = s[:10].split("-")
    return f"{int(d)} {MON[int(m) - 1]} {y}"


def quarter(s):
    return f"Q{(int(s[5:7]) - 1) // 3 + 1} {s[:4]}" if s else ""


def months_back(ym_, n):
    y, m = int(ym_[:4]), int(ym_[5:7]) - n
    while m <= 0:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def dist(a, b):
    dl = (a[0] - b[0]) * 110574
    dn = (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0]))
    return (dl * dl + dn * dn) ** 0.5


def fmt_m(m):
    return f"{m/1000:.1f} km" if m >= 1000 else f"{round(m, -1):.0f} m"


def absolutise(s):
    return re.sub(r'((?:src|href)=")(?!https?:|/|#|mailto:|tel:|data:)', r"\1/", s)


def coords(x):
    for a, b in (("latitude", "longitude"), ("lat", "lng")):
        try:
            return float(x[a]), float(x[b])
        except (KeyError, TypeError, ValueError):
            pass
    return None


def build_all(head, header, footer):
    nl = load("new-launches.json")
    market = load("market-data.json")
    stations = load("geo/stations.json")["stations"]
    projects = load("ura/projects.json")
    by_name = {}
    for p in projects:
        by_name.setdefault(norm(p[0]), []).append(p)
    ura_geo = {}
    for p in glob.glob(os.path.join(D, "geo", "ura", "d*.json")):
        d = os.path.basename(p)[1:3]
        for k, v in load(f"geo/ura/{os.path.basename(p)}").items():
            ura_geo[(d, k)] = v
    meta_by_key = {(p[2], f"{p[0]}|{p[1]}"): p for p in projects}
    hdb_pts = []
    for t, v in market["hdb"]["towns"].items():
        try:
            for key, g in load(f"geo/hdb/{v['file']}.json").items():
                hdb_pts.append((g[0], g[1], t))
        except FileNotFoundError:
            pass
    ura_cache = {}

    def ura(d):
        if d not in ura_cache:
            try:
                ura_cache[d] = load(f"ura/d{d}.json")
            except FileNotFoundError:
                ura_cache[d] = {}
        return ura_cache[d]

    head, header, footer = absolutise(head), absolutise(header), absolutise(footer)
    for old in glob.glob(os.path.join(OUT, "*.html")):
        os.remove(old)
    os.makedirs(OUT, exist_ok=True)
    retrieved = nl.get("retrieved", "")[:10]
    built = []
    for x in nl["projects"]:
        slug = x.get("slug") or "/new-launch/" + re.sub(r"[^a-z0-9]+", "-", x["name"].lower()).strip("-")
        d = (x.get("district") or "").lower().replace("d", "").zfill(2)
        # URA match: same name (and district when there are several)
        cands = [p for p in by_name.get(norm(x["name"]), []) if p[2] == d] or by_name.get(norm(x["name"]), [])
        up = max(cands, key=lambda p: p[6]) if cands else None
        g = coords(x)
        if not g and up:
            v = ura_geo.get((up[2], f"{up[0]}|{up[1]}"))
            g = (v[0], v[1]) if v else None
        page = render(x, slug, d, up, g, stations, hdb_pts, market, ura, ura_geo, meta_by_key, retrieved, head, header, footer)
        with open(os.path.join(ROOT, slug.lstrip("/") + ".html"), "w", encoding="utf-8") as fh:
            fh.write(page)
        built.append(slug)
    print(f"built {len(built)} new launch pages")
    return built


def render(x, slug, d, up, g, stations, hdb_pts, market, ura, ura_geo, meta_by_key, retrieved, head, header, footer):
    name = x["name"]
    url = SITE + slug
    selling = x["status"] == "selling"
    area = DISTRICT.get(d, "")
    loc = f"District {int(d)}{(' (' + area + ')') if area else ''}" if d.isdigit() else ""
    ten = TENURE.get(x.get("tenure"), "Leasehold")
    ptype = PTYPE.get(x.get("ptype") or "condo", "Condominium")
    topq = quarter(x.get("top"))
    street = title(up[1]) if up else ""
    facts = [("Developer", x.get("developer") or "–"), ("Type", ptype), ("Location", (street + ", " if street else "") + loc),
             ("Market segment", {"CCR": "Core Central Region (CCR)", "RCR": "Rest of Central Region (RCR)", "OCR": "Outside Central Region (OCR)"}.get(x.get("region"), x.get("region") or "–")),
             ("Tenure", ten), ("Expected completion (TOP)", topq or "To be advised"),
             ("Total units", f"{x['units']:,}" if x.get("units") else "–")]
    if selling and x.get("available") is not None and x.get("units") and x["available"] < x["units"]:
        facts.append(("Units still available (ERA listing)", f"{x['available']:,} of {x['units']:,}"))
    if x.get("mix"):
        facts.append(("Unit mix", x["mix"]))
    if x.get("minArea") and x.get("maxArea"):
        facts.append(("Unit sizes", f"{x['minArea']:,}–{x['maxArea']:,} sqft"))
    if x.get("minPsf") and x.get("maxPsf"):
        facts.append(("Price per sq ft (ERA listing)", f"${x['minPsf']:,.0f}–${x['maxPsf']:,.0f} psf"))
    if not selling:
        facts.append(("Launch", f"Expected {dmy(x['launchDate'])}" if x.get("launchDate") else "To be advised"))
        if x.get("minPrice"):
            facts.append(("Indicative starting price", f"From {money(x['minPrice'])}"))
    else:
        facts.append(("Launched", dmy(x["launchDate"])))
    facts_html = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in facts)

    # ---------- developer sales so far (URA caveats)
    sales_html, sales_line = "", ""
    if up:
        rows = ura(up[2]).get(f"{up[0]}|{up[1]}", [])
        ns = [r for r in rows if r[1] == 1]
        if ns:
            units = sum(r[5] for r in ns)
            lastm = max(r[0] for r in ns)
            rec = [r for r in ns if r[0] >= months_back(lastm, 2) and r[5] == 1 and r[2] > 0]
            ps = [r[4] / (r[2] * SQFT) for r in rec]
            allps = [r[4] / (r[2] * SQFT) for r in ns if r[5] == 1 and r[2] > 0]
            sales_line = f"URA records show {units:,} units sold by the developer up to {ym(lastm)}"
            sales_html = (f'<div class="nl-kpis"><div class="nl-tile"><div class="k">Units sold (URA)</div><div class="v">{units:,}</div><div class="s">Developer sales to {ym(lastm)}</div></div>'
                          f'<div class="nl-tile"><div class="k">Median $psf, latest 3 months</div><div class="v">{money(med(ps)) if ps else "–"}</div><div class="s">{len(ps)} caveats</div></div>'
                          f'<div class="nl-tile"><div class="k">$psf range so far</div><div class="v nl-sm">{(money(min(allps)) + " – " + money(max(allps))) if allps else "–"}</div><div class="s">All developer sales on record</div></div></div>'
                          f'<p class="nl-src">From caveats lodged with URA, which lag the actual sale by a few weeks and may not cover every unit. Prices change; ask Serene for the current price list.</p>')

    # ---------- location
    mrt_html, town_html, comp_html = "", "", ""
    if g:
        near = sorted((dist(g, (s[2], s[3])), s) for s in stations)[:3]
        mrt_html = "".join(f"<li><b>{esc(s[0])}</b>{(' <span class=nl-mut>' + esc(s[1]) + '</span>') if s[1] else ''} · about {fmt_m(m)}</li>" for m, s in near)
        best = min(((dist(g, (a, b)), t) for a, b, t in hdb_pts if abs(a - g[0]) < 0.02 and abs(b - g[1]) < 0.02), default=None)
        if best and best[0] <= 1500:
            t = best[1]
            info = market["hdb"]["towns"][t]
            q = market["hdb"]["quarters"]
            i = len(q) - 1 - (1 if market["hdb"].get("last_partial") else 0)
            p4 = (info.get("ft", {}).get("4", {}).get("p") or [0])[i] if info.get("ft", {}).get("4") else 0
            p5 = (info.get("ft", {}).get("5", {}).get("p") or [0])[i] if info.get("ft", {}).get("5") else 0
            town_html = (f'<p>The nearest HDB estate is <a href="/{info["file"]}"><b>{esc(title(t))}</b></a>, about {fmt_m(best[0])} away. '
                         f'{esc(title(t))} 4-room flats resold for an average of {money(p4 * 1000) if p4 else "–"} and 5-room flats {money(p5 * 1000) if p5 else "–"} in {q[i]}.</p>'
                         f'<p>Upgrading from an HDB flat nearby? <a href="/upgrade-checklist">Check your upgrade readiness</a> or '
                         f'<a href="/calculator">work out your budget</a>.</p>')
        comps = []
        for (dd, key), v in ura_geo.items():
            if abs(v[0] - g[0]) > 0.012 or abs(v[1] - g[1]) > 0.012:
                continue
            m = dist(g, v)
            if m > COMP_M:
                continue
            nm, st = key.split("|", 1)
            if up and nm == up[0] and st == up[1]:
                continue
            meta = meta_by_key.get((dd, key))
            if not meta or meta[4] not in ("C", "E") or nm.upper().startswith("LANDED"):
                continue
            rs = [r for r in ura(dd).get(key, []) if r[1] == 3 and r[5] == 1 and r[2] > 0]
            if len(rs) < 3:
                continue
            lastm = max(r[0] for r in rs)
            rr = [r for r in rs if r[0] >= months_back(lastm, 11)]
            comps.append((m, nm, meta, len(rr), med([r[4] / (r[2] * SQFT) for r in rr]), lastm))
        comps.sort()
        if comps:
            comp_html = "".join(
                f"<tr><td><a href='/market-map?proj={esc(title(nm))}'><b>{esc(title(nm))}</b></a><br><span class='nl-mut'>{'Executive condo' if meta[4] == 'E' else 'Condo'} · {esc(meta[5])}</span></td>"
                f"<td class='r'>{fmt_m(m)}</td><td class='r'>{money(ps)} psf</td><td class='r'>{n}</td><td>{ym(lm)}</td></tr>"
                for m, nm, meta, n, ps, lm in comps[:8])

    # ---------- text + FAQs (facts only)
    intro = (f"{name} is a {ten.lower()} {ptype.lower()} by {x.get('developer') or 'the developer'}"
             f"{' at ' + street if street else ''}{', in ' + loc if loc else ''}, with "
             f"{x['units']:,} units" if x.get("units") else f"{name} is a {ten.lower()} {ptype.lower()}{' in ' + loc if loc else ''}")
    intro += f", expected to complete in {topq}." if topq else "."
    if selling:
        intro += f" It launched on {dmy(x['launchDate'])}."
        if sales_line:
            intro += f" {sales_line}."
    else:
        intro += f" Sales are expected to start around {dmy(x['launchDate'])}." if x.get("launchDate") else ""
    faqs = [(f"Where is {name}?", f"{name} is {('at ' + street + ', ') if street else ''}in {loc or 'Singapore'}" + (f", about {fmt_m(near[0][0])} from {near[0][1][0]}." if g else ".")),
            (f"When will {name} be completed?", f"The expected TOP is {topq}, based on ERA's new launch listing." if topq else "The completion date has not been announced."),
            (f"How many units does {name} have?", f"{x['units']:,} units{(', with ' + x['mix'].lower() + ' layouts') if x.get('mix') else ''}." if x.get("units") else "The unit count has not been announced."),
            (f"What is the tenure of {name}?", f"{ten}.")]
    faq_html = "".join(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>" for q, a in faqs)
    ld = [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}]
    res = {"@context": "https://schema.org", "@type": "ApartmentComplex", "name": name, "url": url,
           "address": {"@type": "PostalAddress", "addressCountry": "SG", **({"streetAddress": street} if street else {})}}
    if x.get("units"):
        res["numberOfAccommodationUnits"] = x["units"]
    if g:
        res["geo"] = {"@type": "GeoCoordinates", "latitude": round(g[0], 6), "longitude": round(g[1], 6)}
    if x.get("image"):
        res["image"] = x["image"]
    ld.append(res)

    t = f"{name}: Prices, Units & TOP | Serene Lee"
    if len(t) > 60:
        t = f"{name} | New Launch | Serene Lee"
    if len(t) > 60:
        t = f"{name} | Serene Lee"
    desc = (f"{name}, {ten.lower()} {ptype.lower()}{' in ' + loc if loc else ''}: {x['units']:,} units, TOP {topq or 'TBA'}. "
            if x.get("units") else f"{name}, {ten.lower()} {ptype.lower()}{' in ' + loc if loc else ''}. ")
    desc += "Developer sales, nearest MRT and nearby condo prices." if selling else "Launch details, nearest MRT and nearby condo prices."
    if len(desc) > 155:
        desc = f"{name}: {ptype.lower()}, {x['units'] or ''} units, TOP {topq or 'TBA'}. Sales so far, MRT and nearby prices."[:155]
    h = re.sub(r"<title>.*?</title>", f"<title>{esc(t)}</title>", head, flags=re.S)
    h = re.sub(r'(<meta (?:name|property)="(?:description|og:description|twitter:description)" content=")[^"]*', lambda m: m.group(1) + esc(desc), h)
    h = re.sub(r'(<meta (?:property|name)="(?:og:title|twitter:title)" content=")[^"]*', lambda m: m.group(1) + esc(t), h)
    h = re.sub(r'(<link rel="canonical" href=")[^"]*', r"\g<1>" + url, h)
    h = re.sub(r'(<meta property="og:url" content=")[^"]*', r"\g<1>" + url, h)
    if x.get("image"):
        h = re.sub(r'(<meta (?:property|name)="(?:og:image|twitter:image)" content=")[^"]*', lambda m: m.group(1) + esc(x["image"]), h)
    h = h.replace("</head>", "".join(f'<script type="application/ld+json">{json.dumps(o)}</script>\n' for o in ld) + CSS + "\n</head>")

    if selling:
        cta_txt, msg = "Avail Units & Prices - check with Serene", f"Hi Serene, I'd like the available units and prices for {name}."
    else:
        cta_txt, msg = "Register for Preview", f"Hi Serene, I'd like to register for the preview of {name}."
    wa = "https://wa.me/6580868568?text=" + re.sub(" ", "%20", esc(msg))
    status = "Now selling" if selling else (f"Launching {dmy(x['launchDate'])}" if x.get("launchDate") else "Upcoming")
    img = (f'<div class="nl-img"><img src="{esc(x["image"])}" alt="{esc(name)} artist&#39;s impression" loading="eager"><span class="nl-badge">{esc(status)}</span></div>'
           if x.get("image") else "")

    body = f"""
<div class="page-hero page-hero-wide container">
  <nav class="nl-crumbs" aria-label="Breadcrumb"><a href="/new-launches">New Launches</a> › {esc(name)}</nav>
  <div class="nl-hero">
    <div>
      <span class="eyebrow">{esc(status)}</span>
      <h1 style="font-size:2.1rem;margin-top:10px">{esc(name)}</h1>
      <p class="nl-lead">{esc(intro)}</p>
      <div class="nl-btns"><a class="btn btn-gold nl-wa" target="_blank" rel="noopener" href="{wa}">{esc(cta_txt)}</a>
        <a class="btn btn-navy" href="/calculator">Check my budget</a></div>
    </div>
    {img}
  </div>
</div>
<section style="padding-top:8px;"><div class="container">
  <div class="nl-two">
    <div class="nl-card"><h2>Key facts</h2><table class="nl-facts"><tbody>{facts_html}</tbody></table>
      <p class="nl-src">From ERA Realty's new launch listings, retrieved {esc(dmy(retrieved)) if retrieved else ''}. Details can change; please refer to the developer's official materials.</p></div>
    <div class="nl-card"><h2>Location</h2>
      {f'<h3 class="nl-h3">Nearest MRT and LRT stations</h3><ul class="nl-list">{mrt_html}</ul><p class="nl-src">Straight-line distance from OneMap locations.</p>' if mrt_html else '<p>Location details will be added once the first sales are recorded.</p>'}
      {f'<h3 class="nl-h3">Nearby HDB estate</h3>{town_html}' if town_html else ''}
    </div>
  </div>
  {f'<div class="nl-card"><h2>Developer sales so far</h2>{sales_html}</div>' if sales_html else ''}
  {f'<div class="nl-card"><h2>Resale condos within {COMP_M // 1000} km</h2><div class="nl-tablewrap"><table class="nl-table"><thead><tr><th>Project</th><th class="r">Distance</th><th class="r">Median $psf</th><th class="r">Resales</th><th>Latest</th></tr></thead><tbody>{comp_html}</tbody></table></div><p class="nl-src">Resale $psf, single-unit deals in each project&#39;s latest 12 months on record (URA caveats). Useful for comparing a new launch with older homes nearby.</p></div>' if comp_html else ''}
  <div class="nl-card nl-faq"><h2>Common questions</h2>{faq_html}</div>
  <p class="nl-src">Serene Lee, ERA Realty Network (CEA R027578Z). Information is for general reference only and is not an offer or a valuation. <a href="/new-launches">See all new launches</a>.</p>
</div></section>
<section class="cta-banner"><div class="container cta-banner">
  <h2>Interested in {esc(name)}?</h2>
  <div class="btns">
    <a href="/new-launches" class="btn btn-navy">Compare Other Launches</a>
    <a href="{wa}" target="_blank" rel="noopener" class="btn nl-wa" style="background:#fff;color:var(--navy-900);">{esc(cta_txt)}</a>
  </div>
</div></section>
<script>(function(){{document.querySelectorAll(".nl-wa").forEach(function(a){{a.addEventListener("click",function(){{try{{window.posthog&&posthog.capture("whatsapp_clicked",{{button_text:a.textContent.trim(),button_location:"new launch page",project:{json.dumps(name)},page_path:location.pathname}});}}catch(e){{}}}});}});}})();</script>
"""
    return h + header + body + footer


CSS = """<style>
.nl-crumbs{font-size:.85rem;color:var(--muted);margin-bottom:10px}
.nl-crumbs a{color:var(--navy-900)}
.nl-hero{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:28px;align-items:center}
@media(max-width:860px){.nl-hero{grid-template-columns:1fr}}
.nl-lead{font-size:1rem;max-width:620px}
.nl-btns{display:flex;flex-wrap:wrap;gap:10px;margin-top:14px}
.nl-img{position:relative;border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow);aspect-ratio:4/3;background:var(--cream)}
.nl-img img{width:100%;height:100%;object-fit:cover;display:block}
.nl-badge{position:absolute;left:12px;top:12px;background:var(--gold);color:var(--navy-900);font-weight:700;font-size:.78rem;border-radius:999px;padding:4px 12px}
.nl-card{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:18px;margin-bottom:20px;min-width:0}
.nl-card h2{font-size:1.15rem;margin:0 0 10px}
.nl-h3{font-size:.95rem;margin:12px 0 6px}
.nl-two{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;margin-bottom:20px}
.nl-two .nl-card{margin-bottom:0}
@media(max-width:860px){.nl-two{grid-template-columns:1fr}}
.nl-facts{width:100%;border-collapse:collapse;font-size:.9rem}
.nl-facts th{text-align:left;font-weight:600;color:var(--muted);padding:8px 10px 8px 0;border-top:1px solid var(--line);width:44%;vertical-align:top}
.nl-facts td{padding:8px 0;border-top:1px solid var(--line);color:var(--navy-900)}
.nl-facts tr:first-child th,.nl-facts tr:first-child td{border-top:0}
.nl-list{margin:0;padding-left:18px}.nl-list li{margin:5px 0;font-size:.92rem}
.nl-kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
@media(max-width:700px){.nl-kpis{grid-template-columns:1fr}}
.nl-tile{background:var(--cream);border-radius:12px;padding:12px 14px}
.nl-tile .k{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.nl-tile .v{font:600 1.35rem/1.25 'Fraunces',Georgia,serif;color:var(--navy-900);margin:4px 0 2px;font-variant-numeric:tabular-nums}
.nl-tile .v.nl-sm{font-size:1.05rem}
.nl-tile .s{font-size:.8rem;color:var(--muted)}
.nl-tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
.nl-table{width:100%;border-collapse:collapse;font-size:.86rem}
.nl-table th{text-align:left;font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:var(--cream);padding:9px 12px;white-space:nowrap}
.nl-table td{padding:9px 12px;border-top:1px solid var(--line);vertical-align:top;font-variant-numeric:tabular-nums}
.nl-table .r{text-align:right;white-space:nowrap}
.nl-table a{color:var(--navy-900)}
.nl-mut{color:var(--muted);font-size:.76rem}
.nl-src{font-size:.75rem;color:var(--muted);margin:10px 0 0;line-height:1.5}
.nl-src a{color:inherit}
.nl-faq h3{font-size:1rem;margin:14px 0 4px}
.nl-faq p{color:var(--muted);font-size:.92rem;margin:0}
</style>"""
