#!/usr/bin/env python3
"""
Rebuild sitemap.xml from the site's .html pages.

Every public page is listed under its short address (e.g. /market-map), matching
each page's canonical link. Pages marked noindex, 404.html and internal files
are left out, so a new blog post is picked up automatically the next time this
runs (deploy.yml runs it before every deploy). Standard library only.
"""
import glob, os, re, subprocess
from datetime import datetime, timezone, timedelta

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SITE = "https://sereneleeproperty.com"
SKIP = {"404.html", "SendDialog.html"}
WEEKLY = {"index.html", "market-map.html", "million-dollar-hdb.html", "new-launches.html", "blog.html"}
PRIORITY = {"index.html": "1.0", "market-map.html": "0.9", "million-dollar-hdb.html": "0.9", "new-launches.html": "0.9",
            "calculator.html": "0.8", "blog.html": "0.8", "upgrade-checklist.html": "0.7", "faq.html": "0.7"}


def git_date(path):
    """Date (Singapore time) the file last changed in git; today if git has no record.
    Workflows check out the full history (fetch-depth: 0) so this is accurate."""
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cI", "--", os.path.basename(path)],
                             cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        if out:
            return datetime.fromisoformat(out).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    except Exception:
        pass
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")


def main():
    urls = []
    for path in sorted(glob.glob(os.path.join(ROOT, "*.html"))):
        name = os.path.basename(path)
        if name in SKIP:
            continue
        html = open(path, encoding="utf-8").read()
        if re.search(r'<meta name="robots" content="[^"]*noindex', html):
            continue
        loc = SITE + "/" if name == "index.html" else SITE + "/" + name[:-5]
        pri = PRIORITY.get(name, "0.7" if name.startswith("blog") else "0.5")
        freq = "weekly" if name in WEEKLY else "monthly"
        urls.append((0 if name == "index.html" else 1, loc, freq, pri, git_date(path)))
    urls.sort()
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for _, loc, freq, pri, mod in urls:
        out += ["  <url>", f"    <loc>{loc}</loc>", f"    <lastmod>{mod}</lastmod>", f"    <changefreq>{freq}</changefreq>", f"    <priority>{pri}</priority>", "  </url>"]
    out.append("</urlset>")
    open(os.path.join(ROOT, "sitemap.xml"), "w").write("\n".join(out) + "\n")
    print(f"sitemap.xml: {len(urls)} pages")


if __name__ == "__main__":
    main()
