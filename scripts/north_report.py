#!/usr/bin/env python3
"""Monthly North HDB resale report (Woodlands, Sembawang, Yishun) for Serene's email list.

Usage:  python3 scripts/north_report.py [YYYY-MM]      (default: last full calendar month, SGT)

Writes:
  data/north-report/<YYYY-MM>.json          figures used in the email (for checking)
  assets/email/north-report-<YYYY-MM>.jpg   summary card image (1200px wide) shown in the email
  data/north-report/<YYYY-MM>-kit.json      Kit content_tree (Classic template) + subject + preview text

Data: data/hdb/<town>.json (HDB resale flat prices, data.gov.sg, refreshed weekly).
Deal rows: [month, flat_type, storey_from, sqm, model_idx, lease_start, price].
The email is drafted in Kit (tag north-hdb-report) and Serene reviews and sends it herself.
"""
import json, os, sys, statistics as st, html
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOWNS = ["woodlands", "sembawang", "yishun"]
FT = {"2": "2-room", "3": "3-room", "4": "4-room", "5": "5-room", "E": "Executive", "M": "Multi-gen"}
SITE = "https://sereneleeproperty.com"
SGT = timezone(timedelta(hours=8))


def last_full_month():
    now = datetime.now(SGT)
    first = now.replace(day=1)
    prev = first - timedelta(days=1)
    return prev.strftime("%Y-%m")


def month_label(m):
    return datetime.strptime(m + "-01", "%Y-%m-%d").strftime("%B %Y")


def k(v):
    return f"${v/1000:,.0f}k"


def pct(a, b):
    return None if not a or not b else (a - b) / b * 100


def town_stats(t, m, ly):
    d = json.load(open(os.path.join(ROOT, "data", "hdb", t + ".json")))
    rows = [(s, b, *r) for s, bl in d["streets"].items() for b, rs in bl.items() for r in rs]
    latest = max(r[2] for r in rows)
    cur = [r for r in rows if r[2] == m]
    prev = [r for r in rows if r[2] == ly]
    out = {"town": d["town"].title(), "slug": t, "sold": len(cur), "sold_ly": len(prev), "ft": {}, "data_to": latest}
    for f in ["3", "4", "5", "E"]:
        a = [r[8] for r in cur if r[3] == f]
        b = [r[8] for r in prev if r[3] == f]
        out["ft"][f] = {"n": len(a), "median": st.median(a) if a else None,
                        "n_ly": len(b), "median_ly": st.median(b) if b else None}
    top = max(cur, key=lambda r: r[8]) if cur else None
    if top:
        out["top"] = {"block": top[1], "street": top[0].title(), "type": {"E": "Executive flat", "M": "multi-generation flat"}.get(top[3], FT.get(top[3], top[3]) + " flat"),
                      "storey": f"{top[4]}-{top[4]+2}", "sqm": top[5], "price": top[8]}
    return out


def build(m):
    y, mo = map(int, m.split("-"))
    ly = f"{y-1}-{mo:02d}"
    towns = [town_stats(t, m, ly) for t in TOWNS]
    data_to = min(t["data_to"] for t in towns)
    if data_to < m:
        sys.exit(f"HDB data only runs to {data_to}; {m} is not in yet. Wait for the weekly refresh.")
    complete = data_to > m  # a later month exists, so this month's registrations are (nearly) complete

    total = sum(t["sold"] for t in towns)
    total_ly = sum(t["sold_ly"] for t in towns)
    hl = []
    busiest = max(towns, key=lambda t: t["sold"])
    ch = pct(total, total_ly)
    hl.append(f"{total} HDB flats resold across the three towns in {month_label(m)}"
              + (f" ({'up' if ch >= 0 else 'down'} {abs(ch):.0f}% on {month_label(ly)})" if ch is not None else "")
              + f". {busiest['town']} was busiest with {busiest['sold']}.")
    moves = []
    for t in towns:
        f4 = t["ft"]["4"]
        c = pct(f4["median"], f4["median_ly"])
        if c is not None and f4["n"] >= 10 and f4["n_ly"] >= 10:
            moves.append((abs(c), c, t, f4))
    if moves:
        _, c, t, f4 = max(moves, key=lambda x: x[0])
        hl.append(f"Biggest 4-room move: {t['town']} median {k(f4['median'])}, "
                  f"{'up' if c >= 0 else 'down'} {abs(c):.1f}% on a year ago ({f4['n']} deals vs {f4['n_ly']}). "
                  "Medians mix flats of different ages, so check your own block.")
    tops = [t for t in towns if t.get("top")]
    if tops:
        tt = max(tops, key=lambda t: t["top"]["price"])
        tp = tt["top"]
        hl.append(f"Top sale: a {tp['type']} at Blk {tp['block']} {tp['street']}, {tt['town']} "
                  f"(floor {tp['storey']}, {tp['sqm']:.0f} sqm) for ${tp['price']:,.0f}.")

    camp = f"north-{m}"
    utm = f"utm_source=email&utm_medium=newsletter&utm_campaign={camp}"
    img_rel = f"assets/email/north-report-{m}.jpg"
    out = {"month": m, "label": month_label(m), "compare": ly, "data_to": data_to, "complete": complete,
           "total": total, "total_ly": total_ly, "towns": towns, "highlights": hl,
           "image": f"{SITE}/{img_rel}", "utm": utm}
    os.makedirs(os.path.join(ROOT, "data", "north-report"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "data", "north-report", m + ".json"), "w"), indent=1)
    render_card(out, os.path.join(ROOT, img_rel))
    kit = kit_tree(out)
    json.dump(kit, open(os.path.join(ROOT, "data", "north-report", m + "-kit.json"), "w"), indent=1, ensure_ascii=False)
    return out, kit


def render_card(o, path):
    cols = ""
    for t in o["towns"]:
        ch = pct(t["sold"], t["sold_ly"])
        rows = ""
        for f in ["3", "4", "5", "E"]:
            x = t["ft"][f]
            if not x["median"]:
                continue
            c = pct(x["median"], x["median_ly"])
            cs = "" if c is None or x["n_ly"] < 5 or x["n"] < 5 else ('<span class="n">&ndash;</span>' if abs(c) < 0.5 else f'<span class="{"up" if c >= 0 else "dn"}">{"▲" if c >= 0 else "▼"} {abs(c):.0f}%</span>')
            rows += f'<tr><td>{FT[f]}</td><td class="r"><b>{k(x["median"])}</b> {cs}</td><td class="r n">{x["n"]}</td></tr>'
        cols += f"""<div class="col"><h2>{html.escape(t['town'])}</h2>
<div class="big">{t['sold']}<small> flats sold</small></div>
<div class="sub">{('' if ch is None else (('▲ ' if ch>=0 else '▼ ') + f'{abs(ch):.0f}% vs a year ago'))}</div>
<table><tr><th>Flat type</th><th class="r">Median</th><th class="r">Deals</th></tr>{rows}</table></div>"""
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1200px;font-family:Inter,'DejaVu Sans',sans-serif;background:#f5f4f0;color:#0b2a4a;padding:44px}}
.top{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:26px}}
.eb{{font-size:18px;font-weight:700;letter-spacing:.12em;color:#c9a227;text-transform:uppercase}}
h1{{font-family:Fraunces,Georgia,'DejaVu Serif',serif;font-size:46px;margin-top:6px}}
.brand{{text-align:right;font-size:17px;color:#55657a}}
.brand b{{color:#0b2a4a;font-size:20px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}
.col{{background:#fff;border-radius:18px;padding:24px;border-top:6px solid #c9a227}}
h2{{font-family:Fraunces,Georgia,'DejaVu Serif',serif;font-size:30px}}
.big{{font-size:50px;font-weight:800;margin-top:10px}}
.big small{{font-size:18px;font-weight:600;color:#55657a}}
.sub{{font-size:17px;color:#55657a;margin:2px 0 14px;min-height:22px}}
table{{width:100%;border-collapse:collapse;font-size:19px}}
th{{text-align:left;font-size:14px;color:#55657a;text-transform:uppercase;letter-spacing:.04em;padding:6px 0;border-bottom:2px solid #eee}}
td{{padding:9px 0;border-bottom:1px solid #f0eee8}}
.r{{text-align:right}} .n{{color:#55657a}}
.up{{color:#1d7a46;font-size:15px;font-weight:700}} .dn{{color:#b42318;font-size:15px;font-weight:700}}
.foot{{margin-top:22px;font-size:15px;color:#55657a;display:flex;justify-content:space-between}}
</style></head><body>
<div class="top"><div><div class="eb">North HDB resale report</div><h1>{o['label']}</h1></div>
<div class="brand"><b>Serene Lee</b><br>ERA Realty · CEA R027578Z<br>sereneleeproperty.com</div></div>
<div class="grid">{cols}</div>
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


def P(*leaves):
    return {"type": "paragraph", "children": list(leaves)}


def T(text, **kw):
    d = {"text": text}
    d.update(kw)
    return d


def L(href, text):
    return {"type": "link", "href": href, "children": [{"text": text}]}


def kit_tree(o):
    m, u = o["month"], o["utm"]
    tree = [
        {"type": "heading", "level": 1, "children": [T(f"North HDB resale: {o['label']}")]},
        P(T("Hi there,")),
        P(T(f"Here's what HDB flats in Woodlands, Sembawang and Yishun resold for in {o['label']}, "
            "straight from HDB's official data.")),
        {"type": "image", "src": o["image"], "alt": f"North HDB resale report {o['label']}: flats sold and median prices for Woodlands, Sembawang and Yishun",
         "href": f"{SITE}/market-map?region=North&{u}", "fullWidth": True},
        {"type": "heading", "level": 2, "children": [T("3 things to know")]},
        {"type": "list", "children": [{"type": "list_item", "children": [T(h)]} for h in o["highlights"]]},
        {"type": "heading", "level": 2, "children": [T("What's your flat worth?")]},
        P(T("Town medians mix flats of different ages and sizes. For your own block, and what you could move to next, "
            "get a free personal plan from me.")),
        {"type": "button", "href": f"{SITE}/flat-report?{u}", "children": [T("Get My Free Flat Report")],
         "backgroundColor": "#C9A227", "color": "#0B2A4A", "roundedCornerOption": "small", "size": "large", "align": "center"},
        P(T("Town guides: "), L(f"{SITE}/woodlands?{u}", "Woodlands"), T(" · "), L(f"{SITE}/sembawang?{u}", "Sembawang"),
          T(" · "), L(f"{SITE}/yishun?{u}", "Yishun"), T(" · "), L(f"{SITE}/right-sizing-north?{u}", "Right-sizing guide")),
        P(T("Questions? Just reply to this email or "), L("https://wa.me/6580868568?text=Hi%20Serene%2C%20I%20read%20your%20North%20HDB%20report.", "WhatsApp me"), T(".")),
        P(T("Serene Lee")),
        {"type": "divider", "color": "#E6E2D8"},
        P(T("Serene Lee · ERA Realty Network Pte Ltd (L3002382K) · CEA Reg. R027578Z · +65 8086 8568. "
            "Figures are past HDB resale transactions (data.gov.sg), registered in the month shown; they are not a valuation.",
            fontSize=12, color="#6B7280")),
    ]
    subject = f"North HDB resale: {o['label']} ({o['total']} flats sold)"
    preview = o["highlights"][1] if len(o["highlights"]) > 1 else o["highlights"][0]
    return {"subject": subject, "preview_text": preview[:140], "content_tree": tree,
            "tag_id": 24833032, "email_template_id": 5567270}


if __name__ == "__main__":
    month = sys.argv[1] if len(sys.argv) > 1 else last_full_month()
    o, kit = build(month)
    print(json.dumps({"month": o["label"], "complete": o["complete"], "total": o["total"],
                      "highlights": o["highlights"], "image": o["image"], "subject": kit["subject"]}, indent=1))
