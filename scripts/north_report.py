#!/usr/bin/env python3
"""Monthly Singapore HDB resale report for Serene's email list (islandwide + one "town in focus").

Usage:  python3 scripts/north_report.py [YYYY-MM]      (default: last full calendar month, SGT)

(File name kept from the first version, which covered only Woodlands/Sembawang/Yishun; the
workflow and the monthly scheduled task point at these paths.)

Writes:
  data/north-report/<YYYY-MM>.json          figures used in the email (for checking)
  assets/email/north-report-<YYYY-MM>.jpg   summary card image (1200px wide) shown in the email
  assets/email/north-report-<YYYY-MM>.html  paste-ready email: Serene copies it into a Kit broadcast

Data: data/hdb/<town>.json (HDB resale flat prices, data.gov.sg, refreshed weekly).
Deal rows: [month, flat_type, storey_from, sqm, model_idx, lease_start, price].
Town in focus rotates through Woodlands, Sembawang and Yishun (Serene's farm area), one per month.
"""
import glob, html, json, os, statistics as st, sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOCUS = ["woodlands", "sembawang", "yishun"]
FT = {"2": "2-room", "3": "3-room", "4": "4-room", "5": "5-room", "E": "Executive", "M": "Multi-gen"}
TYPES = ["3", "4", "5", "E"]
SITE = "https://sereneleeproperty.com"
SGT = timezone(timedelta(hours=8))
# Required verbatim by ERA AI Usage Governance Policy v1.0 for AI-assisted analytical reports.
AI_DISCLAIMER = ("This document contains AI-assisted analysis provided for general informational purposes only. "
                 "It does not constitute formal legal, financial, or certified property valuation advice. "
                 "Recipients shall not rely on this information unless they have independently verified this "
                 "information to their satisfaction.")


def last_full_month():
    first = datetime.now(SGT).replace(day=1)
    return (first - timedelta(days=1)).strftime("%Y-%m")


def month_label(m):
    return datetime.strptime(m + "-01", "%Y-%m-%d").strftime("%B %Y")


def k(v):
    return f"${v/1000:,.0f}k"


def pct(a, b):
    return None if not a or not b else (a - b) / b * 100


def updown(c, dp=0):
    return f"{'up' if c >= 0 else 'down'} {abs(c):.{dp}f}%"


def load_rows():
    """All deals islandwide: (town_slug, town_name, street, block, month, ft, storey, sqm, model, lease, price)."""
    rows, latest = [], {}
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "hdb", "*.json"))):
        slug = os.path.basename(f)[:-5]
        if slug in ("index", "million", "million-summary"):
            continue
        d = json.load(open(f))
        if "streets" not in d:
            continue
        name = d["town"].title()
        for s, bl in d["streets"].items():
            for b, rs in bl.items():
                for r in rs:
                    rows.append((slug, name, s, b, *r))
        latest[slug] = max(r[4] for r in rows if r[0] == slug)
    return rows, latest


def ft_stats(cur, prev):
    out = {}
    for f in TYPES:
        a = [r[10] for r in cur if r[5] == f]
        b = [r[10] for r in prev if r[5] == f]
        out[f] = {"n": len(a), "median": st.median(a) if a else None, "n_ly": len(b), "median_ly": st.median(b) if b else None}
    return out


def deal_desc(r):
    t = {"E": "Executive flat", "M": "multi-generation flat"}.get(r[5], FT.get(r[5], r[5]) + " flat")
    return f"a {t} at Blk {r[3]} {r[2].title()}, {r[1]} (floor {r[6]}-{r[6]+2}, {r[7]:.0f} sqm) for ${r[10]:,.0f}"


def build(m):
    y, mo = map(int, m.split("-"))
    ly = f"{y-1}-{mo:02d}"
    rows, latest = load_rows()
    data_to = min(latest.values())
    if data_to < m:
        sys.exit(f"HDB data only runs to {data_to}; {m} is not in yet. Wait for the weekly refresh.")
    cur = [r for r in rows if r[4] == m]
    prev = [r for r in rows if r[4] == ly]

    # Islandwide
    nat = {"sold": len(cur), "sold_ly": len(prev), "ft": ft_stats(cur, prev),
           "million": sum(1 for r in cur if r[10] >= 1_000_000), "million_ly": sum(1 for r in prev if r[10] >= 1_000_000)}
    top = max(cur, key=lambda r: r[10])

    # Top 5 towns by flats sold
    towns = {}
    for r in cur:
        towns.setdefault((r[0], r[1]), []).append(r)
    top5 = []
    for (slug, name), rs in sorted(towns.items(), key=lambda kv: -len(kv[1]))[:5]:
        f4 = [r[10] for r in rs if r[5] == "4"]
        top5.append({"slug": slug, "town": name, "sold": len(rs), "median4": st.median(f4) if f4 else None, "n4": len(f4)})

    # Town in focus (rotates monthly)
    fslug = FOCUS[(y * 12 + mo) % len(FOCUS)]
    fc = [r for r in cur if r[0] == fslug]
    fp = [r for r in prev if r[0] == fslug]
    focus = {"slug": fslug, "town": fc[0][1] if fc else fslug.title(), "sold": len(fc), "sold_ly": len(fp), "ft": ft_stats(fc, fp)}

    # Highlights (3)
    hl = []
    c = pct(nat["sold"], nat["sold_ly"])
    hl.append(f"{nat['sold']:,} HDB flats were resold across Singapore in {month_label(m)}"
              + (f", {updown(c)} on {month_label(ly)}" if c is not None else "")
              + f". The busiest towns were {top5[0]['town']} ({top5[0]['sold']}), {top5[1]['town']} ({top5[1]['sold']}) and {top5[2]['town']} ({top5[2]['sold']}).")
    hl.append(f"{nat['million']} flats sold for $1 million or more (vs {nat['million_ly']} a year earlier). "
              f"Top sale: {deal_desc(top)}.")
    f4 = focus["ft"]["4"]
    fch = pct(f4["median"], f4["median_ly"])
    line = f"Town in focus, {focus['town']}: {focus['sold']} resales"
    if f4["median"]:
        line += f"; 4-room median {k(f4['median'])}"
        if fch is not None and f4["n"] >= 10 and f4["n_ly"] >= 10:
            line += f", {updown(fch, 1)} on a year ago ({f4['n']} deals vs {f4['n_ly']})"
    hl.append(line + ". Medians mix flats of different ages, so check your own block.")

    camp = f"hdb-{m}"
    utm = f"utm_source=email&utm_medium=newsletter&utm_campaign={camp}"
    img_rel = f"assets/email/north-report-{m}.jpg"
    out = {"month": m, "label": month_label(m), "compare": ly, "data_to": data_to, "complete": data_to > m,
           "national": nat, "top_sale": {"desc": deal_desc(top), "price": top[10]}, "top5": top5, "focus": focus,
           "highlights": hl, "image": f"{SITE}/{img_rel}", "utm": utm,
           "subject": f"Singapore Property Updates, {month_label(m)}: {nat['sold']:,} HDB resales, {nat['million']} at $1M+",
           "preview_text": f"Singapore's busiest towns, million-dollar flats and a closer look at {focus['town']}."}
    os.makedirs(os.path.join(ROOT, "data", "north-report"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "data", "north-report", m + ".json"), "w"), indent=1)
    render_card(out, os.path.join(ROOT, img_rel))
    open(os.path.join(ROOT, "assets", "email", f"north-report-{m}.html"), "w").write(email_html(out))
    old = os.path.join(ROOT, "data", "north-report", m + "-kit.json")
    if os.path.exists(old):
        os.remove(old)
    return out


def chg(x):
    c = pct(x["median"], x["median_ly"])
    if c is None or x["n"] < 5 or x["n_ly"] < 5:
        return ""
    if abs(c) < 0.5:
        return '<span class="n">&ndash;</span>'
    return f'<span class="{"up" if c >= 0 else "dn"}">{"▲" if c >= 0 else "▼"} {abs(c):.0f}%</span>'


def ft_table(fts):
    rows = "".join(f'<tr><td>{FT[f]}</td><td class="r"><b>{k(x["median"])}</b> {chg(x)}</td><td class="r n">{x["n"]:,}</td></tr>'
                   for f, x in fts.items() if x["median"])
    return f'<table><tr><th>Flat type</th><th class="r">Median</th><th class="r">Deals</th></tr>{rows}</table>'


def sub(a, b):
    c = pct(a, b)
    return "" if c is None else ("▲ " if c >= 0 else "▼ ") + f"{abs(c):.0f}% vs a year ago"


def render_card(o, path):
    n, f = o["national"], o["focus"]
    t5 = "".join(f'<tr><td>{i}. {html.escape(t["town"])}</td><td class="r"><b>{t["sold"]}</b></td><td class="r n">{k(t["median4"]) if t["median4"] else "–"}</td></tr>'
                 for i, t in enumerate(o["top5"], 1))
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1200px;font-family:Inter,'DejaVu Sans',sans-serif;background:#f5f4f0;color:#0b2a4a;padding:44px}}
.top{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:26px}}
.eb{{font-size:18px;font-weight:700;letter-spacing:.12em;color:#c9a227;text-transform:uppercase}}
h1{{font-family:Fraunces,Georgia,'DejaVu Serif',serif;font-size:46px;margin-top:6px}}
.brand{{text-align:right;font-size:17px;color:#55657a}} .brand b{{color:#0b2a4a;font-size:20px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}
.col{{background:#fff;border-radius:18px;padding:24px;border-top:6px solid #c9a227}}
.col.focus{{border-top-color:#0b2a4a}}
.lbl{{font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#c9a227}}
h2{{font-family:Fraunces,Georgia,'DejaVu Serif',serif;font-size:28px;margin-top:2px}}
.big{{font-size:46px;font-weight:800;margin-top:8px}} .big small{{font-size:17px;font-weight:600;color:#55657a}}
.sub{{font-size:16px;color:#55657a;margin:2px 0 12px;min-height:21px}}
.pill{{display:inline-block;background:#fff8e1;border:1px solid #c9a227;border-radius:999px;padding:4px 12px;font-size:15px;font-weight:700;margin-bottom:12px}}
table{{width:100%;border-collapse:collapse;font-size:18px}}
th{{text-align:left;font-size:13px;color:#55657a;text-transform:uppercase;letter-spacing:.04em;padding:6px 0;border-bottom:2px solid #eee}}
td{{padding:8px 0;border-bottom:1px solid #f0eee8}}
.r{{text-align:right}} .n{{color:#55657a}}
.up{{color:#1d7a46;font-size:14px;font-weight:700}} .dn{{color:#b42318;font-size:14px;font-weight:700}}
.foot{{margin-top:22px;font-size:15px;color:#55657a;display:flex;justify-content:space-between;gap:20px}}
</style></head><body>
<div class="top"><div><div class="eb">Singapore Property Updates</div><h1>{o['label']}</h1></div>
<div class="brand"><b>Serene Lee</b><br>ERA Realty · CEA R027578Z<br>sereneleeproperty.com</div></div>
<div class="grid">
<div class="col"><div class="lbl">Islandwide</div><h2>Singapore</h2>
<div class="big">{n['sold']:,}<small> flats sold</small></div><div class="sub">{sub(n['sold'], n['sold_ly'])}</div>
<div class="pill">{n['million']} sold for $1M+</div>{ft_table(n['ft'])}</div>
<div class="col"><div class="lbl">Most resales</div><h2>Top 5 towns</h2>
<table style="margin-top:14px"><tr><th>Town</th><th class="r">Sold</th><th class="r">4-rm median</th></tr>{t5}</table></div>
<div class="col focus"><div class="lbl">Town in focus</div><h2>{html.escape(f['town'])}</h2>
<div class="big">{f['sold']}<small> flats sold</small></div><div class="sub">{sub(f['sold'], f['sold_ly'])}</div>{ft_table(f['ft'])}</div>
</div>
<div class="foot"><span>Median resale prices; ▲▼ = change vs {month_label(o['compare'])} (shown when both months have 5+ deals).</span><span>Source: HDB resale flat prices, data.gov.sg</span></div>
</body></html>"""
    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.dirname(path), exist_ok=True)
    exe = "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 300}, device_scale_factor=1)
        pg.set_content(doc)
        pg.wait_for_timeout(300)
        pg.screenshot(path=path, full_page=True, type="jpeg", quality=88)
        b.close()


def email_html(o):
    """Paste-ready email: Serene opens it in a browser, selects everything below the line, copies, pastes into Kit."""
    u, e, f = o["utm"], html.escape, o["focus"]
    lis = "".join(f"<li>{e(h)}</li>" for h in o["highlights"])
    a = lambda href, t: f'<a href="{href}" style="color:#0b2a4a">{t}</a>'
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="robots" content="noindex">
<title>Email: Singapore Property Updates {e(o['label'])}</title></head>
<body style="max-width:640px;margin:24px auto;padding:0 16px;font-family:Arial,Helvetica,sans-serif;color:#1f2937;line-height:1.55">
<div style="background:#fff8e1;border:1px solid #c9a227;border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:22px">
<b>For Serene (don't copy this box):</b> Subject: <b>{e(o['subject'])}</b><br>Preview text: {e(o['preview_text'])}<br>
Copy everything below the line into a new Kit broadcast. Send to: subscribers of your Singapore Property Updates form. Check the figures before sending.</div>
<hr>
<h1 style="font-size:24px;color:#0b2a4a">Singapore Property Updates: {e(o['label'])}</h1>
<p>Hi there,</p>
<p>Here's what happened in Singapore's HDB resale market in {e(o['label'])}, straight from HDB's official data, plus a closer look at {e(f['town'])}.</p>
<p><a href="{SITE}/market-map?{u}"><img src="{o['image']}" alt="Singapore HDB resale report {e(o['label'])}: flats sold, median prices, top 5 towns and {e(f['town'])}" style="width:100%;max-width:600px;border-radius:8px"></a></p>
<h2 style="font-size:19px;color:#0b2a4a">3 things to know</h2><ul>{lis}</ul>
<h2 style="font-size:19px;color:#0b2a4a">What's your flat worth?</h2>
<p>Town medians mix flats of different ages and sizes. For your own block, and what you could move to next, get a free personal plan from me.</p>
<p><a href="{SITE}/flat-report?{u}" style="display:inline-block;background:#c9a227;color:#0b2a4a;font-weight:bold;padding:12px 22px;border-radius:6px;text-decoration:none">Get My Free Flat Report</a></p>
<p>More: {a(f"{SITE}/{f['slug']}?{u}", e(f['town']) + " town guide")} · {a(f"{SITE}/town-guide?{u}", "All town guides")} · {a(f"{SITE}/million-dollar-hdb?{u}", "$1M HDB tracker")} · {a(f"{SITE}/new-launches?{u}", "New launches")}</p>
<p>Questions? Just reply to this email or {a("https://wa.me/6580868568?text=Hi%20Serene%2C%20I%20read%20your%20property%20report.","WhatsApp me")}.</p>
<p>Serene Lee</p>
<hr style="border:none;border-top:1px solid #e6e2d8">
<p style="font-size:12px;color:#6b7280">Serene Lee · ERA Realty Network Pte Ltd (L3002382K) · CEA Reg. R027578Z · +65 8086 8568. Figures are past HDB resale transactions (data.gov.sg), registered in the month shown; they are not a valuation.</p>
<p style="font-size:12px;color:#6b7280;font-style:italic">{e(AI_DISCLAIMER)}</p>
</body></html>"""


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else last_full_month()
    o = build(month)
    print(json.dumps({"month": o["label"], "complete": o["complete"], "subject": o["subject"],
                      "focus": o["focus"]["town"], "highlights": o["highlights"], "image": o["image"]}, indent=1))
