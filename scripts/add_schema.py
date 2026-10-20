#!/usr/bin/env python3
"""
Adds Google structured data (schema.org JSON-LD) to every public page:

  BreadcrumbList  every indexable page except the home page
                  e.g. Home > Town Guides > Woodlands, Home > Blog > <post>
  Dataset         pages that publish HDB / URA figures: the 26 town pages,
                  the Market Map and the Million-Dollar HDB list

Safe to run any number of times: blocks it added before (marked
data-schema="breadcrumb" / "dataset") are replaced, never duplicated.
Runs in deploy.yml and the weekly data workflows, after build_town_pages.py,
so new pages and new data dates are picked up automatically.

Standard library only.
"""
import glob, html, json, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SITE = "https://sereneleeproperty.com"
SKIP = {"404.html", "SendDialog.html", "index.html"}

# Breadcrumb label for each top-level page (page file name without .html)
NAMES = {
    "about": "About", "blog": "Blog", "faq": "FAQ", "contact": "Contact",
    "calculator": "Affordability Calculator", "upgrade-checklist": "Upgrade Checklist",
    "buyer-check": "Buyer Readiness Check", "market-map": "Market Map",
    "million-dollar-hdb": "Million-Dollar HDB", "new-launches": "New Launches",
    "subscribers": "Subscribe", "privacy": "Privacy Policy", "town-guide": "Town Guides", "right-sizing-north": "Right-Sizing Guide", "useful-numbers": "Useful Phone Numbers",
    "testimonials": "Testimonials",
}
BLOG_CHILDREN = {"quiz-lease-decay"}  # pages that sit under the Blog

HDB_SRC = "https://data.gov.sg/datasets/d_8b84c4ee58e3cfc0ece0d773c8ca6abc/view"
URA_SRC = "https://eservice.ura.gov.sg/maps/api/"
ONEMAP_SRC = "https://www.onemap.gov.sg/"
CREATOR = {"@type": "Person", "name": "Serene Lee", "url": SITE + "/about",
           "jobTitle": "Property Agent, ERA Realty Network (CEA R027578Z)"}


def load(p):
    with open(os.path.join(ROOT, "data", p)) as f:
        return json.load(f)


def block(kind, obj):
    return (f'<script type="application/ld+json" data-schema="{kind}">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "</script>")


def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


def page_title(h):
    m = re.search(r"<title>(.*?)</title>", h, re.S)
    t = html.unescape(m.group(1)).strip() if m else ""
    return re.split(r"\s+\|\s+", t)[0].strip()


def dataset(name, desc, url, temporal, place, modified, variables, sources, keywords):
    return {
        "@context": "https://schema.org", "@type": "Dataset",
        "name": name, "description": desc, "url": url,
        "creator": CREATOR, "isAccessibleForFree": True,
        "keywords": keywords,
        "temporalCoverage": temporal,
        "spatialCoverage": {"@type": "Place", "name": place,
                            "address": {"@type": "PostalAddress", "addressCountry": "SG"}},
        "dateModified": modified,
        "variableMeasured": variables,
        "isBasedOn": sources,
    }


def main():
    market = load("market-data.json")
    hdb, ura = market["hdb"], market["ura"]
    last = hdb["last_month"]
    hdb_date = hdb["fetched"][:10]
    towns = {v["file"]: (t, v) for t, v in hdb["towns"].items()}
    title = lambda s: re.sub(r"(^|[\s/(])(\w)", lambda m: m.group(1) + m.group(2).upper(), s.lower())
    try:
        million = load("hdb/million-summary.json")
    except (FileNotFoundError, json.JSONDecodeError):
        million = {}

    home = ("Home", SITE + "/")
    n_bc = n_ds = 0
    pages = sorted(glob.glob(os.path.join(ROOT, "*.html"))) + sorted(glob.glob(os.path.join(ROOT, "hdb", "*", "*.html")))
    for path in pages:
        name = os.path.basename(path)
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        if name in SKIP:
            continue
        h = open(path, encoding="utf-8").read()
        if re.search(r'<meta name="robots" content="[^"]*noindex', h):
            continue
        h = re.sub(r'\n?<script type="application/ld\+json" data-schema="(?:breadcrumb|dataset)">.*?</script>', "", h, flags=re.S)
        slug = rel[:-5]
        url = f"{SITE}/{slug}"
        add = []

        # ---------------- breadcrumbs
        if slug.startswith("hdb/"):  # block page: Home > Town Guides > Town > Blk
            tslug = slug.split("/")[1]
            tname = title(towns[tslug][0]) if tslug in towns else tslug.title()
            add.append(block("breadcrumb", crumbs([home, ("Town Guides", SITE + "/town-guide"), (tname, f"{SITE}/{tslug}"),
                                                   (page_title(h).replace(" HDB Resale Prices", "").replace(" Resale Prices", ""), url)])))
        elif slug in towns:
            tname = title(towns[slug][0])
            add.append(block("breadcrumb", crumbs([home, ("Town Guides", SITE + "/town-guide"), (tname, url)])))
        elif slug.startswith("blog-") or slug in BLOG_CHILDREN:
            add.append(block("breadcrumb", crumbs([home, ("Blog", SITE + "/blog"), (page_title(h), url)])))
        else:
            add.append(block("breadcrumb", crumbs([home, (NAMES.get(slug) or page_title(h), url)])))
        n_bc += 1

        # ---------------- datasets
        ds = None
        if slug in towns:
            town, info = towns[slug]
            tname = title(town)
            try:
                since = load(f"hdb/{info['file']}.json").get("since", "")
            except FileNotFoundError:
                since = ""
            ds = dataset(
                f"{tname} HDB resale and private property prices",
                (f"HDB resale prices in {tname}, Singapore, by flat type, remaining lease and nearest MRT station, "
                 f"with quarterly averages and block-level resales over the last 3 years, "
                 f"plus condo and executive condo transactions near {tname} and current new launches. "
                 f"Compiled weekly from HDB resale records (data.gov.sg), URA private residential transactions "
                 f"and OneMap locations."),
                url, f"{since or months_back(last, 35)}/{last}", f"{tname}, Singapore", hdb_date,
                ["Resale price (SGD)", "Price per square foot (SGD)", "Flat type", "Floor area",
                 "Lease commencement year", "Distance to nearest MRT station (m)"],
                [HDB_SRC, URA_SRC, ONEMAP_SRC],
                [f"{tname} HDB resale prices", f"{tname} condo prices", "Singapore property prices", "HDB resale"])
        elif slug == "market-map":
            ds = dataset(
                "Singapore HDB resale and private property transactions by town and district",
                (f"Quarterly HDB resale volumes and average prices for every HDB town since 2017, private residential "
                 f"transactions by postal district (new sale, sub sale and resale) for the last 5 years, and block- and "
                 f"project-level deal histories. Compiled weekly from HDB resale records (data.gov.sg) and URA private "
                 f"residential transactions, with OneMap locations and MRT distances."),
                url, f"2017-01/{last}", "Singapore", hdb_date,
                ["Resale price (SGD)", "Number of transactions", "Price per square foot (SGD)", "Type of sale",
                 "Market segment (CCR/RCR/OCR)", "Distance to nearest MRT station (m)"],
                [HDB_SRC, URA_SRC, ONEMAP_SRC],
                ["Singapore property market", "HDB resale prices", "URA private transactions", "condo prices by district"])
        elif slug == "million-dollar-hdb":
            ds = dataset(
                "Million-dollar HDB resale flats in Singapore",
                ("Every HDB resale flat registered at $1,000,000 or more in the last 36 months, with town, block, street, "
                 "flat type, floor band, floor area, flat model, lease commencement year and price. "
                 "Compiled weekly from HDB resale records published on data.gov.sg."),
                url, f"{million.get('since') or months_back(last, 35)}/{last}", "Singapore", hdb_date,
                ["Resale price (SGD)", "Price per square foot (SGD)", "Flat type", "Floor band", "Floor area",
                 "Lease commencement year"],
                [HDB_SRC],
                ["million-dollar HDB", "HDB resale prices", "Singapore HDB"])
        if ds:
            add.append(block("dataset", ds))
            n_ds += 1

        h = h.replace("</head>", "\n".join(add) + "\n</head>", 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(h)
    print(f"schema: {n_bc} breadcrumb lists, {n_ds} datasets")


def months_back(ym, n):
    y, m = int(ym[:4]), int(ym[5:7]) - n
    while m <= 0:
        m += 12
        y -= 1
    return f"{y:04d}-{m:02d}"


if __name__ == "__main__":
    main()
