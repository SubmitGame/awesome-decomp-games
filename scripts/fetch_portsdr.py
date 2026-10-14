#!/usr/bin/env python3
"""Scrape the portsdr.com homepage port cards (no API) -> raw/portsdr.json.
Keeps one GitHub repo per card (the "Repository" link, normalised to https://github.com/owner/repo),
drops non-GitHub links, release-tag duplicates, launchers, and Android-only forks of games that already have
a desktop card. data-ai-assisted -> ai flag. build.py applies the 10-star bar on live GitHub data."""
import html, json, os, re, requests
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "awesome-decomp-games-refresh (+https://github.com/SubmitGame/awesome-decomp-games)"}
T = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()
def norm(u):
    m = re.match(r"https?://(?:www\.)?github\.com/([^/\s#?]+)/([^/\s#?]+)", u or "")
    return m and f"https://github.com/{m.group(1)}/{re.sub(r'\.git$', '', m.group(2))}"
def main():
    h = requests.get("https://portsdr.com/", headers=UA, timeout=60); h.raise_for_status()
    cards = []
    for attrs, body in re.findall(r'<article class="port-card"([^>]*)>(.*?)</article>', h.text, re.S):
        a = dict(re.findall(r'data-([a-z-]+)="([^"]*)"', attrs))
        game = T((re.search(r"<h3>(.*?)</h3>", body, re.S) or [None, ""])[1])
        proj = T((re.search(r'class="project-name">(.*?)</p>', body, re.S) or [None, ""])[1])
        links = re.findall(r'<a href="([^"]+)"[^>]*>([^<]*)</a>', body)
        repo = next((norm(u) for u, t in links if t.strip().lower() == "repository" and norm(u)), None)
        if not repo: continue  # non-GitHub or missing repository
        plats = [p for p in html.unescape(a.get("platforms", "")).split("|") if p]
        cards.append({"game": game, "project": proj, "url": repo, "platform": html.unescape(a.get("original-platform", "")),
                      "platforms": plats, "ai": a.get("ai-assisted") == "true", "updated_at": a.get("updated-at")})
    desktop = {c["game"].lower() for c in cards if set(c["platforms"]) - {"Android"}}
    out, seen = [], set()
    for c in cards:
        k = c["url"].lower()
        if k in seen: continue  # release-tag / duplicate cards
        if re.search(r"launcher", f'{c["project"]} {c["url"]}', re.I): continue
        if c["platforms"] == ["Android"] and (c["game"].lower() in desktop or "android" in c["url"].lower()): continue
        seen.add(k); out.append(c)
    os.makedirs(os.path.join(ROOT, "raw"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "raw", "portsdr.json"), "w"), indent=1, ensure_ascii=False)
    print(f"portsdr: {len(cards)} cards with github repo, {len(out)} kept")
if __name__ == "__main__": main()
