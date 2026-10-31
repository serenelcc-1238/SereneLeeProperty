#!/usr/bin/env python3
"""
Average HDB resale price per block and per street, by flat type, for the last
3 months in the site's HDB data (data/hdb/<town>.json). Also each block's lease
start year. Writes data/hdb-block-resale.json for the private agent app
(/agent, block facts panel). Runs at every deploy. Standard library only.
"""
import glob, json, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def main():
    hdb = json.load(open(os.path.join(ROOT, "market-data.json")))["hdb"]
    last = hdb["last_month"]
    y, m = int(last[:4]), int(last[5:])
    months = []
    for i in range(3):
        mm, yy = m - i, y
        while mm <= 0:
            mm += 12
            yy -= 1
        months.append(f"{yy:04d}-{mm:02d}")
    months.sort()
    want = set(months)
    blk, st, lease = {}, {}, {}
    for p in glob.glob(os.path.join(ROOT, "hdb", "*.json")):
        f = json.load(open(p))
        for s, bl in (f.get("streets") or {}).items():
            for b, rows in bl.items():
                k = s + "|" + b
                if rows:
                    lease[k] = rows[0][5]
                for r in rows:
                    if r[0] not in want:
                        continue
                    psf = r[6] / (r[3] * 10.7639)
                    for d, key in ((blk, k), (st, s)):
                        a = d.setdefault(key, {}).setdefault(r[1], [0, 0, 0])
                        a[0] += 1; a[1] += r[6]; a[2] += psf
    fin = lambda d: {k: {t: [a[0], round(a[1] / a[0]), round(a[2] / a[0])] for t, a in v.items()} for k, v in d.items()}
    out = {"months": months, "asOf": (hdb.get("fetched") or "")[:10], "blk": fin(blk), "st": fin(st), "lease": lease}
    with open(os.path.join(ROOT, "hdb-block-resale.json"), "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print("block resale:", months, len(out["blk"]), "blocks")


if __name__ == "__main__":
    main()
