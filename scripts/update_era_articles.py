#!/usr/bin/env python3
"""
Weekly ERA Research & Insights refresh for sereneleeproperty.com

Reads the same feed that powers these ERA pages:
  https://www.era.com.sg/research-articles/   (category Research)
  https://www.era.com.sg/blogs                (category Blog)
  https://www.era.com.sg/press-release        (category PressRelease)
and rewrites the "ERA Research & Insights" list on blog.html between the
ERA-ARTICLES markers: the newest PER_CAT items of each category, each with
title, date, ERA's image, a short summary and a link to the full article
on era.com.sg. Full article text is never copied.

Summary = Serene's own note from scripts/era-notes.json when there is one
for that slug, otherwise ERA's own description, trimmed.

Also writes data/era-articles.json. If ERA cannot be reached or returns too
few items, nothing is changed and the script exits 1. Standard library only.
"""
import html, json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
API = "https://www.era.com.sg/api/article/search"
SGT = timezone(timedelta(hours=8))
PER_CAT = 6
MIN_ITEMS = 6
CATS = {  # API category: (label on the site, ERA path, tag css class)
    "Research": ("ERA Research", "research-articles", "blog-tag-research"),
    "Blog": ("Market Insight", "blogs", ""),
    "PressRelease": ("Press Release", "press-release", "blog-tag-pr"),
}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def fetch(cat):
    q = urllib.parse.urlencode({"category": cat, "page": 1, "pageSize": PER_CAT, "keyword": ""})
    req = urllib.request.Request(f"{API}?{q}", headers={
        "User-Agent": UA, "Accept": "application/json", "Referer": "https://www.era.com.sg/"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            items = d.get("data") or []
            print(f"  {cat}: {len(items)} items (of {d.get('totalCount')})")
            return items
        except Exception as e:  # noqa: BLE001
            print(f"  {cat}: attempt {attempt + 1} failed: {e}")
            time.sleep(5)
    return []


def trim(text, n=230):
    text = re.sub(r"\s+", " ", html.unescape(text or "")).strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0].rstrip(",;:–-")
    return cut + "…"


def nice_date(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(SGT)
    return d.strftime("%-d %b %Y"), d.strftime("%Y-%m-%d")


def row(a, notes):
    label, path, tagcls = CATS[a["category"]]
    shown, key = nice_date(a.get("publishedAt") or a.get("entryDate"))
    url = f"https://www.era.com.sg/{path}/{urllib.parse.quote(a['slug'])}"
    note = notes.get(a["slug"])
    summary = (f'<span class="era-take">Serene&rsquo;s take:</span>{note}' if note
               else html.escape(trim(a.get("description"))))
    img = a.get("imageUrl") or ""
    thumb = (f'<img src="{html.escape(img)}" alt="" loading="lazy">' if img else "")
    title = html.escape(re.sub(r"\s+", " ", a["title"]).strip())
    return (f'      <div class="blog-row" data-date="{key}" data-era-cat="{a["category"]}">\n'
            f'        <div class="blog-row-thumb">{thumb}</div>\n'
            f'        <div>\n'
            f'          <span class="blog-tag {tagcls}">{label}</span>\n'
            f'          <span style="font-size:.75rem;color:var(--muted);margin-left:8px;">ERA &middot; {shown}</span>\n'
            f'          <div class="blog-title" style="font-size:1.2rem;">{title}</div>\n'
            f'          <div class="blog-excerpt" style="max-width:700px;">{summary}</div>\n'
            f'          <a href="{url}" target="_blank" rel="noopener" style="font-size:.85rem;font-weight:700;color:var(--navy-900);">Read the full article on ERA &rarr;</a>\n'
            f'        </div>\n'
            f'      </div>\n')


def main():
    print("Fetching ERA articles...")
    items, failed = [], []
    for cat in CATS:
        got = [a for a in fetch(cat) if a.get("slug") and a.get("title") and a.get("category") == cat]
        if not got:
            failed.append(cat)
        items += got
    if len(items) < MIN_ITEMS:
        print(f"Only {len(items)} articles fetched — leaving the site unchanged.")
        sys.exit(1)
    items.sort(key=lambda a: a.get("publishedAt") or "", reverse=True)

    try:
        notes = json.load(open(os.path.join(ROOT, "scripts/era-notes.json"))).get("notes", {})
    except (OSError, ValueError):
        notes = {}

    path = os.path.join(ROOT, "blog.html")
    page = open(path).read()
    s, e = "<!-- ERA-ARTICLES:START -->", "<!-- ERA-ARTICLES:END -->"
    i, j = page.find(s), page.find(e)
    if i < 0 or j < i:
        raise SystemExit("ERA-ARTICLES markers missing in blog.html")
    body = "\n" + "".join(row(a, notes) for a in items) + "      "
    page = page[:i + len(s)] + body + page[j:]
    stamp = datetime.now(SGT).strftime("%-d %b %Y")
    page = re.sub(r"(<!-- ERA-ART-DATE:START -->).*?(<!-- ERA-ART-DATE:END -->)", rf"\g<1>{stamp}\g<2>", page)
    open(path, "w").write(page)

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    json.dump({"retrieved": datetime.now(SGT).isoformat(timespec="minutes"),
               "articles": [{"category": a["category"], "title": a["title"].strip(), "slug": a["slug"],
                             "published": a.get("publishedAt"),
                             "url": f"https://www.era.com.sg/{CATS[a['category']][1]}/{a['slug']}"} for a in items]},
              open(os.path.join(ROOT, "data/era-articles.json"), "w"), indent=1, ensure_ascii=False)
    print(f"Updated blog.html with {len(items)} ERA articles; newest: {items[0]['title'].strip()}")
    if failed:
        print(f"WARNING: no items from {', '.join(failed)} this week.")
        sys.exit(2)


if __name__ == "__main__":
    main()
