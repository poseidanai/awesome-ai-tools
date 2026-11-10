#!/usr/bin/env python3
"""Hover previews for the Live AI Tools Board (09.11.2026).

For every tool on the board takes the first real picture, GIF or video from its README and keeps a copy
next to the page (media/<slug>.<ext>), because the site only shows pictures from its own address.
Badges, logos and icons are skipped (svg, shields, files under 20 KB). No picture in the README:
GitHub's own card for the repo. Writes media.json {repo: {"src": "media/x.gif", "kind": "img"|"video"}}.

  python3 fetch_media.py [--out DIR] [--refresh]

Already fetched repos are kept unless --refresh. One failed repo never stops the rest.
"""
import argparse
import json
import os
import re
import time
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
UA = "poseidanai-tools-board"
MAX = {"img": 3_500_000, "video": 7_000_000}
MIN = 20_000
SKIP = re.compile(r"shields\.io|badge|star-history|contrib\.rocks|api\.star|trendshift|producthunt|"
                  r"buymeacoffee|ko-fi|discord|twitter|x\.com|\.svg(\?|$)|logo|icon|avatar|sponsor", re.I)
EXT = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp", "video/mp4": "mp4",
       "video/webm": "webm", "video/quicktime": "mov"}


def get(url, limit=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        ctype = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
        body = r.read((limit or 10_000_000) + 1)
    return ctype, body


def readme(repo):
    for name in ("README.md", "readme.md", "Readme.md", "README.MD"):
        try:
            return get(f"https://raw.githubusercontent.com/{repo}/HEAD/{name}")[1].decode("utf-8", "replace")
        except Exception:
            continue
    return ""


def candidates(repo, text):
    found = re.findall(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)", text)
    found += re.findall(r"<(?:img|source|video)[^>]+src=[\"']([^\"']+)", text, re.I)
    found += re.findall(r"(https://github\.com/user-attachments/assets/[0-9a-f-]+)", text)
    found += re.findall(r"(https://github\.com/[^/\s]+/[^/\s]+/assets/\d+/[0-9a-f-]+)", text)
    pos = {u: text.find(u) for u in found}
    out = []
    for u in sorted(set(found), key=lambda u: pos[u]):
        if SKIP.search(u):
            continue
        if not u.startswith("http"):
            u = f"https://raw.githubusercontent.com/{repo}/HEAD/" + u.lstrip("./")
        u = re.sub(r"https://github\.com/([^/]+/[^/]+)/(?:blob|raw)/", r"https://raw.githubusercontent.com/\1/", u)
        out.append(u)
    return out[:6]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "site"))
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    data = json.load(open(os.path.join(a.out, "data.json")))
    repos = [i["repo"] for v in data["categories"].values() for i in v]
    mdir = os.path.join(a.out, "media")
    os.makedirs(mdir, exist_ok=True)
    mpath = os.path.join(a.out, "media.json")
    media = json.load(open(mpath)) if os.path.exists(mpath) else {}
    got = card = failed = 0
    for n, repo in enumerate(repos):
        old = media.get(repo)
        if old and not a.refresh and os.path.exists(os.path.join(a.out, old["src"])):
            continue
        time.sleep(1.5) if n else None
        slug = re.sub(r"[^a-z0-9]+", "-", repo.lower()).strip("-")
        pick = None
        try:
            for url in candidates(repo, readme(repo)):
                try:
                    ctype, body = get(url, max(MAX.values()))
                except Exception:
                    continue
                ext = EXT.get(ctype)
                kind = "video" if ctype.startswith("video/") else "img"
                if not ext or len(body) < MIN or len(body) > MAX[kind]:
                    continue
                pick = (body, ext, kind)
                break
            if not pick:
                ctype, body = get(f"https://opengraph.githubassets.com/1/{repo}")
                pick = (body, EXT.get(ctype, "png"), "img")
                card += 1
            else:
                got += 1
        except Exception as e:
            print(f"media: {repo}: {e}", file=sys.stderr)
            failed += 1
            continue
        body, ext, kind = pick
        for f in os.listdir(mdir):
            if f.startswith(slug + "."):
                os.remove(os.path.join(mdir, f))
        open(os.path.join(mdir, f"{slug}.{ext}"), "wb").write(body)
        media[repo] = {"src": f"media/{slug}.{ext}", "kind": kind}
    json.dump(media, open(mpath, "w"), separators=(",", ":"))
    print(f"tools-media ok: {len(media)} of {len(repos)} have a preview (new from README {got}, GitHub card {card}, failed {failed})")
    return 0 if media else 2


if __name__ == "__main__":
    sys.exit(main())
