#!/usr/bin/env python3
"""
Builds one static page per HDB town (e.g. woodlands.html -> /woodlands) from the
weekly data files, so search engines can read the prices without running JS.

Inputs (all refreshed weekly by other scripts):
  data/market-data.json, data/hdb/<town>.json        HDB resale (data.gov.sg)
  data/ura/d<NN>.json, data/ura/projects.json        URA private transactions
  data/geo/*                                         OneMap locations / nearest MRT
  data/new-launches.json                             ERA new launch feed

Header, footer and <head> boilerplate are copied from million-dollar-hdb.html so
menu changes flow through automatically.

Run: python3 scripts/build_town_pages.py            (builds every town in TOWNS)
Standard library only.
"""
import html, json, os, re, statistics
from datetime import datetime

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D = os.path.join(ROOT, "data")
SITE = "https://sereneleeproperty.com"
SQFT = 10.7639

# Every HDB town in data/market-data.json gets a page at /<town-file-name>.
# Set INDEX = False to keep all town pages out of Google and the sitemap.
INDEX = True
NEAR_M = 500           # private projects within this distance of a town's blocks count as "in and around" it
REGION_ORDER = ["North", "North-East", "East", "West", "Central"]

FT = {"1": "1-room", "2": "2-room", "3": "3-room", "4": "4-room", "5": "5-room", "E": "Executive", "M": "Multi-gen"}
SALE = {1: "New sale", 2: "Sub sale", 3: "Resale"}
PT = {"C": "Condo", "E": "Executive condo", "L": "Landed"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load(p):
    with open(os.path.join(D, p)) as f:
        return json.load(f)


def esc(s):
    return html.escape(str(s), quote=True)


def title(s):
    return re.sub(r"(^|[\s/(])(\w)", lambda m: m.group(1) + m.group(2).upper(), s.lower())


def money(v):
    return f"${round(v):,}"


def money_k(v):
    return f"${v/1e6:.2f}M" if v >= 1e6 else f"${round(v/1000):,}k"


def ym(s):
    return f"{MON[int(s[5:7]) - 1]} {s[:4]}"


def med(a):
    return statistics.median(a) if a else 0


def months_back(last, n):
    y, m = int(last[:4]), int(last[5:7]) - n
    while m <= 0:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def fmt_date(iso):
    d = datetime.fromisoformat(iso[:16])
    return f"{d.day} {MON[d.month - 1]} {d.year}"


def pct(a, b):
    if not a or not b:
        return ""
    c = (a - b) / b * 100
    cls = "up" if c > 0.5 else "down" if c < -0.5 else ""
    return f'<span class="tp-chg {cls}">{"+" if c > 0 else ""}{c:.1f}%</span>'


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ------------------------------------------------------------------ charts
def line_chart(quarters, series, label):
    """Static SVG line chart: series = [(name, colour, [values or 0])]."""
    W, H, L, R, T, B = 640, 260, 56, 30, 14, 34
    vals = [v for _, _, s in series for v in s if v]
    if not vals:
        return ""
    lo, hi = min(vals) * 0.95, max(vals) * 1.03
    step = 50 if hi - lo < 400 else 100 if hi - lo < 900 else 200
    lo = int(lo // step * step)
    x = lambda i: L + i * (W - L - R) / max(len(quarters) - 1, 1)
    y = lambda v: T + (hi - v) * (H - T - B) / (hi - lo)
    out = [f'<svg class="tp-chart" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}">']
    g = lo
    while g <= hi:
        out.append(f'<line x1="{L}" x2="{W-R}" y1="{y(g):.1f}" y2="{y(g):.1f}" class="grid"/>'
                   f'<text x="{L-6}" y="{y(g)+4:.1f}" text-anchor="end">${g:,}k</text>')
        g += step
    for i, q in enumerate(quarters):
        if i % 2 == 0 or i == len(quarters) - 1:
            out.append(f'<text x="{x(i):.1f}" y="{H-10}" text-anchor="middle">{q.replace(" ", "&#160;")}</text>')
    for name, col, s in series:
        pts = [(x(i), y(v)) for i, v in enumerate(s) if v]
        if len(pts) < 2:
            continue
        out.append(f'<polyline fill="none" stroke="{col}" stroke-width="2.5" points="' +
                   " ".join(f"{a:.1f},{b:.1f}" for a, b in pts) + '"/>')
        a, b = pts[-1]
        out.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="3.5" fill="{col}"/>')
    out.append("</svg>")
    legend = "".join(f'<span><i style="background:{c}"></i>{esc(n)}</span>' for n, c, s in series if any(s))
    return "".join(out) + f'<div class="tp-key">{legend}</div>'


# ------------------------------------------------------------------ page
def nearby_projects(geo_blocks):
    """Private projects within NEAR_M of any block of the town -> {(district, key): metres}."""
    import math
    grid = {}
    for v in geo_blocks.values():
        grid.setdefault((round(v[0] * 100), round(v[1] * 100)), []).append(v)
    out = {}
    for path in sorted(os.listdir(os.path.join(D, "geo", "ura"))):
        d = path[1:3]
        for key, v in load(f"geo/ura/{path}").items():
            gx, gy = round(v[0] * 100), round(v[1] * 100)
            best = 9e9
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for b in grid.get((gx + dx, gy + dy), []):
                        dl = (v[0] - b[0]) * 110574
                        dn = (v[1] - b[1]) * 111320 * math.cos(math.radians(v[0]))
                        best = min(best, (dl * dl + dn * dn) ** 0.5)
            if best <= NEAR_M:
                out[(d, key)] = best
    return out


def build(town, cfg, shell_head, shell_header, shell_footer, picker):
    market = load("market-data.json")
    th = market["hdb"]["towns"][town]
    f = load(f"hdb/{th['file']}.json")
    geo = load(f"geo/hdb/{th['file']}.json")
    st = load("geo/stations.json")
    S = st["stations"]
    last = market["hdb"]["last_month"]
    c12, c24 = months_back(last, 12), months_back(last, 24)  # (c12, last] = last 12 months
    tname = title(town)
    page = cfg["slug"]
    url = f"{SITE}/{page}"
    now_year = int(last[:4])

    rows = []  # flatten: month, ft, storey, sqm, model, lease, price, street, blk
    for street, blocks in f["streets"].items():
        for blk, rs in blocks.items():
            for r in rs:
                rows.append(r + [street, blk])
    r12 = [r for r in rows if r[0] > c12]
    r24 = [r for r in rows if c24 < r[0] <= c12]
    psf = lambda r: r[6] / (r[3] * SQFT)

    # --- flat type table
    ft_rows, ft_med = [], {}
    for code in ["2", "3", "4", "5", "E", "M"]:
        a = [r for r in r12 if r[1] == code]
        if not a:
            continue
        b = [r for r in r24 if r[1] == code]
        m, mb = med([r[6] for r in a]), med([r[6] for r in b])
        ft_med[code] = m
        rent = RENTS.get(town, {}).get(code)
        ft_rows.append(
            f"<tr><td><b>{FT[code]}</b></td><td class='r'>{len(a):,}</td><td class='r'><b>{money(m)}</b></td>"
            f"<td class='r'>{money(med([psf(r) for r in a]))}</td><td class='r'>{money_k(min(r[6] for r in a))} – {money_k(max(r[6] for r in a))}</td>"
            f"<td class='r'>{pct(m, mb) if len(b) >= 10 else '–'}</td>"
            f"<td class='r'>{money(rent) + '/mth' if rent else '–'}</td></tr>")
    all12 = [r[6] for r in r12]
    m4 = ft_med.get("4", 0)

    # --- quarterly trend (last 12 full quarters)
    q = market["hdb"]["quarters"]
    endq = len(q) - 1 - (1 if market["hdb"].get("last_partial") else 0)
    qs = list(range(max(0, endq - 11), endq + 1))
    cols = {"3": "#8ea8c1", "4": "#0b2a4a", "5": "#c9a227", "E": "#9b4d2e"}
    series = [(FT[k], cols[k], [th["ft"][k]["p"][i] if th["ft"][k]["n"][i] >= 3 else 0 for i in qs])
              for k in ["3", "4", "5", "E"] if k in th["ft"]]
    chart = line_chart([q[i] for i in qs], series, f"Average {tname} HDB resale price by quarter and flat type")
    q4 = th["ft"].get("4", {}).get("p", [])
    trend_line = ""
    if q4 and q4[endq] and q4[endq - 4]:
        c = (q4[endq] - q4[endq - 4]) / q4[endq - 4] * 100
        trend_line = (f"The average 4-room resale was about ${q4[endq]:,}k in {q[endq]}, "
                      f"{'up' if c >= 0 else 'down'} {abs(c):.1f}% from ${q4[endq-4]:,}k a year earlier ({q[endq-4]}).")

    # --- MRT: blocks grouped by nearest station
    by_st, far = {}, []
    for key, v in geo.items():
        street, blk = key.split("|", 1)
        i, dist = v[3][0]
        (by_st.setdefault(i, []) if dist <= 1000 else far).append((street, blk, dist))
    blk_dist = {f"{k}": v[3][0][1] for k, v in geo.items()}
    mrt_rows = []
    for i, blks in sorted(by_st.items(), key=lambda kv: -len(kv[1])):
        if len(blks) < 5:
            continue
        keys = {f"{s}|{b}" for s, b, _ in blks}
        d4 = [r[6] for r in r12 if r[1] == "4" and f"{r[7]}|{r[8]}" in keys]
        d5 = [r[6] for r in r12 if r[1] == "5" and f"{r[7]}|{r[8]}" in keys]
        near500 = sum(1 for _, _, d in blks if d <= 500)
        s = S[i]
        mrt_rows.append(
            f"<tr><td><a href='/market-map?mrt={slug(s[0])}&amp;r=500'><b>{esc(s[0])}</b></a><br><span class='tp-mut'>{esc(s[1])}</span></td>"
            f"<td class='r'>{len(blks)}</td><td class='r'>{near500}</td>"
            f"<td class='r'>{money(med(d4)) if len(d4) >= 5 else '–'}</td><td class='r'>{money(med(d5)) if len(d5) >= 5 else '–'}</td></tr>")
    mrt_names = [S[i][0] for i, b in sorted(by_st.items(), key=lambda kv: -len(kv[1])) if len(b) >= 5]
    # 4-room premium for being within 500 m of an MRT
    n4 = [r[6] for r in r12 if r[1] == "4" and blk_dist.get(f"{r[7]}|{r[8]}", 9e9) <= 500]
    f4 = [r[6] for r in r12 if r[1] == "4" and blk_dist.get(f"{r[7]}|{r[8]}", 0) > 500]
    mrt_gap = ""
    if len(n4) >= 20 and len(f4) >= 20:
        g = med(n4) - med(f4)
        mrt_gap = (f"4-room flats within 500 m of an MRT station sold at a median of {money(med(n4))} in the last 12 months, "
                   f"versus {money(med(f4))} further away, a difference of about {money(abs(g))} "
                   f"({'more' if g >= 0 else 'less'} near the MRT). Flat age and size also differ between the two groups, so treat this as a guide, not a rule.")

    # --- lease age bands (4-room and 5-room)
    bands = [("Before 1990", 0, 1989), ("1990 – 2004", 1990, 2004), ("2005 – 2014", 2005, 2014), ("2015 onwards", 2015, 9999)]
    lease_rows = []
    for lab, a, b in bands:
        cells = []
        for code in ("4", "5"):
            d = [r[6] for r in r12 if r[1] == code and a <= r[5] <= b]
            cells.append(f"<td class='r'>{money(med(d)) if len(d) >= 5 else '–'}<br><span class='tp-mut'>{len(d)} deals</span></td>")
        if not a:
            left = f"under {99 - (now_year - b)} yrs"
        elif b >= 9999:
            left = f"{99 - (now_year - a)}+ yrs"
        else:
            left = f"about {99 - (now_year - a)}–{99 - (now_year - b)} yrs"
        lease_rows.append(f"<tr><td><b>{lab}</b><br><span class='tp-mut'>Lease left: {left}</span></td>{''.join(cells)}</tr>")

    # --- top resales
    top = sorted(r12, key=lambda r: -r[6])[:5]
    top_rows = "".join(
        f"<tr><td>{ym(r[0])}</td><td><a href='/market-map?blk={esc(r[8])}&amp;street={esc(title(r[7]))}'>Blk {esc(r[8])} {esc(title(r[7]))}</a></td>"
        f"<td>{FT[r[1]]}</td><td>{r[2]:02d}–{r[2]+2:02d}</td><td class='r'><b>{money(r[6])}</b></td></tr>" for r in top)

    # --- private: projects in and around the town (by OneMap location)
    near = nearby_projects(geo)
    dists = {}
    for (dd, _k) in near:
        dists[dd] = dists.get(dd, 0) + 1
    d_main = sorted(dists, key=lambda k: -dists[k])
    d = d_main[0] if d_main else ""
    launch_districts = [k for k in d_main if dists[k] >= max(3, 0.2 * len(near))] or d_main[:1]
    ura, ugeo = {}, {}
    for dd in dists:
        u, g = load(f"ura/d{dd}.json"), load(f"geo/ura/d{dd}.json")
        for (d2, key) in near:
            if d2 == dd and key in u:
                ura[key], ugeo[key] = u[key], g.get(key)
    projects = {(p[0], p[1]): p for p in load("ura/projects.json") if p[2] in dists}
    plast = max((r[0] for rs in ura.values() for r in rs), default=last)
    pc12, pc24 = months_back(plast, 12), months_back(plast, 24)
    ppsf = lambda r: r[4] / (r[2] * SQFT)
    pte_rows, pte_med = [], {}
    for code in ("C", "E"):
        a = [r for rs in ura.values() for r in rs if r[1] == 3 and r[6] == code and r[5] == 1 and r[0] > pc12]
        b = [r for rs in ura.values() for r in rs if r[1] == 3 and r[6] == code and r[5] == 1 and pc24 < r[0] <= pc12]
        if not a:
            continue
        pte_med[code] = med([r[4] for r in a])
        pte_rows.append(
            f"<tr><td><b>{PT[code]} resale</b></td><td class='r'>{len(a)}</td><td class='r'><b>{money(pte_med[code])}</b></td>"
            f"<td class='r'>{money(med([ppsf(r) for r in a]))}</td><td class='r'>{pct(med([ppsf(r) for r in a]), med([ppsf(r) for r in b])) if len(b) >= 10 else '–'}</td></tr>")
    proj, proj_all = [], [k for k in ura if not k.upper().startswith("LANDED HOUSING")]
    for key, rs in ura.items():
        name, street = key.split("|", 1)
        if name.upper().startswith("LANDED HOUSING"):
            continue
        a = [r for r in rs if r[0] > pc12 and r[5] == 1]
        if len(a) < 3:
            continue
        meta = projects.get((name, street))
        pt = meta[4] if meta else ""
        if pt not in ("C", "E"):
            continue
        g = ugeo.get(key)  # [lat, lng, postal, nearest stations]
        near = f"{esc(S[g[3][0][0]][0])}, {g[3][0][1]:,} m" if g else "–"
        kinds = {}
        for r in a:
            kinds[r[1]] = kinds.get(r[1], 0) + 1
        mix = SALE[max(kinds, key=kinds.get)] + ("s" if len(kinds) == 1 else " mostly")
        proj.append((len(a), f"<tr><td><a href='/market-map?proj={esc(title(name))}'><b>{esc(title(name))}</b></a><br><span class='tp-mut'>{PT[pt]} · {esc(meta[5] if meta else '')}</span></td>"
                     f"<td class='r'>{len(a)}<br><span class='tp-mut'>{mix}</span></td><td class='r'>{money(med([ppsf(r) for r in a]))}</td><td>{near}</td></tr>"))
    proj_rows = "".join(r for _, r in sorted(proj, key=lambda x: -x[0])[:10])

    # --- new launches
    nl = load("new-launches.json")
    launches = [p for p in nl["projects"] if p.get("district", "")[1:] in launch_districts]
    dlab = " / ".join(f"D{k}" for k in launch_districts)
    ten = {"leasehold_99": "99-year leasehold", "freehold": "Freehold"}
    nl_rows = "".join(
        f"<tr><td><b>{esc(p['name'])}</b><br><span class='tp-mut'>{esc(p.get('developer',''))}</span></td><td>{esc(p.get('status','').title())}</td>"
        f"<td>{esc(ten.get(p.get('tenure'), p.get('tenure','')))}</td><td>{('TOP ' + p['top'][:4]) if p.get('top') else '–'}</td>"
        f"<td class='r'>{money(p['minPrice']) if p.get('minPrice') else 'TBC'}</td></tr>" for p in launches)

    # --- persona maths
    up = ""
    base_ft = "4" if m4 else ("5" if ft_med.get("5") else "3")
    base = ft_med.get(base_ft, 0)
    tgt = "E" if pte_med.get("E") else ("C" if pte_med.get("C") else "")
    if base and tgt:
        other = f", and a resale condo for about <b>{money(pte_med['C'])}</b>" if tgt == "E" and pte_med.get("C") else ""
        up = (f"<p>A typical {tname} {FT[base_ft]} flat resold for about <b>{money(base)}</b> in the last 12 months. A resale "
              f"{PT[tgt].lower()} in and around {tname} went for about <b>{money(pte_med[tgt])}</b>{other}. "
              f"The gap of roughly <b>{money(pte_med[tgt] - base)}</b> to {'an EC' if tgt=='E' else 'a condo'} is what your sale proceeds, CPF and a new loan need to cover.</p>")
    down = ""
    big = ft_med.get("E") or ft_med.get("5")
    small = ft_med.get("3") or ft_med.get("2")
    if big and small and big > small:
        bl = "Executive" if ft_med.get("E") else "5-room"
        sl = "3-room" if ft_med.get("3") else "2-room"
        down = (f"<p>{'An' if bl[0] in 'AEIOU' else 'A'} {bl} flat here resold for about <b>{money(big)}</b>, and a {sl} for about <b>{money(small)}</b>. "
                f"Moving from one to the other in {tname} could free up roughly <b>{money(big - small)}</b> before stamp duty, agent fees "
                f"and the CPF refund to your own account.</p>")

    # --- FAQ
    faqs = [
        (f"How much is a 4-room HDB flat in {tname}?",
         f"In the last 12 months ({ym(months_back(last, 11))} to {ym(last)}), {len([r for r in r12 if r[1]=='4']):,} 4-room flats resold in {tname} "
         f"at a median price of {money(m4)}. Prices depend mostly on the remaining lease, floor and distance to the MRT." if m4 else ""),
        (f"Which MRT stations serve {tname}?",
         f"Most {tname} HDB blocks are nearest to {', '.join(mrt_names[:-1])} or {mrt_names[-1]} station, based on OneMap locations." if len(mrt_names) > 1 else ""),
        (f"Is {tname} a good place to upgrade or right-size?",
         f"{tname} has a range of flat ages and sizes, with {len(proj_all)} condo and EC projects in and around the estate, so upgraders and "
         f"right-sizers can often stay in the same area. The right choice depends on your budget, CPF and timeline; Serene can work out the numbers with you."),
        (f"Are there new launches near {tname}?",
         (f"Yes. {', '.join(p['name'] for p in launches)} {'is' if len(launches)==1 else 'are'} in {dlab}, the postal district{'s' if len(launch_districts)>1 else ''} around {tname}. See the New Launches page for details."
          if launches else f"There are no new launches in {dlab} in the current feed. See the New Launches page for options elsewhere.")),
    ]
    faqs = [(qq, aa) for qq, aa in faqs if aa]
    faq_html = "".join(f"<h3>{esc(qq)}</h3><p>{esc(aa)}</p>" for qq, aa in faqs)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": qq, "acceptedAnswer": {"@type": "Answer", "text": aa}} for qq, aa in faqs]}

    cps = [ppsf(r) for rs in ura.values() for r in rs if r[1] == 3 and r[6] in ("C", "E") and r[5] == 1 and r[0] > pc12]
    kpi_psf = f"{money(med(cps))} psf" if len(cps) >= 5 else "–"
    hdb_date = fmt_date(market["hdb"]["fetched"])
    ura_date = fmt_date(market["ura"]["fetched"])
    meta_title = f"{tname} HDB & Condo Prices {now_year} | Serene Lee"
    lead = (f"{tname} 4-room HDB resale median {money(m4)} in the last 12 months." if m4
            else f"{tname} HDB resale prices for the last 12 months.")
    meta_desc = f"{lead} Prices by flat type, lease and MRT, plus nearby condos and ECs. Updated weekly."
    robots = "" if INDEX else '<meta name="robots" content="noindex, follow">\n'
    head = shell_head
    head = re.sub(r"<title>.*?</title>", f"<title>{esc(meta_title)}</title>", head, flags=re.S)
    head = re.sub(r'(<meta (?:name|property)="(?:description|og:description|twitter:description)" content=")[^"]*', lambda m: m.group(1) + esc(meta_desc), head)
    head = re.sub(r'(<meta (?:property|name)="(?:og:title|twitter:title)" content=")[^"]*', lambda m: m.group(1) + esc(meta_title), head)
    head = re.sub(r'(<link rel="canonical" href=")[^"]*', r"\g<1>" + url, head)
    head = re.sub(r'(<meta property="og:url" content=")[^"]*', r"\g<1>" + url, head)
    head = head.replace('<link rel="canonical"', robots + '<link rel="canonical"', 1)
    head = head.replace("</head>", f'<script type="application/ld+json">{json.dumps(faq_ld)}</script>\n{CSS}\n</head>')

    wa = lambda t: "https://wa.me/6580868568?text=" + re.sub(r" ", "%20", esc(t))
    body = f"""
<div class="page-hero page-hero-wide container">
  <span class="eyebrow">Town guide</span>
  {picker.replace(f'value="{page}"', f'value="{page}" selected')}
  <h1 style="font-size:2.1rem;margin-top:14px">{esc(tname)} property prices: HDB, condos and MRT</h1>
  <p>What {esc(tname)} flats and condos have actually sold for, by flat type, lease and MRT station. Official HDB and URA data, updated every week.</p>
  <p class="tp-upd">HDB data retrieved {hdb_date} (latest resale month {ym(last)}) · URA data retrieved {ura_date}</p>
</div>

<section style="padding-top:12px;"><div class="container">
  <div class="tp-kpis">
    <div class="tp-tile" data-kind="hdb"><div class="k">HDB resales, last 12 months</div><div class="v">{len(r12):,}</div><div class="s">Median {money(med(all12))}</div></div>
    <div class="tp-tile" data-kind="hdb"><div class="k">4-room median</div><div class="v">{money(m4) if m4 else '–'}</div><div class="s">{len([r for r in r12 if r[1]=='4']):,} deals</div></div>
    <div class="tp-tile"><div class="k">{'MRT &amp; LRT stations' if any('LRT' in n for n in mrt_names) else 'MRT stations'}</div><div class="v">{len(mrt_names)}</div><div class="s">{esc(', '.join(mrt_names[:4]) + (f' and {len(mrt_names)-4} more' if len(mrt_names) > 4 else ''))}</div></div>
    <div class="tp-tile" data-kind="pte"><div class="k">Nearby condo &amp; EC resale</div><div class="v">{kpi_psf}</div><div class="s">Median, last 12 months</div></div>
  </div>

  <div class="tp-card" data-kind="hdb"><h2>HDB resale prices by flat type</h2>
    <div class="tp-tablewrap"><table class="tp-table"><thead><tr><th>Flat type</th><th class="r">Deals</th><th class="r">Median price</th><th class="r">Median $psf</th><th class="r">Range</th><th class="r">vs year before</th><th class="r">Median rent{(' (' + RENT_SRC[0] + ')') if RENT_SRC[0] else ''}</th></tr></thead>
    <tbody>{''.join(ft_rows)}</tbody></table></div>
    <p class="tp-src">Last 12 months: {ym(months_back(last, 11))} to {ym(last)}, compared with the 12 months before. Source: <a href="https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/view" target="_blank" rel="noopener">HDB resale flat prices (data.gov.sg)</a>. Not a valuation.{(' Median rent: whole-flat rentals approved by HDB in ' + RENT_SRC[0] + ', <a href="' + RENT_SRC[1] + '" target="_blank" rel="noopener">HDB median rents (data.gov.sg)</a>; "–" means too few rentals to publish.') if RENT_SRC[0] else ''}</p>
  </div>

  <div class="tp-card" data-kind="hdb"><h2>Price trend by quarter</h2>
    {chart}
    <p class="tp-note">{esc(trend_line)}</p>
    <p class="tp-src">Average resale price per quarter, quarters with at least 3 deals. Latest full quarter: {q[endq]}.</p>
  </div>

  <div class="tp-card" data-kind="hdb"><h2>Prices by nearest MRT station</h2>
    <div class="tp-tablewrap"><table class="tp-table"><thead><tr><th>Nearest station</th><th class="r">Blocks</th><th class="r">Within 500 m</th><th class="r">4-room median</th><th class="r">5-room median</th></tr></thead>
    <tbody>{''.join(mrt_rows)}</tbody></table></div>
    <p class="tp-note">{esc(mrt_gap)}</p>
    <p class="tp-src">Each block counts under its nearest station within 1 km ({len(far)} blocks are further than 1 km from any station). Medians cover the last 12 months, with at least 5 deals. Locations: OneMap, Singapore Land Authority; straight-line distance. Tap a station to see every block and condo near it.</p>
  </div>

  <div class="tp-two" data-kind="hdb">
    <div class="tp-card"><h2>Price by lease age</h2>
      <div class="tp-tablewrap"><table class="tp-table"><thead><tr><th>Lease started</th><th class="r">4-room</th><th class="r">5-room</th></tr></thead><tbody>{''.join(lease_rows)}</tbody></table></div>
      <p class="tp-src">Median resale price, last 12 months. HDB flats have 99-year leases. <a href="/blog-post-lease-decay-99-year-property">How lease decay affects value</a>.</p>
    </div>
    <div class="tp-card"><h2>Highest resales, last 12 months</h2>
      <div class="tp-tablewrap"><table class="tp-table"><thead><tr><th>Month</th><th>Block</th><th>Type</th><th>Floor</th><th class="r">Price</th></tr></thead><tbody>{top_rows}</tbody></table></div>
      <p class="tp-src">Tap a block to see every resale in it on the Market Map.</p>
    </div>
  </div>

  <div class="tp-card" data-kind="pte"><h2>Condos and executive condos in and around {esc(tname)}</h2>
    <div class="tp-tablewrap"><table class="tp-table"><thead><tr><th>Type</th><th class="r">Deals</th><th class="r">Median price</th><th class="r">Median $psf</th><th class="r">$psf vs year before</th></tr></thead><tbody>{''.join(pte_rows)}</tbody></table></div>
    <h3 class="tp-h3">Most traded projects</h3>
    <div class="tp-tablewrap"><table class="tp-table"><thead><tr><th>Project</th><th class="r">Deals</th><th class="r">Median $psf</th><th>Nearest MRT</th></tr></thead><tbody>{proj_rows}</tbody></table></div>
    <p class="tp-src">{len(proj_all)} private projects within {NEAR_M} m of a {esc(tname)} HDB block (OneMap locations), postal district{'s' if len(dists)>1 else ''} {', '.join(sorted(dists))}. Last 12 months of URA caveats to {ym(plast)}; single-unit deals only. Source: <a href="https://eservice.ura.gov.sg/maps/api/" target="_blank" rel="noopener">URA Data Service</a>.</p>
  </div>

  {f'''<div class="tp-card" data-kind="pte"><h2>New launches in {dlab}</h2>
    <div class="tp-tablewrap"><table class="tp-table"><thead><tr><th>Project</th><th>Status</th><th>Tenure</th><th>Completion</th><th class="r">From</th></tr></thead><tbody>{nl_rows}</tbody></table></div>
    <p class="tp-src">From the ERA new launch feed, retrieved {fmt_date(nl['retrieved'])}. <a href="/new-launches">All new launches</a> · Ask Serene about prices and availability.</p>
  </div>''' if launches else ''}

  <div class="tp-two">
    <div class="tp-card tp-persona"><h2>Upgrading from your {esc(tname)} flat?</h2>{up}
      <div class="tp-btns"><a class="btn btn-navy" href="/upgrade-checklist">Check my upgrade readiness</a>
      <a class="btn btn-gold" target="_blank" rel="noopener" href="{wa(f'Hi Serene, I live in {tname} and want to know if I can upgrade.')}">Ask Serene</a></div></div>
    <div class="tp-card tp-persona"><h2>Right-sizing after the children move out?</h2>{down}
      {f'<p><a href="/right-sizing-north?town={page}"><b>Read the right-sizing guide for {esc(tname)}</b></a>: selling, renting out rooms and the Lease Buyback Scheme, with a quick estimate.</p>' if page in ("woodlands", "sembawang", "yishun") else ''}
      <div class="tp-btns"><a class="btn btn-navy" href="/market-map?town={page}">Check my block's prices</a>
      <a class="btn btn-gold" target="_blank" rel="noopener" href="{wa(f'Hi Serene, I am thinking of right-sizing from my {tname} flat. Could we talk?')}">Ask Serene</a></div></div>
  </div>

  <div class="tp-card tp-faq"><h2>{esc(tname)} property: common questions</h2>{faq_html}</div>
</div></section>

<section class="cta-banner"><div class="container cta-banner">
  <h2>What could your {esc(tname)} flat sell for?</h2>
  <div class="btns">
    <a href="/market-map" class="btn btn-navy">Check My Block's Prices</a>
    <a href="{wa(f'Hi Serene, I saw your {tname} page and would like a valuation of my flat.')}" target="_blank" rel="noopener" class="btn" style="background:#fff;color:var(--navy-900);">Get a Free Valuation</a>
  </div>
</div></section>
"""
    out = head + shell_header + body + shell_footer
    with open(os.path.join(ROOT, f"{page}.html"), "w") as fh:
        fh.write(out)
    return {"town": tname, "slug": page, "region": th["region"], "m4": m4, "n12": len(r12),
            "med": med(all12), "mrt": len(mrt_names), "psf": kpi_psf}


CSS = """<style>
.tp-upd{font-size:.82rem;color:var(--muted)}
.tp-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:0 0 20px}
@media(max-width:760px){.tp-kpis{grid-template-columns:1fr 1fr}}
.tp-tile{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 14px;min-width:0}
.tp-tile .k{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.tp-tile .v{font:600 1.35rem/1.25 'Fraunces',Georgia,serif;color:var(--navy-900);margin:4px 0 2px;font-variant-numeric:tabular-nums}
.tp-tile .s{font-size:.8rem;color:var(--muted)}
.tp-card{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:18px;margin-bottom:20px;min-width:0}
.tp-card h2{font-size:1.15rem;margin:0 0 10px}
.tp-h3{font-size:1rem;margin:16px 0 8px}
.tp-two{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;margin-bottom:20px}
.tp-two .tp-card{margin-bottom:0}
@media(max-width:860px){.tp-two{grid-template-columns:1fr}}
.tp-tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
.tp-table{width:100%;border-collapse:collapse;font-size:.86rem}
.tp-table th{text-align:left;font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:var(--cream);padding:9px 12px;white-space:nowrap}
.tp-table td{padding:9px 12px;border-top:1px solid var(--line);vertical-align:top;font-variant-numeric:tabular-nums}
.tp-table .r{text-align:right;white-space:nowrap}
.tp-table a{color:var(--navy-900)}
.tp-mut{color:var(--muted);font-size:.78rem}
.tp-chg{font-weight:600}.tp-chg.up{color:#1f7a4a}.tp-chg.down{color:#b3412e}
.tp-src{font-size:.75rem;color:var(--muted);margin:10px 0 0;line-height:1.45}
.tp-src a{color:inherit}
.tp-note{font-size:.92rem;margin:12px 0 0;max-width:820px}
.tp-chart{width:100%;height:auto;display:block}
.tp-chart text{font:500 11px 'Inter',sans-serif;fill:var(--muted)}
.tp-chart .grid{stroke:var(--line);stroke-width:1}
.tp-key{display:flex;flex-wrap:wrap;gap:14px;font-size:.8rem;color:var(--muted);margin-top:6px}
.tp-key i{display:inline-block;width:14px;height:4px;border-radius:2px;margin-right:6px;vertical-align:middle}
.tp-persona p{font-size:.92rem;color:var(--ink,inherit)}
.tp-btns{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}
.tp-pick{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;margin:14px 0 4px}
[data-kind][hidden]{display:none!important}
.tp-est{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px}
.tp-kind{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.tp-lab{font-weight:700;font-size:.9rem;color:var(--navy-900);margin-right:2px}
.tp-pick{gap:12px 24px}
.tp-pick label{font-weight:700;font-size:.9rem;color:var(--navy-900)}
.tp-pick select{min-width:240px;max-width:100%;font-size:1rem;padding:10px 12px}
.tp-region{font-size:1.15rem;margin:22px 0 10px}
.tp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.tp-town{display:flex;flex-direction:column;gap:3px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px 16px;text-decoration:none;color:var(--muted);font-size:.84rem}
.tp-town b{font:600 1.1rem 'Fraunces',Georgia,serif;color:var(--navy-900);margin-bottom:4px}
.tp-town strong{color:var(--navy-900)}
.tp-town:hover{border-color:var(--gold);box-shadow:var(--shadow)}
.tp-faq h3{font-size:1rem;margin:16px 0 4px}
.tp-faq p{color:var(--muted);font-size:.92rem;margin:0;max-width:820px}
</style>"""


def picker_html(market, with_kind=True):
    groups = {}
    for t, v in market["hdb"]["towns"].items():
        groups.setdefault(v["region"] or "Other", []).append((title(t), v["file"]))
    opts = "".join(
        f'<optgroup label="{esc(r)}">' + "".join(f'<option value="{f}">{esc(n)}</option>' for n, f in sorted(groups[r])) + "</optgroup>"
        for r in REGION_ORDER + sorted(set(groups) - set(REGION_ORDER)) if r in groups)
    kind = ('<div class="tp-kind" role="group" aria-label="Property type"><span class="tp-lab">Show</span>'
            '<button type="button" class="filter-chip active" data-k="all">HDB &amp; private</button>'
            '<button type="button" class="filter-chip" data-k="hdb">HDB only</button>'
            '<button type="button" class="filter-chip" data-k="pte">Private only</button></div>') if with_kind else ""
    return ('<div class="tp-pick"><div class="tp-est"><label for="tpTown">Choose an estate</label>'
            '<select id="tpTown" class="sort-select" onchange="tpGo(this.value)">'
            '<option value="">Select an HDB town…</option>' + opts + "</select></div>" + kind + "</div>" + KIND_JS)


KIND_JS = """<script>
(function(){
  var q=new URLSearchParams(location.search).get("type"), k=q==="hdb"?"hdb":q==="private"?"pte":"all";
  function set(v,save){k=v;
    document.querySelectorAll("[data-kind]").forEach(function(e){e.hidden=v!=="all"&&e.getAttribute("data-kind")!==v;});
    document.querySelectorAll(".tp-kind [data-k]").forEach(function(b){b.classList.toggle("active",b.getAttribute("data-k")===v);});
    if(save){try{var u=new URL(location.href);if(v==="all")u.searchParams.delete("type");else u.searchParams.set("type",v==="pte"?"private":"hdb");history.replaceState(null,"",u.pathname+u.search+u.hash);}catch(e){}}}
  window.tpGo=function(t){if(!t)return;try{posthog.capture("town_guide_switch",{to:t,type:k});}catch(e){}
    location.href="/"+t+(k==="all"?"":"?type="+(k==="pte"?"private":"hdb"));};
  document.addEventListener("click",function(e){var b=e.target.closest(".tp-kind [data-k]");if(!b)return;set(b.getAttribute("data-k"),true);
    try{posthog.capture("town_guide_type",{type:b.getAttribute("data-k")});}catch(x){}});
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",function(){set(k,false);});else set(k,false);
})();
</script>"""


def build_hub(stats, market, head, header, footer, picker):
    by = {}
    for x in stats:
        by.setdefault(x["region"], []).append(x)
    cards = ""
    for r in REGION_ORDER:
        if r not in by:
            continue
        cards += f'<h2 class="tp-region">{esc(r)}</h2><div class="tp-grid">' + "".join(
            f'<a class="tp-town" href="/{x["slug"]}"><b>{esc(x["town"])}</b>'
            f'<span>4-room median <strong>{money(x["m4"]) if x["m4"] else "–"}</strong></span>'
            f'<span>{x["n12"]:,} HDB resales · {x["mrt"]} MRT/LRT station{"s" if x["mrt"] != 1 else ""}</span>'
            f'<span>Condo &amp; EC resale {x["psf"]}</span></a>' for x in sorted(by[r], key=lambda x: x["town"])) + "</div>"
    last = market["hdb"]["last_month"]
    t = "HDB Town Guides: Prices by Estate | Serene Lee"
    dsc = "Resale prices for all 26 HDB towns by flat type, lease and MRT station, plus nearby condos, ECs and new launches. Official HDB and URA data, weekly."
    h = re.sub(r"<title>.*?</title>", f"<title>{esc(t)}</title>", head, flags=re.S)
    h = re.sub(r'(<meta (?:name|property)="(?:description|og:description|twitter:description)" content=")[^"]*', lambda m: m.group(1) + esc(dsc), h)
    h = re.sub(r'(<meta (?:property|name)="(?:og:title|twitter:title)" content=")[^"]*', lambda m: m.group(1) + esc(t), h)
    h = re.sub(r'(<link rel="canonical" href=")[^"]*', r"\g<1>" + SITE + "/town-guide", h)
    h = re.sub(r'(<meta property="og:url" content=")[^"]*', r"\g<1>" + SITE + "/town-guide", h)
    if not INDEX:
        h = h.replace('<link rel="canonical"', '<meta name="robots" content="noindex, follow">\n<link rel="canonical"', 1)
    h = h.replace("</head>", CSS + "\n</head>")
    body = f"""
<div class="page-hero page-hero-wide container">
  <span class="eyebrow">Town guides</span>
  <h1 style="font-size:2.1rem;">HDB town guides: prices by estate</h1>
  <p>Pick an estate to see what flats and condos there have actually sold for, by flat type, lease and MRT station. Official HDB and URA data, updated every week.</p>
  {picker}
  <p class="tp-upd">Last 12 months of HDB resales to {ym(last)}.</p>
</div>
<section style="padding-top:12px;"><div class="container">{cards}</div></section>
"""
    with open(os.path.join(ROOT, "town-guide.html"), "w") as fh:
        fh.write(h + header + body + footer)


HOME_TOWNS = ["woodlands", "sembawang", "yishun"]  # Serene's focus estates, shown on the homepage


def update_home(stats, market):
    """Refresh the town-guide strip on index.html between <!-- TOWNS:START --> and <!-- TOWNS:END -->."""
    path = os.path.join(ROOT, "index.html")
    h = open(path, encoding="utf-8").read()
    if "<!-- TOWNS:START -->" not in h:
        return
    by = {x["slug"]: x for x in stats}
    cards = "".join(
        f'<a class="tp-town" href="/{s}" data-hm="town-{s}"><b>{esc(by[s]["town"])}</b>'
        f'<span>4-room median <strong>{money(by[s]["m4"]) if by[s]["m4"] else "–"}</strong></span>'
        f'<span>{by[s]["n12"]:,} HDB resales in 12 months</span>'
        f'<span>Condo &amp; EC resale {by[s]["psf"]}</span>'
        f'<span class="tp-go">Open the {esc(by[s]["town"])} guide &rarr;</span></a>'
        for s in HOME_TOWNS if s in by)
    block = (f'<!-- TOWNS:START -->\n<div class="tp-grid home-towns">{cards}</div>\n'
             f'<p class="tp-upd" style="margin-top:10px">Official HDB and URA data to {ym(market["hdb"]["last_month"])}, updated weekly. '
             f'<a href="/town-guide">See all 26 HDB town guides</a> · Children moved out? <a href="/right-sizing-north">Read the right-sizing guide</a>.</p>\n<!-- TOWNS:END -->')
    h = re.sub(r"<!-- TOWNS:START -->.*?<!-- TOWNS:END -->", lambda m: block, h, flags=re.S)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(h)


def main():
    tpl = open(os.path.join(ROOT, "million-dollar-hdb.html")).read()
    head = tpl[:tpl.index("<body>")]
    header = tpl[tpl.index("<body>"):tpl.index("</header>") + len("</header>")] + "\n"
    footer = "\n" + tpl[tpl.index("<!-- FOOTER -->"):]
    # The shell comes from the million-dollar page: drop its own menu highlight and its
    # page-specific schema (add_schema.py adds the right ones for each generated page).
    header = header.replace(' class="active"', "")
    head = re.sub(r'\n?<script type="application/ld\+json" data-schema="(?:breadcrumb|dataset)">.*?</script>', "", head, flags=re.S)
    market = load("market-data.json")
    picker = picker_html(market)
    stats = []
    for town, v in market["hdb"]["towns"].items():
        if not os.path.exists(os.path.join(D, "hdb", v["file"] + ".json")):
            continue
        try:
            stats.append(build(town, {"slug": v["file"]}, head, header, footer, picker))
        except Exception as e:  # one bad town must not stop the others
            print(f"skipped {town}: {e}")
    build_hub(stats, market, head, header, footer, picker_html(market, with_kind=False))
    update_home(stats, market)
    build_rightsizing(market, head, header, footer)
    import build_useful_numbers  # same shell, so menu/footer changes reach it too
    build_useful_numbers.main()
    print(f"built {len(stats)} town pages + town-guide.html (index={INDEX})")


RS_TOWNS = ["WOODLANDS", "SEMBAWANG", "YISHUN"]


def load_rents():
    """HDB median monthly rents (whole flat) from data/rents.json, refreshed weekly by
    scripts/update_rents.py; HDB publishes a new quarter about 4 weeks after it ends."""
    try:
        r = load("rents.json")
        return r["towns"], r.get("prev_year", {}), (r["label"], r["url"])
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return {}, {}, ("", "")


RENTS, RENTS_PREV, RENT_SRC = load_rents()
SMALL_SQM = 70  # "smaller condo": units up to 70 sqm (about 750 sqft)


def build_rightsizing(market, head, header, footer):
    from rightsizing_page import render  # page text and layout live in their own file
    last = market["hdb"]["last_month"]
    c12 = months_back(last, 12)
    data = {}
    for town in RS_TOWNS:
        info = market["hdb"]["towns"][town]
        f = load(f"hdb/{info['file']}.json")
        geo = load(f"geo/hdb/{info['file']}.json")
        rows = [r for st in f["streets"].values() for rs in st.values() for r in rs if r[0] > c12]
        sale = {}
        for ft in ["2", "3", "4", "5", "E"]:
            a = [r[6] for r in rows if r[1] == ft]
            if len(a) >= 5:
                sale[ft] = [len(a), round(med(a), -3)]
        near = nearby_projects(geo)
        small = []
        plast = ""
        for (dd, key) in near:
            for r in load(f"ura/d{dd}.json").get(key, []):
                plast = max(plast, r[0])
        pc12 = months_back(plast or last, 12)
        for (dd, key) in near:
            if key.upper().startswith("LANDED HOUSING"):
                continue
            for r in load(f"ura/d{dd}.json").get(key, []):
                if r[1] == 3 and r[5] == 1 and r[6] in ("C", "E") and r[2] <= SMALL_SQM and r[0] > pc12:
                    small.append(r[4])
        nxt = {k: sale[k] for k in ("3", "2") if k in sale}
        if len(small) >= 5:
            nxt["condo"] = [len(small), round(med(small), -3)]
        data[info["file"]] = {"name": title(town), "sale": sale, "next": nxt, "rent": RENTS.get(town, {})}
    meta = {"hdb_month": ym(last), "hdb_from": ym(months_back(last, 11)), "hdb_date": fmt_date(market["hdb"]["fetched"]),
            "ura_date": fmt_date(market["ura"]["fetched"]), "rent_q": RENT_SRC[0], "rent_url": RENT_SRC[1], "small_sqm": SMALL_SQM}
    page = render(data, meta, head, header, footer, esc, money)
    with open(os.path.join(ROOT, "right-sizing-north.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    print("built right-sizing-north.html")


if __name__ == "__main__":
    main()
