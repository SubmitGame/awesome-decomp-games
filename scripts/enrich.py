#!/usr/bin/env python3
"""Enrich data/collected.json -> data/enriched.json.
GitHub stars / last commit / release / archive state via batched `gh api graphql`,
decomp.dev progress (already merged in collect), and HTTP link checks for non-GitHub URLs."""
import json, re, os, subprocess, sys, time, concurrent.futures as cf
import requests
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GH = re.compile(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/#?]+)", re.I)
UA = {"User-Agent": "awesome-decomp-games-linkcheck/1.0 (+https://github.com/SubmitGame/awesome-decomp-games)"}

FIELDS = """nameWithOwner url stargazerCount forkCount isArchived isFork isDisabled pushedAt description homepageUrl
 openGraphImageUrl usesCustomOpenGraphImage licenseInfo{spdxId}
 repositoryTopics(first:10){nodes{topic{name}}}
 latestRelease{tagName publishedAt url}
 releases{totalCount}
 defaultBranchRef{target{... on Commit{committedDate}}}"""

def gql(q):
    for attempt in range(4):
        p = subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], capture_output=True, text=True)
        try:
            out = json.loads(p.stdout)
            if "data" in out: return out["data"] or {}
        except Exception:
            pass
        err = (p.stdout + p.stderr).lower()
        print("  graphql retry:", err.strip()[:160].replace("\n", " "), file=sys.stderr)
        if "rate limit" in err: time.sleep(60)
        elif "parse error" in err or "syntax" in err: return None
        else: time.sleep(3 * (attempt + 1))
    print("graphql failed:", p.stderr[:300], p.stdout[:300], file=sys.stderr)
    return None

def _query(chunk):
    parts = [f'r{j}: repository(owner:{json.dumps(o)}, name:{json.dumps(n)}){{{FIELDS}}}' for j, (o, n) in enumerate(chunk)]
    return gql("query{" + "\n".join(parts) + " rateLimit{remaining}}")

def _fetch(chunk, res):
    data = _query(chunk)
    if data is None:
        if len(chunk) == 1:
            res[(chunk[0][0].lower(), chunk[0][1].lower())] = None; return
        mid = len(chunk) // 2  # bisect to isolate a bad query
        _fetch(chunk[:mid], res); _fetch(chunk[mid:], res); return
    for j, (o, n) in enumerate(chunk):
        res[(o.lower(), n.lower())] = data.get(f"r{j}")

def fetch_github(pairs, batch=30):
    res = {}
    pairs = [p for p in pairs if re.fullmatch(r"[A-Za-z0-9_.-]+", p[0]) and re.fullmatch(r"[A-Za-z0-9_.-]+", p[1])]
    with cf.ThreadPoolExecutor(3) as ex:
        list(ex.map(lambda i: _fetch(pairs[i:i + batch], res), range(0, len(pairs), batch)))
    print(f"  github fetched {len(res)}", file=sys.stderr)
    return res

BROWSER_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}

def check_url(u):
    """Return (status, working_url). Falls back to https:// for plain-http links."""
    st = _check(u)
    if (st == 0 or st >= 400) and u.startswith("http://"):
        u2 = "https://" + u[len("http://"):]
        st2 = _check(u2)
        if 200 <= st2 < 400: return st2, u2
    return st, u

def _check(u):
    try:
        r = requests.head(u, headers=UA, timeout=15, allow_redirects=True)
        if r.status_code in (403, 405, 400, 404, 429, 501) or r.status_code >= 500:
            r = requests.get(u, headers=BROWSER_UA, timeout=25, allow_redirects=True, stream=True); r.close()
        return r.status_code
    except Exception as e:
        return 0

def main():
    recs = json.load(open(os.path.join(ROOT, "data", "collected.json")))
    pairs = {}
    for r in recs:
        m = GH.match(r["url"])
        if m:
            o, n = m.group(1), re.sub(r"\.git$", "", m.group(2))
            r["_gh"] = (o.lower(), n.lower()); pairs[(o.lower(), n.lower())] = (o, n)
    print(f"querying {len(pairs)} GitHub repos", file=sys.stderr)
    info = fetch_github(pairs.values())
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    urls = set()
    for r in recs:
        if "_gh" in r:
            g = info.get(r.pop("_gh"))
            if g:
                br = (g.get("defaultBranchRef") or {}).get("target") or {}
                rel = g.get("latestRelease") or {}
                r["github"] = {
                    "repo": g["nameWithOwner"], "stars": g["stargazerCount"], "forks": g["forkCount"],
                    "archived": g["isArchived"], "fork": g["isFork"], "pushed_at": g["pushedAt"],
                    "last_commit": br.get("committedDate") or g["pushedAt"], "description": g.get("description") or "",
                    "homepage": g.get("homepageUrl") or "", "license": (g.get("licenseInfo") or {}).get("spdxId"),
                    "topics": [t["topic"]["name"] for t in (g.get("repositoryTopics") or {}).get("nodes", [])],
                    "release": rel.get("tagName"), "release_date": rel.get("publishedAt"), "release_url": rel.get("url"),
                    "releases": (g.get("releases") or {}).get("totalCount", 0),
                    "og_image": g["openGraphImageUrl"] if g.get("usesCustomOpenGraphImage") else None,
                }
                r["link_status"] = 200 if not g.get("isDisabled") else 451
            else:
                r["github"] = None; r["link_status"] = 404
        else:
            urls.add(r["url"])
        for k in ("play_url", "info_url", "decompdev_url"):
            if r.get(k): urls.add(r[k])
        if r.get("github", {}) and r["github"].get("homepage", "").startswith("http"): pass
    print(f"link-checking {len(urls)} non-GitHub URLs", file=sys.stderr)
    with cf.ThreadPoolExecutor(24) as ex:
        status = dict(zip(urls, ex.map(check_url, urls)))
    def apply(r, k):
        st, u2 = status.get(r[k], (0, r[k]))
        r[k] = u2
        return st
    for r in recs:
        checked = {k: apply(r, k) for k in ("play_url", "info_url", "decompdev_url") if r.get(k) in status}
        if "github" not in r: r["link_status"] = apply(r, "url")
        r["links_checked"] = checked
        r["checked_at"] = now
    json.dump(recs, open(os.path.join(ROOT, "data", "enriched.json"), "w"), indent=1, ensure_ascii=False)
    dead = sum(1 for r in recs if not (200 <= (r["link_status"] or 0) < 400))
    print(f"enriched {len(recs)} records; dead/unreachable main links: {dead}", file=sys.stderr)

if __name__ == "__main__": main()
