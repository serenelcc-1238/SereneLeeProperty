#!/usr/bin/env python3
"""
Builds /useful-numbers (useful-numbers.html): one de-duplicated list of
phone numbers for Singapore home owners, each checked against the agency's own
website. Header and footer come from million-dollar-hdb.html, like the other
generated pages, so it runs inside build_town_pages.py's weekly rebuild.

To change a number: edit SECTIONS below, update CHECKED, and push.
"""
import html, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SITE = "https://sereneleeproperty.com"
URL = SITE + "/useful-numbers"
CHECKED = "20 Oct 2026"

S = {
    "spf": ("Singapore Police Force", "https://www.police.gov.sg/contact-us"),
    "sms": ("SPF, SMS 70999", "https://www.police.gov.sg/SMS-70999"),
    "scdf": ("SCDF", "https://scdf.gov.sg/home/about-us/information-on-ems"),
    "sp": ("SP Group", "https://www.spgroup.com.sg/contact-us"),
    "pub": ("PUB", "https://pub.gov.sg/contact-us"),
    "nea": ("NEA", "https://nea.gov.sg/corporate-functions/Contact-Us"),
    "avs": ("NParks AVS", "https://avs.nparks.gov.sg/contact-us/"),
    "acres": ("ACRES", "https://acres.org.sg/?p=1466"),
    "hdb": ("HDB (17 Nov 2025 notice)", "https://www.hdb.gov.sg/business/estate-agents-and-salespersons/letters-to-keos/Transition-to-Non-Toll-Free-Numbers-for-HDB-managed-Hotlines"),
    "cea": ("CEA", "https://www.cea.gov.sg/contact-us/"),
    "ura": ("URA", "https://www.ura.gov.sg/Corporate/Contact-Us"),
    "iras": ("IRAS", "https://www.iras.gov.sg/irashome/Contact-Us/Call-us/"),
    "cpf": ("CPF Board", "https://www.cpf.gov.sg/member/contact-us/call-us"),
    "moh": ("MOH", "https://moh.gov.sg/contact-us"),
    "ica": ("ICA", "https://ica.gov.sg/contactus"),
    "mom": ("MOM", "https://mom.gov.sg/contact-us/phone"),
    "sbtc": ("Sembawang Town Council", "https://sbtc.org.sg/?p=1683"),
    "nstc": ("Nee Soon Town Council", "https://www.nstc.org.sg/useful-hotlines/"),
}

# (name, what it's for, number as shown, source key)
SECTIONS = [
    ("Emergency", "em", [
        ("Police", "Crime or danger, right now", "999", "spf"),
        ("Fire and emergency ambulance", "Fire, or someone seriously ill or injured", "995", "scdf"),
        ("Police emergency SMS", "When it isn't safe to talk (replaced 71999 in 2024)", "70999", "sms"),
        ("Non-emergency ambulance", "Hospital transport that isn't an emergency", "1777", "scdf"),
        ("ScamShield helpline", "Unsure if a call, message or person is a scam (24 hours)", "1799", "spf"),
    ]),
    ("Police and safety (non-urgent)", "sf", [
        ("Police hotline", "Give information on a crime", "1800 255 0000", "spf"),
        ("Traffic Police", "Traffic enquiries", "6547 0000", "spf"),
        ("SCDF fire hazard reporting", "Blocked exits, fire safety concerns", "1800 280 0000", "scdf"),
        ("SCDF general enquiries", "Other SCDF matters", "1800 286 5555", "scdf"),
    ]),
    ("Home: power, water and gas", "ut", [
        ("Electricity fault or outage", "SP Group, 24 hours", "1800 778 8888", "sp"),
        ("Gas leak or gas supply fault", "SP Group gas emergency", "1800 752 1800", "sp"),
        ("Utilities bill and account", "SP Services billing", "1800 222 2333", "sp"),
        ("Water pipe burst or no water", "PUB 24-hour call centre", "1800 2255 782", "pub"),
    ]),
    ("Estate and neighbourhood", "es", [
        ("NEA", "Cleanliness, hygiene, mosquito breeding", "6225 5632", "nea"),
        ("Animal Response Centre", "Animal welfare and nuisance, injured animals (24 hours)", "1800 476 1600", "avs"),
        ("ACRES wildlife rescue", "Wildlife rescue, 7am to 1am daily", "9783 7782", "acres"),
        ("NParks", "Park maintenance, tree trimming", "1800 471 7300", "sbtc"),
        ("LTA", "Roads, road works, traffic matters", "1800 225 5582", "sbtc"),
        ("Community Mediation Centre", "Neighbour disputes", "1800 2255 529", "sbtc"),
    ]),
    ("Town councils in the North", "tc", [
        ("Sembawang Town Council: 24-hour repairs", "Lift breakdowns, power or water failure in common areas", "1800 275 5555", "sbtc"),
        ("Sembawang Town Council office", "Admiralty, Canberra, Naval Base, Sembawang and Woodlands divisions", "6368 3100", "sbtc"),
        ("Nee Soon Town Council office", "Yishun estates", "6758 0129", "nstc"),
    ]),
    ("Housing and property", "pr", [
        ("HDB Branch Service Line", "Your flat, repairs, branch matters", "6225 5432", "hdb"),
        ("HDB Sales and Resale", "Buying or selling an HDB flat", "6866 3066", "hdb"),
        ("HDB SERS enquiries", "Selective En bloc Redevelopment Scheme", "6866 3070", "hdb"),
        ("CEA (Council for Estate Agencies)", "Check or report a property agent", "1800 643 2555", "cea"),
        ("URA", "Planning, private property, car parks", "6221 6666", "ura"),
    ]),
    ("Government services", "gv", [
        ("CPF Board", "CPF accounts, housing and retirement", "1800 227 1188", "cpf"),
        ("IRAS", "Income tax (salaried employees)", "1800 356 8300", "iras"),
        ("MOH general line", "Weekdays 8.30am to 6pm", "6325 9220", "moh"),
        ("ICA call centre", "Passports, IC, PR; weekdays 8am to 5.30pm", "6391 6100", "ica"),
        ("MOM", "Service feedback; most enquiries are online", "6438 5122", "mom"),
    ]),
]


def esc(s):
    return html.escape(str(s), quote=True)


def tel(n):
    return "tel:" + re.sub(r"\D", "", n)


def main():
    tpl = open(os.path.join(ROOT, "million-dollar-hdb.html"), encoding="utf-8").read()
    head = tpl[:tpl.index("<body>")]
    header = tpl[tpl.index("<body>"):tpl.index("</header>") + len("</header>")].replace(' class="active"', "") + "\n"
    footer = "\n" + tpl[tpl.index("<!-- FOOTER -->"):]
    head = re.sub(r'\n?<script type="application/ld\+json" data-schema="(?:breadcrumb|dataset)">.*?</script>', "", head, flags=re.S)

    t = "Useful Phone Numbers for Singapore Home Owners | Serene Lee"
    d = ("Emergency, HDB, CPF, utilities, town council and property hotlines in one list, each checked against the "
         "official website. Tap to call.")
    h = re.sub(r"<title>.*?</title>", f"<title>{esc(t)}</title>", head, flags=re.S)
    h = re.sub(r'(<meta (?:name|property)="(?:description|og:description|twitter:description)" content=")[^"]*', lambda m: m.group(1) + esc(d), h)
    h = re.sub(r'(<meta (?:property|name)="(?:og:title|twitter:title)" content=")[^"]*', lambda m: m.group(1) + esc(t), h)
    h = re.sub(r'(<link rel="canonical" href=")[^"]*', r"\g<1>" + URL, h)
    h = re.sub(r'(<meta property="og:url" content=")[^"]*', r"\g<1>" + URL, h)
    h = h.replace("</head>", CSS + "\n</head>")

    jump = "".join(f'<a href="#{sid}" class="filter-chip">{esc(name)}</a>' for name, sid, _ in SECTIONS)
    cards = ""
    for name, sid, rows in SECTIONS:
        items = "".join(
            f'<li><div class="un-what"><b>{esc(n)}</b><span>{esc(w)}</span></div>'
            f'<a class="un-call" href="{tel(num)}" data-num="{esc(n)}">{esc(num)}</a></li>'
            for n, w, num, src in rows)
        cards += f'<div class="un-card{" un-em" if sid == "em" else ""}" id="{sid}"><h2>{esc(name)}</h2><ul>{items}</ul></div>'
    used = []
    for _, _, rows in SECTIONS:
        for r in rows:
            if r[3] not in used:
                used.append(r[3])
    srcs = " · ".join(f'<a href="{S[k][1]}" target="_blank" rel="noopener">{esc(S[k][0])}</a>' for k in used)

    body = f"""
<div class="page-hero page-hero-wide container">
  <span class="eyebrow">Useful phone numbers</span>
  <h1 style="font-size:2.1rem;">Useful phone numbers for Singapore home owners</h1>
  <p>Emergency, home, estate and government hotlines in one list. On your phone, tap a number to call.</p>
  <p class="un-upd">Every number checked against the agency's own website on {CHECKED}. HDB's hotlines changed from 1800 numbers on 17 Nov 2025, so older lists may be out of date.</p>
  <div class="un-tools"><button type="button" class="btn btn-navy btn-sm" id="unPrint">Print this list</button>
    <a class="btn btn-gold btn-sm" target="_blank" rel="noopener" id="unWa" href="https://wa.me/6580868568?text=Hi%20Serene%2C%20could%20you%20send%20me%20your%20useful%20phone%20numbers%20list%3F">Send me this list on WhatsApp</a></div>
  <nav class="un-jump" aria-label="Sections">{jump}</nav>
</div>

<section style="padding-top:8px;"><div class="container">
  <div class="un-grid">{cards}</div>
  <div class="un-card un-note"><h2>Before you call</h2>
    <ul class="un-plain">
      <li>In an emergency, always call 999 (Police) or 995 (Fire and Ambulance) first.</li>
      <li>Calling a 1800 number from a mobile may still use your plan's airtime.</li>
      <li>Your own town council's 24-hour number is also on the notice board at your lift lobby.</li>
      <li>Government officers will never ask you to transfer money or give your Singpass details over the phone. If unsure, hang up and call ScamShield at 1799.</li>
    </ul>
    <p class="un-src">Sources, checked {CHECKED}: {srcs}. Numbers can change; if one doesn't work, check the agency's website. Spot an outdated number? <a href="/contact">Let Serene know</a>.</p>
  </div>
</div></section>

<section class="cta-banner un-noprint"><div class="container cta-banner">
  <h2>Planning a move? Talk to Serene.</h2>
  <div class="btns">
    <a href="/town-guide" class="btn btn-navy">See Prices in Your Estate</a>
    <a href="https://wa.me/6580868568?text=Hi%20Serene%2C%20I%20saw%20your%20useful%20numbers%20page%20and%20would%20like%20to%20chat." target="_blank" rel="noopener" class="btn" style="background:#fff;color:var(--navy-900);">WhatsApp Serene</a>
  </div>
</div></section>
<script>
(function(){{
  function track(e,p){{try{{window.posthog&&posthog.capture(e,p);}}catch(x){{}}}}
  document.getElementById("unPrint").onclick=function(){{track("useful_numbers_print",{{}});window.print();}};
  document.getElementById("unWa").onclick=function(){{track("whatsapp_clicked",{{button_text:"Send me this list on WhatsApp",button_location:"useful numbers",page_path:location.pathname}});}};
  document.addEventListener("click",function(e){{var a=e.target.closest(".un-call");if(a)track("useful_number_call",{{line:a.getAttribute("data-num")}});}});
}})();
</script>
"""
    with open(os.path.join(ROOT, "useful-numbers.html"), "w", encoding="utf-8") as fh:
        fh.write(h + header + body + footer)
    print("built useful-numbers.html")


CSS = """<style>
.un-upd{font-size:.84rem;color:var(--muted);max-width:760px}
.un-tools{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 6px}
.un-jump{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.un-jump .filter-chip{text-decoration:none;font-size:.82rem}
.un-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin-bottom:20px}
@media(max-width:860px){.un-grid{grid-template-columns:1fr}}
.un-card{background:#fff;border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;min-width:0;scroll-margin-top:90px}
.un-card h2{font-size:1.1rem;margin:0 0 6px}
.un-card ul{list-style:none;margin:0;padding:0}
.un-card li{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 0;border-top:1px solid var(--line)}
.un-card li:first-child{border-top:0}
.un-what{min-width:0}
.un-what b{display:block;color:var(--navy-900);font-size:.95rem}
.un-what span{display:block;color:var(--muted);font-size:.8rem;margin-top:2px}
.un-call{flex:none;font:600 1.05rem/1 'Inter',sans-serif;font-variant-numeric:tabular-nums;color:var(--navy-900);text-decoration:none;background:var(--cream);border:1px solid var(--line);border-radius:999px;padding:8px 14px;white-space:nowrap}
.un-call:hover{border-color:var(--gold)}
.un-em{border-color:#d9a0a0}
.un-em h2{color:#a8321f}
.un-em .un-call{background:#fbecea;border-color:#efc4be;color:#8a2a1a;font-size:1.15rem}
.un-plain{list-style:disc!important;padding-left:20px!important}
.un-plain li{display:list-item;border:0;padding:4px 0;font-size:.92rem}
.un-note{margin-bottom:20px}
.un-src{font-size:.75rem;color:var(--muted);margin:10px 0 0;line-height:1.55}
.un-src a{color:inherit}
@media print{
  header,footer,.fab-wa,.un-tools,.un-jump,.un-noprint,#chatbotLauncher,.chatbot-launcher,.chatbot-panel,[class*="profile-card"]{display:none!important}
  body{background:#fff}
  .un-grid{grid-template-columns:1fr 1fr;gap:10px}
  .un-card{break-inside:avoid;padding:8px 10px}
  .un-call{background:none;border:0;padding:0;font-size:.95rem}
  .page-hero{padding:0}
}
</style>"""


if __name__ == "__main__":
    main()
