#!/usr/bin/env python3
"""
Builds /property-rates (property-rates.html): Singapore property rules and
rates on one page: LTV, TDSR/MSR, BSD, ABSD, SSD and the normal (progressive)
payment scheme for uncompleted private homes. Every figure is checked against
IRAS, MAS or HDB. Header and footer come from million-dollar-hdb.html, like
the other generated pages, so it runs inside build_town_pages.py's rebuild.

To change a rate: edit the tables below, update CHECKED, and push.
"""
import html, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SITE = "https://sereneleeproperty.com"
URL = SITE + "/property-rates"
CHECKED = "10 Nov 2026"

SRC = {
    "bsd": ("IRAS, BSD", "https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/buyer's-stamp-duty-(bsd)"),
    "absd": ("IRAS, ABSD", "https://www.iras.gov.sg/taxes/stamp-duty/for-property/buying-or-acquiring-property/additional-buyer's-stamp-duty-(absd)"),
    "fta": ("IRAS, ABSD under FTAs", "https://www.iras.gov.sg/taxes/stamp-duty/for-property/appeals-refunds-reliefs-and-remissions/common-stamp-duty-remissions-and-reliefs-for-property/foreigners-eligible-for-absd-remission-under-free-trade-agreements-(ftas)"),
    "couple": ("IRAS, ABSD remission for married couples", "https://www.iras.gov.sg/taxes/stamp-duty/for-property/appeals-refunds-reliefs-and-remissions/common-stamp-duty-remissions-and-reliefs-for-property/remission-of-absd-for-a-married-couple"),
    "ssd": ("IRAS, SSD", "https://www.iras.gov.sg/taxes/stamp-duty/for-property/selling-or-disposing-property/seller's-stamp-duty-(ssd)-for-residential-property"),
    "ssd25": ("MAS/MND, 3 Jul 2025 SSD changes", "https://www.mas.gov.sg/news/media-releases/2025/extension-of-the-holding-period-of-sellers-stamp-duty-and-higher-ssd-rates"),
    "ltv": ("MAS, loan tenure and LTV limits", "https://www.mas.gov.sg/regulation/explainers/new-housing-loans/loan-tenure-and-loan-to-value-limits"),
    "msr": ("MAS, MSR and TDSR rules", "https://www.mas.gov.sg/regulation/explainers/new-housing-loans/msr-and-tdsr-rules"),
    "tdsr": ("MAS, TDSR thresholds", "https://www.mas.gov.sg/regulation/explainers/tdsr-for-property-loans/calculating-tdsr-thresholds"),
    "hdb": ("HDB, 20 Aug 2024 HDB loan LTV", "https://www.hdb.gov.sg/business-partners/estate-agents-and-salespersons/letters-to-keos/measures-to-cool-the-hdb-resale-market-and-provide-greater-support-for-first-time-home-buyers"),
    "ura": ("URA, buying uncompleted private property", "https://www.ura.gov.sg/guidelines/property-and-business-owners/property/buying-property/"),
}

# Normal payment scheme (Housing Developers Rules) for uncompleted private homes.
NPS = [
    ("Booking fee", "When the Option to Purchase (OTP) is issued", 5),
    ("Sale & Purchase Agreement", "Within 8 weeks of the OTP date", 15),
    ("Foundation", "Completion of foundation work", 10),
    ("Framework", "Reinforced concrete framework", 10),
    ("Walls", "Partition walls", 5),
    ("Ceiling", "Roofing / ceiling", 5),
    ("Windows", "Doors, windows, electrical wiring, plumbing", 5),
    ("Car park", "Car park, roads and drains", 5),
    ("TOP", "Temporary Occupation Permit", 25),
    ("CSC", "Certificate of Statutory Completion", 15),
]
# LTV, minimum cash down payment (MAS)
NPS_LTV = [(75, 5), (55, 10), (45, 25)]


def esc(s):
    return html.escape(str(s), quote=True)


def src(*keys):
    return '<p class="pr-src">Source: ' + " · ".join(
        f'<a href="{SRC[k][1]}" target="_blank" rel="noopener">{esc(SRC[k][0])}</a>' for k in keys) + "</p>"


def chips(*items):
    return '<div class="pr-chips">' + "".join(f"<span>{esc(i)}</span>" for i in items) + "</div>"


def table(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="pr-tw"><table class="pr-t {cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def nps_split(ltv, cash_min):
    """For each stage, how it is paid (cash first, then cash/CPF, then loan)."""
    own = 100 - ltv
    paid, out = 0, []
    for _, _, pct in NPS:
        parts, left, start = [], pct, paid
        cash = max(0, min(left, cash_min - start))
        if cash:
            parts.append(f"{cash}% cash")
            left -= cash; start += cash
        cpf = max(0, min(left, own - start))
        if cpf:
            parts.append(f"{cpf}% CPF / cash")
            left -= cpf; start += cpf
        if left:
            parts.append("Loan" if left == pct else f"{left}% loan")
        paid += pct
        out.append("<br>".join(parts))
    return out


def body():
    ltv = table(
        ["Outstanding housing loans", "LTV limit", "LTV if tenure &gt; 30 yrs (HDB flat &gt; 25 yrs) or loan runs past age 65", "Min. cash down payment"],
        [["None (1st loan)", "<b>75%</b>", "<b>55%</b>", "5% (10% at 55% LTV)"],
         ["1", "<b>45%</b>", "<b>25%</b>", "25%"],
         ["2 or more", "<b>35%</b>", "<b>15%</b>", "25%"]])
    tdsr = table(["Ratio", "Limit", "Applies to"],
        [["<b>TDSR</b> (Total Debt Servicing Ratio)", "<b>55%</b> of gross monthly income", "All property loans from banks: covers all monthly debts (home, car, personal, student loans, credit cards)"],
         ["<b>MSR</b> (Mortgage Servicing Ratio)", "<b>30%</b> of gross monthly income", "HDB flats and ECs: covers all property loan repayments"]])
    bsd = table(["Purchase price or market value (higher of)", "Rate"],
        [["First $180,000", "1%"], ["Next $180,000", "2%"], ["Next $640,000", "3%"],
         ["Next $500,000", "4%"], ["Next $1,500,000", "5%"], ["Above $3,000,000", "6%"]], "pr-t2")
    absd = table(["Buyer", "1st home", "2nd home", "3rd and later"],
        [["Singapore Citizen", "0%", "20%", "30%"],
         ["Singapore PR", "5%", "30%", "35%"],
         ["Foreigner", "60%", "60%", "60%"],
         ["Entity / trustee", "65%", "65%", "65%"]])
    ssd = table(["Held for", "Bought on/after 4 Jul 2025", "Bought 11 Mar 2017 – 3 Jul 2025"],
        [["Up to 1 year", "<b>16%</b>", "12%"], ["1 to 2 years", "<b>12%</b>", "8%"],
         ["2 to 3 years", "<b>8%</b>", "4%"], ["3 to 4 years", "<b>4%</b>", "None"],
         ["More than 4 years", "None", "None"]])
    cols = [nps_split(l, c) for l, c in NPS_LTV]
    nps_rows = [[f"<b>{esc(n)}</b><span class='pr-sub'>{esc(w)}</span>", f"<b>{p}%</b>"] + [c[i] for c in cols]
                for i, (n, w, p) in enumerate(NPS)]
    nps = table(["Stage", "Payment"] + [f"With {l}% loan" for l, _ in NPS_LTV], nps_rows, "pr-nps")

    cards = [
        ("ltv", "LTV", "Loan-to-value limits", "How much a bank can lend, as a share of the price or valuation (whichever is lower).",
         chips("All buyers", "All bank housing loans") + ltv +
         '<ul class="pr-notes"><li>Maximum loan tenure: <b>30 years</b> for HDB flats, <b>35 years</b> for private property.</li>'
         '<li>Joint borrowers: age is the <b>income-weighted average age</b> (each borrower\'s age × their share of combined income).</li>'
         '<li>HDB housing loan: LTV <b>75%</b> (down from 80% since 20 Aug 2024).</li>'
         '<li>Borrowers that are companies or other non-individuals: LTV <b>15%</b>.</li></ul>' + src("ltv", "hdb")),
        ("tdsr", "TDSR &amp; MSR", "Debt servicing limits", "Caps on how much of your income can go to loan repayments.",
         chips("All buyers", "Bank loans and HDB loans") + tdsr +
         '<ul class="pr-notes"><li>Applies when the OTP was granted on or after 16 Dec 2021.</li>'
         '<li>Banks assess TDSR at a stress-test interest rate, not today\'s rate, and count only part of variable income (bonus, commission, rental). Ask your banker for your exact figure.</li></ul>'
         + src("msr", "tdsr")),
        ("bsd", "BSD", "Buyer's Stamp Duty", "Paid on every residential purchase. Rates for purchases on or after 15 Feb 2023.",
         chips("All buyers", "Cash or CPF", "Due within 14 days of exercising the OTP / signing") + bsd +
         '<ul class="pr-notes"><li>Example: a $1.5M condo pays $44,600 BSD.</li><li>Rounded down to the nearest dollar.</li></ul>' + src("bsd")),
        ("absd", "ABSD", "Additional Buyer's Stamp Duty", "Paid on top of BSD, based on who is buying and how many homes they own. Rates from 27 Apr 2023.",
         chips("Selected buyers", "Cash, CPF reimbursement possible", "Due within 14 days of exercising the OTP / signing") + absd +
         '<ul class="pr-notes"><li><b>Joint buyers</b> pay the highest rate that applies to any of them.</li>'
         '<li><b>Free trade agreements:</b> nationals of the USA, and nationals and PRs of Iceland, Liechtenstein, Norway and Switzerland, pay the same as Singapore Citizens.</li>'
         '<li><b>Married couples (at least one Singapore Citizen), buying jointly:</b> ABSD on a 1st home is remitted. On a 2nd home, the couple can claim a refund if they sell their 1st home within 6 months of buying (for an uncompleted property, within 6 months of TOP or CSC, whichever is earlier) and meet IRAS conditions.</li>'
         '<li>Housing developers: 35% plus a non-remittable 5%.</li></ul>' + src("absd", "fta", "couple")),
        ("ssd", "SSD", "Seller's Stamp Duty", "Paid by the seller when a residential property is sold within the holding period. Based on the date the seller bought it.",
         chips("Sellers", "Cash", "Due within 14 days of the sale (OTP exercised / S&P signed)") + ssd +
         '<ul class="pr-notes"><li>Charged on the sale price or market value, whichever is higher.</li>'
         '<li>The holding period went up from 3 to 4 years for homes bought on or after 4 Jul 2025.</li></ul>' + src("ssd", "ssd25")),
        ("nps", "NPS", "Progressive payment scheme", "The normal payment scheme for buying an uncompleted private home (new launch) from a developer. Excludes ECs and HDB BTO flats.",
         chips("New launch buyers", "Paid by stage of construction") + nps +
         '<ul class="pr-notes"><li>The last three columns show how each stage is paid at each LTV limit. Your own money (cash first, then CPF or cash) goes in before the bank loan.</li>'
         '<li>The booking fee is always paid in cash.</li>'
         '<li>Always check the payment schedule in the developer\'s Sale &amp; Purchase Agreement for your unit.</li></ul>' + src("ura")),
    ]
    jump = "".join(f'<a href="#{cid}" class="filter-chip">{lab}</a>' for cid, lab, *_ in cards)
    html_cards = "".join(
        f'<div class="pr-card" id="{cid}"><div class="pr-hd"><span class="pr-tag">{lab}</span><h2>{esc(title)}</h2></div>'
        f'<p class="pr-lede">{esc(lede)}</p>{inner}</div>' for cid, lab, title, lede, inner in cards)
    return f"""
<div class="page-hero page-hero-wide container">
  <span class="eyebrow">Property rates &amp; rules</span>
  <h1 style="font-size:2.1rem;">Singapore property rates and rules, on one page</h1>
  <p>Loan limits, stamp duties and the new launch payment schedule that every buyer and seller should know.</p>
  <p class="pr-upd">Every rate checked against IRAS, MAS and HDB on {CHECKED}. Compiled with AI assistance and reviewed by Serene Lee. Rates can change with new cooling measures, so check the official source before you commit.</p>
  <div class="un-tools"><button type="button" class="btn btn-navy btn-sm" id="prPrint">Print this page</button>
    <a class="btn btn-gold btn-sm" target="_blank" rel="noopener" id="prWa" href="https://wa.me/6580868568?text=Hi%20Serene%2C%20could%20you%20work%20out%20the%20stamp%20duty%20and%20loan%20for%20a%20property%20I%27m%20looking%20at%3F">Work out my numbers with Serene</a></div>
  <nav class="un-jump" aria-label="Sections">{jump}</nav>
</div>

<section style="padding-top:8px;"><div class="container">
  <div class="pr-grid">{html_cards}</div>
  <p class="pr-src" style="margin-bottom:24px;">This page is general information only and does not constitute financial, legal or tax advice. Your loan and stamp duty depend on your own circumstances. Spot an outdated rate? <a href="/contact">Let Serene know</a>.</p>
</div></section>

<section class="cta-banner un-noprint"><div class="container cta-banner">
  <h2>Buying, selling or upgrading? Get your numbers checked.</h2>
  <div class="btns">
    <a href="/calculator" class="btn btn-navy">Try the Affordability Calculator</a>
    <a href="https://wa.me/6580868568?text=Hi%20Serene%2C%20I%20saw%20your%20property%20rates%20page%20and%20would%20like%20to%20chat." target="_blank" rel="noopener" class="btn" style="background:#fff;color:var(--navy-900);">WhatsApp Serene</a>
  </div>
</div></section>
<script>
(function(){{
  function track(e,p){{try{{window.posthog&&posthog.capture(e,p);}}catch(x){{}}}}
  document.getElementById("prPrint").onclick=function(){{track("property_rates_print",{{}});window.print();}};
  document.getElementById("prWa").onclick=function(){{track("whatsapp_clicked",{{button_text:"Work out my numbers with Serene",button_location:"property rates",page_path:location.pathname}});}};
}})();
</script>
"""


CSS = """<style>
.pr-upd{font-size:.84rem;color:var(--muted);max-width:760px}
.un-tools{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 6px}
.un-jump{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.un-jump .filter-chip{text-decoration:none;font-size:.82rem}
.pr-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin-bottom:20px}
.pr-card#nps,.pr-card#ltv{grid-column:1/-1}
@media(max-width:860px){.pr-grid{grid-template-columns:1fr}}
.pr-card{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:18px 20px;min-width:0;scroll-margin-top:90px}
.pr-hd{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.pr-tag{font:700 .78rem/1 'Inter',sans-serif;letter-spacing:.06em;color:#fff;background:var(--navy-900);border-radius:6px;padding:5px 8px}
.pr-card h2{font-size:1.15rem;margin:0}
.pr-lede{color:var(--muted);font-size:.88rem;margin:8px 0 10px}
.pr-chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.pr-chips span{font-size:.75rem;background:var(--cream);border:1px solid var(--line);border-radius:999px;padding:4px 10px;color:var(--navy-900)}
.pr-tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
.pr-t{width:100%;border-collapse:collapse;font-size:.88rem;font-variant-numeric:tabular-nums}
.pr-t th{background:var(--navy-900);color:#fff;text-align:left;font-weight:600;font-size:.78rem;padding:8px 10px;vertical-align:bottom}
.pr-t td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.pr-t tbody tr:nth-child(even) td{background:#fafaf7}
.pr-t2 td:last-child,.pr-t2 th:last-child{text-align:right}
.pr-nps{min-width:640px}
.pr-nps td{font-size:.82rem}
.pr-sub{display:block;color:var(--muted);font-size:.75rem;margin-top:2px}
.pr-notes{margin:12px 0 0;padding-left:18px;font-size:.86rem;line-height:1.5}
.pr-notes li{margin:4px 0}
.pr-src{font-size:.75rem;color:var(--muted);margin:10px 0 0;line-height:1.55}
.pr-src a{color:inherit}
@media print{
  header,footer,.fab-wa,.un-tools,.un-jump,.un-noprint,#chatbotLauncher,.chatbot-launcher,.chatbot-panel,[class*="profile-card"]{display:none!important}
  .pr-grid{display:block}.pr-card{break-inside:avoid;margin-bottom:12px}
}
</style>"""


def main():
    tpl = open(os.path.join(ROOT, "million-dollar-hdb.html"), encoding="utf-8").read()
    head = tpl[:tpl.index("<body>")]
    header = tpl[tpl.index("<body>"):tpl.index("</header>") + len("</header>")].replace(' class="active"', "") + "\n"
    footer = "\n" + tpl[tpl.index("<!-- FOOTER -->"):]
    head = re.sub(r'\n?<script type="application/ld\+json" data-schema="(?:breadcrumb|dataset)">.*?</script>', "", head, flags=re.S)

    t = "Singapore Property Rates & Rules: LTV, TDSR, BSD, ABSD, SSD | Serene Lee"
    d = ("Loan-to-value limits, TDSR and MSR, buyer's and additional buyer's stamp duty, seller's stamp duty and the new "
         "launch progressive payment scheme, checked against IRAS, MAS and HDB.")
    h = re.sub(r"<title>.*?</title>", f"<title>{esc(t)}</title>", head, flags=re.S)
    h = re.sub(r'(<meta (?:name|property)="(?:description|og:description|twitter:description)" content=")[^"]*', lambda m: m.group(1) + esc(d), h)
    h = re.sub(r'(<meta (?:property|name)="(?:og:title|twitter:title)" content=")[^"]*', lambda m: m.group(1) + esc(t), h)
    h = re.sub(r'(<link rel="canonical" href=")[^"]*', r"\g<1>" + URL, h)
    h = re.sub(r'(<meta property="og:url" content=")[^"]*', r"\g<1>" + URL, h)
    h = h.replace("</head>", CSS + "\n</head>")
    with open(os.path.join(ROOT, "property-rates.html"), "w", encoding="utf-8") as fh:
        fh.write(h + header + body() + footer)
    print("built property-rates.html")


if __name__ == "__main__":
    main()
