#!/usr/bin/env python3
"""
Instagram feed for sereneleeproperty.com, from Buffer.

Reads the Instagram posts Buffer has published for Serene (@serene.leecc),
keeps feed posts and reels that were scheduled through Buffer (via "buffer";
not stories, not posts made directly in the Instagram app), saves each post's
image into assets/ig/feed/<post id>.jpg and writes data/instagram.json
(newest first) for the homepage "On Instagram" section.

Needs the repo secret BUFFER_API_KEY (from https://publish.buffer.com/settings/api).
Without it, only images still missing for posts already in data/instagram.json
are downloaded, and the script exits 3 so the workflow flags it.
Standard library only.
"""
import json, os, sys, time, urllib.request

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
API = "https://api.buffer.com"
ORG = "6ab3b5877214dd7a8a3a58a4"
CHANNEL = "6ab3d158ea19ca0bdec53ba7"   # Instagram @serene.leecc
KEEP = 24
UA = "Mozilla/5.0 (compatible; sereneleeproperty-site/1.0)"
QUERY = """query P($org: OrganizationId!, $after: String) {
  posts(first: 50, after: $after, input: { organizationId: $org,
        filter: { channelIds: ["%s"], status: [sent] }, sort: [{ field: dueAt, direction: desc }] }) {
    edges { node { id text sentAt via externalLink assets { source thumbnail mimeType } } }
    pageInfo { hasNextPage endCursor } } }""" % CHANNEL
OUT = os.path.join(ROOT, "data/instagram.json")
IMG_DIR = os.path.join(ROOT, "assets/ig/feed")


def gql(key, variables):
    body = json.dumps({"query": QUERY, "variables": variables}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    if d.get("errors"):
        raise RuntimeError(d["errors"])
    return d["data"]["posts"]


def fetch_posts(key):
    out, after = [], None
    for _ in range(4):
        page = gql(key, {"org": ORG, "after": after})
        out += [e["node"] for e in page["edges"]]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    return out


def keep(p):
    link = p.get("externalLink") or ""
    return p.get("via") == "buffer" and ("/p/" in link or "/reel/" in link) and p.get("assets")


def caption(text):
    lines = [l.strip() for l in (text or "").split("\n") if l.strip() and not l.strip().startswith("#")]
    return lines[0][:160] if lines else ""


def download(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return True
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if len(data) < 1000:
                raise RuntimeError("too small")
            with open(path, "wb") as f:
                f.write(data)
            return True
        except Exception as e:  # noqa: BLE001
            print(f"  image {url[:80]}… attempt {attempt + 1} failed: {e}")
            time.sleep(3)
    return False


def main():
    os.makedirs(IMG_DIR, exist_ok=True)
    key = os.environ.get("BUFFER_API_KEY", "").strip()
    old = json.load(open(OUT)) if os.path.exists(OUT) else {"posts": []}
    if key:
        posts = [p for p in fetch_posts(key) if keep(p)][:KEEP]
        items = []
        for p in posts:
            a = p["assets"][0]
            items.append({"id": p["id"], "url": p["externalLink"], "caption": caption(p["text"]),
                          "sentAt": p["sentAt"], "src": a.get("thumbnail") or a.get("source"),
                          "type": "reel" if "/reel/" in p["externalLink"] else "post"})
        print(f"  {len(items)} Buffer-scheduled Instagram posts")
    else:
        print("BUFFER_API_KEY not set: only downloading missing images for the existing list.")
        items = old.get("posts", [])
    for it in items:
        path = os.path.join(IMG_DIR, it["id"] + ".jpg")
        it["img"] = "assets/ig/feed/" + it["id"] + ".jpg" if download(it["src"], path) else it.get("img", "")
    items = [it for it in items if it.get("img")]
    for f in os.listdir(IMG_DIR):          # drop images no longer listed
        if f.endswith(".jpg") and f[:-4] not in {it["id"] for it in items}:
            os.remove(os.path.join(IMG_DIR, f))
    with open(OUT, "w") as f:
        json.dump({"account": "serene.leecc", "profile": "https://www.instagram.com/serene.leecc/",
                   "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "posts": items}, f, indent=1, ensure_ascii=False)
    print(f"Wrote {len(items)} posts to data/instagram.json")
    if not key:
        sys.exit(3)


if __name__ == "__main__":
    main()
