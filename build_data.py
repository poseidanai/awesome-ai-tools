#!/usr/bin/env python3
"""Live AI Tools Board data (09.11.2026).

Reads tools.tsv (category, repo, description, featured y/n, tags, kind), asks GitHub for the star counts and writes
data.json for the page poseidanai.com/github-trends. Uses the public search API without a token: several
`repo:` qualifiers per query, 10 queries a minute at most. Keeps history.json (one sample per hour, 8 days)
so the page can show the gain of the last 24 hours.

  python3 build_data.py [--out DIR]

A repo GitHub does not return keeps its last known stars (and is reported on stderr), so one bad answer
never empties the board. Exit 2 when no star count at all could be read (cannot-verify, not ok).
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = 30
UA = "poseidanai-tools-board"


def load_rows(path):
    rows = []
    for line in open(path, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 4 and parts[1]:
            rows.append({"category": parts[0], "repo": parts[1], "desc": parts[2], "featured": parts[3] == "y",
                         "tags": (parts[4].split() if len(parts) > 4 else [])[:3],
                         "kind": parts[5].strip() if len(parts) > 5 else ""})
    return rows


def pick(rows):
    """Same rule as gen.py: featured tools always stay, then the list order, 30 per category."""
    out = []
    for cat in ("creative", "marketing", "build"):
        mine = [r for r in rows if r["category"] == cat]
        keep = {r["repo"] for r in mine if r["featured"]}
        for r in mine:
            if len(keep) >= CAP:
                break
            keep.add(r["repo"])
        out += [r for r in mine if r["repo"] in keep]
    return out


def search(repos):
    q = " ".join(f"repo:{r}" for r in repos)
    url = "https://api.github.com/search/repositories?per_page=100&q=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return {i["full_name"].lower(): i for i in data.get("items", [])}


def fetch_all(repos):
    found, chunk = {}, []
    for repo in repos:
        if chunk and len(" ".join(f"repo:{r}" for r in chunk + [repo])) > 240:
            found.update(search(chunk))
            chunk = []
            time.sleep(7)
        chunk.append(repo)
    if chunk:
        found.update(search(chunk))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "site"))
    a = ap.parse_args()
    rows = pick(load_rows(os.path.join(HERE, "tools.tsv")))
    data_path = os.path.join(a.out, "data.json")
    hist_path = os.path.join(a.out, "history.json")
    last = {}
    if os.path.exists(data_path):
        for items in json.load(open(data_path)).get("categories", {}).values():
            last.update({i["repo"]: i for i in items})
    hist = json.load(open(hist_path)) if os.path.exists(hist_path) else []

    try:
        found = fetch_all([r["repo"] for r in rows])
    except Exception as e:  # network or rate limit: keep the old board
        print(f"cannot-verify: GitHub search failed: {e}", file=sys.stderr)
        return 2
    if not found:
        print("cannot-verify: GitHub returned no repos", file=sys.stderr)
        return 2

    now = dt.datetime.now(dt.timezone.utc)
    day_ago = now - dt.timedelta(hours=20)  # daily runs: the previous day sample
    old = None
    for sample in hist:  # the newest sample that is at least 20 h old
        if dt.datetime.fromisoformat(sample["at"]) <= day_ago:
            old = sample
    if old is None:  # a young board (first days): the oldest sample at least 10 h old, so the gain shows from day one
        for sample in hist:
            if dt.datetime.fromisoformat(sample["at"]) <= now - dt.timedelta(hours=10):
                old = sample
                break
    cats = {"creative": [], "marketing": [], "build": []}
    missing = []
    for r in rows:
        g = found.get(r["repo"].lower())
        if g is None:
            missing.append(r["repo"])
            if r["repo"] not in last:
                continue
            stars, lic = last[r["repo"]]["stars"], last[r["repo"]].get("license")
        else:
            stars, lic = g["stargazers_count"], (g.get("license") or {}).get("spdx_id")
        item = {"repo": r["repo"], "desc": r["desc"], "stars": stars, "license": lic, "featured": r["featured"]}
        if r["tags"]:
            item["tags"] = r["tags"]
        if r["kind"]:
            item["kind"] = r["kind"]
        if old and r["repo"] in old["stars"]:
            item["stars_24h"] = old["stars"][r["repo"]]
        cats[r["category"]].append(item)
    for v in cats.values():
        v.sort(key=lambda i: -i["stars"])
    # trend: one sample per day (the newest of each day), last 7 days, then today
    per_day = {}
    for sample in hist:
        per_day[sample["at"][:10]] = sample
    days = [per_day[d] for d in sorted(per_day) if d < now.date().isoformat()][-6:]
    if len(days) < 2:  # under 3 days of history: one point per hour from all samples, so the line shows from day one
        per_hour = {}
        for sample in hist:
            per_hour[sample["at"][:13]] = sample
        days = [per_hour[h] for h in sorted(per_hour)][-12:]
    for v in cats.values():
        for i in v:
            t = [d["stars"][i["repo"]] for d in days if i["repo"] in d["stars"]] + [i["stars"]]
            if len(t) >= 3:
                i["trend"] = t

    os.makedirs(a.out, exist_ok=True)
    tmp = data_path + ".tmp"
    json.dump({"updated": now.isoformat(timespec="seconds"), "categories": cats}, open(tmp, "w"), separators=(",", ":"))
    os.replace(tmp, data_path)
    hist.append({"at": now.isoformat(timespec="seconds"), "stars": {i["repo"]: i["stars"] for v in cats.values() for i in v}})
    hist = [s for s in hist if dt.datetime.fromisoformat(s["at"]) > now - dt.timedelta(days=8)]
    json.dump(hist, open(hist_path, "w"), separators=(",", ":"))
    total = sum(len(v) for v in cats.values())
    print(f"tools-board ok: {total} tools ({', '.join(f'{k} {len(v)}' for k, v in cats.items())}), missing {len(missing)}"
          + (f": {' '.join(missing)}" if missing else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
