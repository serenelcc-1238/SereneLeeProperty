#!/usr/bin/env python3
"""
Static HDB block pages for Serene's focus estates (Woodlands, Sembawang, Yishun),
e.g. /hdb/yishun/blk-468a-yishun-st-43.

Which blocks: every block with at least MIN_DEALS resales in the last 3 years, plus
every block with a resale of $1,000,000 or more. Rebuilt weekly from the same data
as the town pages (called from build_town_pages.py); blocks that drop out of the
list are removed, so no page is left with stale figures.

Each page: resales by flat type vs the town, every resale in the last 3 years, lease
left, nearest MRT stations, condos within 500 m, median rent, and links to nearby
block pages, the town guide and the Market Map lookup.
"""
import glob, html, json, math, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "hdb")
SITE = "https://sereneleeproperty.com"
TOWNS = ["WOODLANDS", "SEMBAWANG", "YISHUN"]
MIN_DEALS = 15
NEAR_M = 500
SQFT = 10.7639
FT = {"1": "1-room", "2": "2-room", "3": "3-room", "4": "4-room", "5": "5-room", "E": "Executive", "M": "Multi-gen"}
PT = {"C": "Condo", "E": "Executive condo"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load(p):
    with open(os.path.join(D, p)) as f:
        return json.load(f)


esc = lambda s: html.escape(str(s), quote=True)
money = lambda v: f"${round(v):,}"


def title(s):
    return re.sub(r"(^|[\s/(])(\w)", lambda m: m.group(1) + m.group(2).upper(), s.lower())


def ym(s):
    return f"{MON[int(s[5:7]) - 1]} {s[:4]}"


def months_back(ym_, n):
    y, m = int(ym_[:4]), int(ym_[5:7]) - n
    while m <= 0:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def med(a):
    s = sorted(a)
    n = len(s)
    return 0 if not n else (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def dist(a, b):
    dl = (a[0] - b[0]) * 110574
    dn = (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0]))
    return (dl * dl + dn * dn) ** 0.5


def fmt_m(m):
    return f"{m/1000:.1f} km" if m >= 1000 else f"{round(m, -1):.0f} m"


def absolutise(s):
    """The shell comes from a root-level page; make its relative links work in /hdb/<town>/."""
    return re.sub(r'((?:src|href)=")(?!https?:|/|#|mailto:|tel:|data:)', r"\1/", s)


def page_path(town_file, street, blk):
    return f"/hdb/{town_file}/blk-{slugify(blk)}-{slugify(street)}"


def select_blocks(f, million_keys):
    out = []
    for street, blocks in f["streets"].items():
        for blk, rows in blocks.items():
            if len(rows) >= MIN_DEALS or (street, blk) in million_keys:
                out.append((street, blk, rows))
    return out


def build_all(head, header, footer):
    """Returns {TOWN: [(street, blk, path, deals, latest_price, latest_ft), ...]} for the town pages."""
    market = load("market-data.json")
    last = market["hdb"]["last_month"]
    c12 = months_back(last, 12)
    stations = load("geo/stations.json")["stations"]
    try:
        rents_all = load("rents.json")
    except FileNotFoundError:
        rents_all = {"towns": {}, "label": ""}
    million = load("hdb/million.json")
    mkeys = {(d[3], d[2]) for d in million["deals"]}
    projects = {(p[0], p[1]): p for p in load("ura/projects.json")}
    ura_geo = {}
    for p in glob.glob(os.path.join(D, "geo", "ura", "d*.json")):
        d = os.path.basename(p)[1:3]
        for k, v in load(f"geo/ura/{os.path.basename(p)}").items():
            ura_geo[(d, k)] = v
    ura_cache = {}

    def ura_rows(d, key):
        if d not in ura_cache:
            ura_cache[d] = load(f"ura/d{d}.json")
        return ura_cache[d].get(key, [])

    head = absolutise(head)
    header = absolutise(header)
    footer = absolutise(footer)

    # remove last week's pages; only current blocks are written back
    for old in glob.glob(os.path.join(OUT, "*", "*.html")):
        os.remove(old)

    index = {}
    for town in TOWNS:
        info = market["hdb"]["towns"][town]
        tfile, tname = info["file"], title(town)
        f = load(f"hdb/{tfile}.json")
        geo = load(f"geo/hdb/{tfile}.json")
        models = f["models"]
        rents = rents_all["towns"].get(town, {})
        # town medians by flat type, last 12 months
        trow = [r for st in f["streets"].values() for rs in st.values() for r in rs if r[0] > c12]
        tmed = {ft: med([r[6] for r in trow if r[1] == ft]) for ft in FT if any(r[1] == ft for r in trow)}
        chosen = select_blocks(f, mkeys)
        paths = {(s, b): page_path(tfile, s, b) for s, b, _ in chosen}
        index[town] = []
        for street, blk, rows in chosen:
            rows = sorted(rows, key=lambda r: r[0], reverse=True)
            g = geo.get(f"{street}|{blk}")
            path = paths[(street, blk)]
            html_page = render_block(town, tname, tfile, street, blk, rows, g, stations, tmed, rents, rents_all.get("label", ""),
                                     c12, last, models, chosen, paths, geo, ura_geo, ura_rows, projects, market,
                                     head, header, footer)
            os.makedirs(os.path.join(OUT, tfile), exist_ok=True)
            with open(os.path.join(ROOT, path.lstrip("/") + ".html"), "w", encoding="utf-8") as fh:
                fh.write(html_page)
            index[town].append((street, blk, path, len(rows), rows[0][6], rows[0][1]))
        index[town].sort(key=lambda x: -x[3])
    n = sum(len(v) for v in index.values())
    print(f"built {n} block pages ({', '.join(f'{title(t)} {len(v)}' for t, v in index.items())})")
    return index


def render_block(town, tname, tfile, street, blk, rows, g, stations, tmed, rents, rent_label, c12, last, models,
                 chosen, paths, geo, ura_geo, ura_rows, projects, market, head, header, footer):
    st_t = title(street)
    name = f"Blk {blk} {st_t}"
    url = SITE + paths[(street, blk)]
    lease = rows[0][5]
    year = int(last[:4])
    left = 99 - (year - lease)
    r12 = [r for r in rows if r[0] > c12]
    psf = lambda r: r[6] / (r[3] * SQFT)
    fts = sorted({r[1] for r in rows}, key=lambda k: "12345EM".index(k))
    main_ft = max(fts, key=lambda k: sum(1 for r in rows if r[1] == k))
    n_mil = sum(1 for r in rows if r[6] >= 1_000_000)

    # ---------- flat-type table
    ft_rows = ""
    for ft in fts:
        a = [r for r in rows if r[1] == ft]
        a12 = [r for r in a if r[0] > c12]
        base = a12 or a
        m = med([r[6] for r in base])
        tm = tmed.get(ft)
        vs = ""
        if tm and a12:
            c = (m - tm) / tm * 100
            vs = f"{'+' if c >= 0 else ''}{c:.0f}%"
        ft_rows += (f"<tr><td><b>{FT[ft]}</b></td><td class='r'>{len(a)}</td>"
                    f"<td class='r'><b>{money(m)}</b><br><span class='bk-mut'>{'last 12 months' if a12 else 'last 3 years'}</span></td>"
                    f"<td class='r'>{money(med([psf(r) for r in base]))}</td>"
                    f"<td class='r'>{money(min(r[6] for r in a))} – {money(max(r[6] for r in a))}</td>"
                    f"<td class='r'>{money(tm) if tm else '–'}<br><span class='bk-mut'>{vs + ' vs town' if vs else ''}</span></td>"
                    f"<td class='r'>{money(rents[ft]) + '/mth' if rents.get(ft) else '–'}</td></tr>")

    # ---------- all deals
    deal_rows = "".join(
        f"<tr><td>{ym(r[0])}</td><td>{FT[r[1]]}</td><td>{r[2]:02d}–{r[2]+2:02d}</td>"
        f"<td class='r'>{r[3]:g} sqm<br><span class='bk-mut'>{round(r[3]*SQFT):,} sqft</span></td>"
        f"<td>{esc(models[r[4]] if r[4] < len(models) else '')}</td><td class='r'><b>{money(r[6])}</b></td><td class='r'>{money(psf(r))}</td></tr>"
        for r in rows)

    # ---------- MRT
    mrt_html, mrt_line = "", ""
    if g:
        near = [(stations[i], m) for i, m in g[3]]
        mrt_html = "".join(f"<li><b>{esc(s[0])}</b>{(' <span class=bk-mut>' + esc(s[1]) + '</span>') if s[1] else ''} · about {fmt_m(m)}</li>" for s, m in near)
        mrt_line = f"about {fmt_m(near[0][1])} from {near[0][0][0]}"
    postal = g[2] if g and g[2] else ""

    # ---------- condos within 500 m
    condo_html = ""
    if g:
        found = []
        for (d, key), v in ura_geo.items():
            if abs(v[0] - g[0]) > 0.006 or abs(v[1] - g[1]) > 0.006:
                continue
            m = dist(g, v)
            if m > NEAR_M:
                continue
            name_, street_ = key.split("|", 1)
            p = projects.get((name_, street_))
            if not p or p[4] not in PT or name_.upper().startswith("LANDED"):
                continue
            rs = [r for r in ura_rows(d, key) if r[5] == 1 and r[2] > 0]
            if not rs:
                continue
            last_r = max(rs, key=lambda r: r[0])
            pc = [r[4] / (r[2] * SQFT) for r in rs if r[0] >= months_back(last_r[0], 11)]
            found.append((m, name_, p, len(rs), med(pc) if pc else 0))
        found.sort()
        if found:
            condo_html = "".join(
                f"<tr><td><a href='/market-map?proj={esc(title(n))}'><b>{esc(title(n))}</b></a><br><span class='bk-mut'>{PT[p[4]]} · {esc(p[5])}</span></td>"
                f"<td class='r'>{fmt_m(m)}</td><td class='r'>{money(ps) + ' psf' if ps else '–'}</td></tr>"
                for m, n, p, cnt, ps in found[:6])

    # ---------- nearby block pages (internal links)
    sib = []
    if g:
        for s, b, rs in chosen:
            if (s, b) == (street, blk):
                continue
            gg = geo.get(f"{s}|{b}")
            if gg:
                sib.append((dist(g, gg), s, b, len(rs)))
        sib.sort()
    sib_html = "".join(f"<a class='bk-sib' href='{paths[(s, b)]}'><b>Blk {esc(b)}</b> {esc(title(s))}<span>{n} resales · {fmt_m(m)} away</span></a>" for m, s, b, n in sib[:8])

    # ---------- summary sentences (data-driven, unique per block)
    latest = rows[0]
    mf = [r for r in r12 if r[1] == main_ft] or [r for r in rows if r[1] == main_ft]
    mm = med([r[6] for r in mf])
    tm = tmed.get(main_ft)
    cmp_ = ""
    if tm:
        c = (mm - tm) / tm * 100
        cmp_ = f", {'about the same as' if abs(c) < 2 else ('%d%% above' % round(c) if c > 0 else '%d%% below' % round(-c))} the {tname} median of {money(tm)}"
    summary = [
        f"{len(rows)} flats in {name} were resold in the last 3 years ({len(r12)} in the last 12 months).",
        f"The most traded type is the {FT[main_ft]}, with a median of {money(mm)}{cmp_}.",
        f"The latest resale was a {FT[latest[1]]} on floors {latest[2]:02d}–{latest[2]+2:02d} for {money(latest[6])} in {ym(latest[0])}.",
        f"The lease started in {lease}, so about {left} years are left.",
    ]
    if mrt_line:
        summary.append(f"The block is {mrt_line} (straight-line).")
    if n_mil:
        summary.append(f"{n_mil} resale{'s' if n_mil > 1 else ''} here crossed $1 million.")

    # ---------- head
    t = f"{name} HDB Resale Prices | Serene Lee"
    if len(t) > 60:
        t = f"{name} Resale Prices | Serene Lee"
    desc = (f"{name}, {tname}: {len(rows)} HDB resales in 3 years, latest {FT[latest[1]]} {money(latest[6])} ({ym(latest[0])}). "
            f"Prices by flat type and floor, lease, nearest MRT.")
    if len(desc) > 155:
        desc = f"{name}, {tname}: {len(rows)} HDB resales in 3 years. Prices by flat type and floor, lease left and nearest MRT."
    h = re.sub(r"<title>.*?</title>", f"<title>{esc(t)}</title>", head, flags=re.S)
    h = re.sub(r'(<meta (?:name|property)="(?:description|og:description|twitter:description)" content=")[^"]*', lambda m: m.group(1) + esc(desc), h)
    h = re.sub(r'(<meta (?:property|name)="(?:og:title|twitter:title)" content=")[^"]*', lambda m: m.group(1) + esc(t), h)
    h = re.sub(r'(<link rel="canonical" href=")[^"]*', r"\g<1>" + url, h)
    h = re.sub(r'(<meta property="og:url" content=")[^"]*', r"\g<1>" + url, h)
    place = {"@context": "https://schema.org", "@type": "Residence", "name": f"{name}, {tname}, Singapore",
             "address": {"@type": "PostalAddress", "streetAddress": f"{blk} {st_t}", "addressLocality": tname,
                         "postalCode": postal, "addressCountry": "SG"}}
    if g:
        place["geo"] = {"@type": "GeoCoordinates", "latitude": g[0], "longitude": g[1]}
    h = h.replace("</head>", f'<script type="application/ld+json">{json.dumps(place)}</script>\n{CSS}\n</head>')

    lookup = f"/market-map?blk={esc(blk)}&amp;street={esc(st_t)}"
    wa = "https://wa.me/6580868568?text=" + re.sub(" ", "%20", f"Hi Serene, I saw the page for {name}. Could you give me a valuation of my flat?")
    hdb_date = market["hdb"]["fetched"][:10]
    body = f"""
<div class="page-hero page-hero-wide container">
  <nav class="bk-crumbs" aria-label="Breadcrumb"><a href="/town-guide">Town Guides</a> › <a href="/{tfile}">{esc(tname)}</a> › {esc(name)}</nav>
  <h1 style="font-size:2rem;">{esc(name)}: HDB resale prices</h1>
  <p class="bk-meta">{esc(tname)}{(' · Singapore ' + esc(postal)) if postal else ''} · Lease from {lease}, about {left} years left{(' · ' + esc(mrt_line)) if mrt_line else ''}</p>
</div>
<section style="padding-top:8px;"><div class="container">
  <div class="bk-kpis">
    <div class="bk-tile"><div class="k">Resales, last 3 years</div><div class="v">{len(rows)}</div><div class="s">{len(r12)} in the last 12 months</div></div>
    <div class="bk-tile"><div class="k">Latest resale</div><div class="v">{money(latest[6])}</div><div class="s">{FT[latest[1]]} · {ym(latest[0])}</div></div>
    <div class="bk-tile"><div class="k">{FT[main_ft]} median</div><div class="v">{money(mm)}</div><div class="s">{('Town: ' + money(tm)) if tm else ''}</div></div>
    <div class="bk-tile"><div class="k">Lease left</div><div class="v">~{left} yrs</div><div class="s">Lease from {lease}</div></div>
  </div>
  <div class="bk-card"><p class="bk-sum">{esc(' '.join(summary))}</p></div>

  <div class="bk-card"><h2>Prices by flat type</h2>
    <div class="bk-tablewrap"><table class="bk-table"><thead><tr><th>Flat type</th><th class="r">Resales</th><th class="r">Median price</th><th class="r">Median $psf</th><th class="r">Range</th><th class="r">{esc(tname)} median</th><th class="r">Median rent{(' (' + esc(rent_label) + ')') if rent_label else ''}</th></tr></thead><tbody>{ft_rows}</tbody></table></div>
    <p class="bk-src">Block medians use the last 12 months where available, otherwise 3 years. Town medians: last 12 months. Rent: {esc(tname)} median for whole-flat rentals.</p>
  </div>

  <div class="bk-card"><h2>Every resale in the last 3 years</h2>
    <div class="bk-tablewrap"><table class="bk-table"><thead><tr><th>Month</th><th>Flat type</th><th>Floors</th><th class="r">Size</th><th>Model</th><th class="r">Price</th><th class="r">$psf</th></tr></thead><tbody>{deal_rows}</tbody></table></div>
    <p class="bk-src">Month is when HDB registered the resale; floors are HDB's 3-storey bands. <a href="{lookup}">Highlight your own floor on the Market Map</a>.</p>
  </div>

  <div class="bk-two">
    {f'<div class="bk-card"><h2>Nearest MRT and LRT stations</h2><ul class="bk-list">{mrt_html}</ul><p class="bk-src">Straight-line distance from OneMap locations; walking is a little longer. <a href="{lookup}">See it on a map</a>.</p></div>' if mrt_html else ''}
    {f'<div class="bk-card"><h2>Condos and ECs within {NEAR_M} m</h2><div class="bk-tablewrap"><table class="bk-table"><thead><tr><th>Project</th><th class="r">Distance</th><th class="r">Median $psf</th></tr></thead><tbody>{condo_html}</tbody></table></div><p class="bk-src">Median $psf of single-unit deals in each project&#39;s latest 12 months on record (URA).</p></div>' if condo_html else ''}
  </div>

  {f'<div class="bk-card"><h2>Other blocks nearby</h2><div class="bk-sibs">{sib_html}</div><p class="bk-src"><a href="/{tfile}">All {esc(tname)} prices</a> · <a href="/right-sizing-north?town={tfile}">Right-sizing in {esc(tname)}</a></p></div>' if sib_html else ''}

  <p class="bk-src">Sources: HDB resale flat prices (<a href="https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/view" target="_blank" rel="noopener">data.gov.sg</a>), retrieved {hdb_date}; URA private residential transactions; OneMap (Singapore Land Authority) locations; HDB median rents. Updated weekly. Figures are past transactions, not a valuation.</p>
</div></section>

<section class="cta-banner"><div class="container cta-banner">
  <h2>Own a flat in {esc(name)}?</h2>
  <div class="btns">
    <a href="{lookup}" class="btn btn-navy">Check My Floor's Prices</a>
    <a href="{wa}" target="_blank" rel="noopener" class="btn bk-wa" style="background:#fff;color:var(--navy-900);">Get a Free Valuation</a>
  </div>
</div></section>
<script>(function(){{var a=document.querySelector(".bk-wa");if(a)a.onclick=function(){{try{{window.posthog&&posthog.capture("whatsapp_clicked",{{button_text:"Get a Free Valuation",button_location:"block page",page_path:location.pathname}});}}catch(e){{}}}};}})();</script>
"""
    return h + header + body + footer


CSS = """<style>
.bk-crumbs{font-size:.85rem;color:var(--muted);margin-bottom:8px}
.bk-crumbs a{color:var(--navy-900)}
.bk-meta{font-size:.9rem;color:var(--muted)}
.bk-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:0 0 20px}
@media(max-width:760px){.bk-kpis{grid-template-columns:1fr 1fr}}
.bk-tile{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 14px;min-width:0}
.bk-tile .k{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.bk-tile .v{font:600 1.35rem/1.25 'Fraunces',Georgia,serif;color:var(--navy-900);margin:4px 0 2px;font-variant-numeric:tabular-nums}
.bk-tile .s{font-size:.8rem;color:var(--muted)}
.bk-card{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:18px;margin-bottom:20px;min-width:0}
.bk-card h2{font-size:1.15rem;margin:0 0 10px}
.bk-sum{margin:0;font-size:.98rem;line-height:1.6}
.bk-two{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;margin-bottom:20px}
.bk-two .bk-card{margin-bottom:0}
.bk-two:empty{display:none}
@media(max-width:860px){.bk-two{grid-template-columns:1fr}}
.bk-tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
.bk-table{width:100%;border-collapse:collapse;font-size:.86rem}
.bk-table th{text-align:left;font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:var(--cream);padding:9px 12px;white-space:nowrap}
.bk-table td{padding:9px 12px;border-top:1px solid var(--line);vertical-align:top;font-variant-numeric:tabular-nums}
.bk-table .r{text-align:right;white-space:nowrap}
.bk-table a{color:var(--navy-900)}
.bk-mut{color:var(--muted);font-size:.76rem}
.bk-list{margin:0;padding-left:18px}
.bk-list li{margin:6px 0;font-size:.92rem}
.bk-src{font-size:.75rem;color:var(--muted);margin:10px 0 0;line-height:1.5}
.bk-src a{color:inherit}
.bk-sibs{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}
.bk-sib{display:flex;flex-direction:column;gap:2px;border:1px solid var(--line);border-radius:10px;padding:10px 12px;text-decoration:none;color:var(--navy-900);font-size:.9rem}
.bk-sib span{color:var(--muted);font-size:.78rem}
.bk-sib:hover{border-color:var(--gold)}
</style>"""
