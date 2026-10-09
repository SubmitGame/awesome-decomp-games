#!/usr/bin/env python3
"""Classify, filter, rate and merge data/enriched.json (+ data/media.json, data/overrides.json) into data/games.json."""
import json, re, os, math, time, hashlib
from datetime import datetime, timezone
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
def load(p, default):
    try: return json.load(open(D(p)))
    except FileNotFoundError: return default

TOPICS = {
 "static-recomp":  ("Static recompilations", "Console/PC binaries statically recompiled to native code (N64Recomp, XenonRecomp, ReXGlue, ps1/ps2 recomp, ...)."),
 "source-port":    ("Source ports", "Native PC/handheld ports built on top of a decompilation or released source code."),
 "engine-remake":  ("Engine remakes & reimplementations", "Clean-room or reverse-engineered reimplementations of a game's engine; usually need the original assets."),
 "browser-port":   ("Browser ports", "Games that run in a browser tab (WebAssembly / JS ports)."),
 "decompilation":  ("Decompilations", "Source-code reconstructions (matching or functional) of the original game binary."),
 "disassembly":    ("Disassemblies", "Annotated assembly that rebuilds the original ROM, mostly 8/16-bit games."),
 "tool":           ("Tools & launchers", "Recompilers, launchers and helpers around these projects."),
}
ORDER = list(TOPICS)

PLAT_GUESS = [(r"\bn64\b|nintendo ?64|majora|ocarina", "N64"), (r"gamecube|\bgcn?\b|dolphin", "GameCube"),
 (r"\bwii ?u\b", "Wii U"), (r"\bwii\b", "Wii"), (r"\b3ds\b", "3DS"), (r"\bnds\b|nintendo ds", "DS"), (r"\bgba\b", "GBA"),
 (r"\bgbc\b", "Game Boy Color"), (r"\bsnes\b", "SNES"), (r"\bnes\b|famicom", "NES"), (r"\bps2\b|playstation ?2", "PS2"),
 (r"\bps1\b|\bpsx\b|playstation ?1?\b", "PS1"), (r"\bps3\b", "PS3"), (r"\bpsp\b", "PSP"), (r"xbox ?360|\bx360\b|xenon", "Xbox 360"),
 (r"\bxbox\b", "Xbox"), (r"switch", "Switch"), (r"dreamcast", "Dreamcast"), (r"saturn", "Saturn"), (r"genesis|mega ?drive", "Genesis"),
 (r"\bdos\b", "DOS"), (r"android|\bios\b|mobile|j2me", "Mobile"), (r"windows|\bpc\b|win32|directx", "PC")]

def classify(r, text, tu):
    h = set(r.get("hints", []))
    if "tool" in h: return "tool"
    if "browser" in h: return "browser-port"
    if re.search(r"recomp|recompil|xenonrecomp|n64recomp|rexglue", tu): return "static-recomp"
    if re.search(r"\b(wasm|webassembly|emscripten|browser|web ?port|javascript port)\b", tu): return "browser-port"
    if re.search(r"(\bport\b|-port\b|_port\b|\bpc-?port)", tu): return "source-port"
    if "remake" in h or re.search(r"re-?implement|remake|open[- ]?source engine|engine (re)?creation|recreation of the engine|reverse[- ]engineered engine|game engine re", text): return "engine-remake"
    if re.search(r"disassembl|disasm|\bdis\b|_dis\b", text): return "disassembly"
    if re.search(r"recomp|recompil", text): return "static-recomp"
    if "decomp" in h or re.search(r"decomp|decompil|matching", text): return "decompilation"
    if "port" in h or re.search(r"\bport(ed)?\b|source port", text): return "source-port"
    if "recomp" in h: return "static-recomp"
    return "decompilation"

def years_since(iso):
    if not iso: return None
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days / 365.25

def rate(e):
    stars, age, prog, typ = e["stars"] or 0, years_since(e["last_commit"]), e.get("progress"), e["type"]
    rel = e.get("releases") or 0
    # activity
    if e.get("archived"): act = 1
    elif age is None: act = 3 if typ == "browser-port" and e["link_ok"] else 2
    else: act = 5 if age < 0.25 else 4 if age < 1 else 3 if age < 2 else 2 if age < 4 else 1
    # popularity
    pop = 5 if stars >= 5000 else 4 if stars >= 1000 else 3 if stars >= 200 else 2 if stars >= 30 else 1
    if typ == "browser-port" and not e.get("repo"): pop = 3
    desc = (e.get("description") or "").lower()
    # completeness
    if prog is not None:
        comp = 5 if prog >= 99 else 4 if prog >= 75 else 3 if prog >= 40 else 2 if prog >= 10 else 1
    elif re.search(r"\b(100%|fully (matching|decompiled|playable)|complete[ds]?\b|finished)", desc) and "incomplete" not in desc:
        comp = 5 if rel or stars >= 300 else 4
    elif rel >= 5 or (rel and stars >= 500): comp = 4
    elif rel: comp = 3
    elif typ == "browser-port" and e["link_ok"]: comp = 4
    elif stars >= 1000: comp = 4
    elif stars >= 200: comp = 3
    else: comp = 2
    if re.search(r"\b(wip|work in progress|early|incomplete|not (yet )?playable|in progress)\b", desc): comp = min(comp, 3)
    # playability (can an end user actually play it?)
    if typ == "browser-port": play = 5 if e["link_ok"] and e.get("play_status") in (None, "ok") else 1
    elif typ in ("static-recomp", "source-port", "engine-remake"):
        if rel and (rel >= 3 or stars >= 1000): play = 5
        elif rel: play = 4
        elif stars >= 1000: play = 4
        elif stars >= 100: play = 3
        else: play = 2
    elif typ == "decompilation":
        if prog is not None: play = 3 if prog >= 99 else 2 if prog >= 50 else 1
        elif rel and stars >= 200: play = 4
        elif comp >= 4: play = 3
        else: play = 2
    elif typ == "disassembly": play = 3
    else: play = 1
    if re.search(r"\b(not (yet )?playable|non-?playable)\b", desc): play = min(play, 2)
    score = round(0.35 * play + 0.25 * comp + 0.2 * act + 0.2 * pop, 2)
    if e.get("ai_flag"): score = round(score - 0.2, 2)
    return {"playability": play, "completeness": comp, "activity": act, "popularity": pop}, score

def main():
    recs = load("data/enriched.json", [])
    media = load("data/media.json", {})
    over = load("data/overrides.json", {"exclude": [], "set": {}})
    out, seen, dropped = [], {}, []
    nk = lambda u: re.sub(r"^https?://(www\.)?", "", (u or "").lower()).rstrip("/")
    excl = {nk(k) for k in over.get("exclude", [])}
    bstatus = load("data/browser_status.json", {})
    oset = {nk(k): v for k, v in over.get("set", {}).items()}
    for r in recs:
        g = r.get("github") or {}
        ok = 200 <= (r.get("link_status") or 0) < 400 or (r.get("link_status") in (401, 403, 429) and not r.get("github"))  # bot-protected pages count as alive
        if r.get("play_url"): ok = ok or 200 <= r.get("links_checked", {}).get("play_url", 0) < 400
        url = g.get("repo") and f"https://github.com/{g['repo']}" or r["url"]
        if re.search(r"/tree/", r["url"]): url = r["url"]  # monorepo sub-folder entries
        key = url.lower()
        if not ok: dropped.append({"title": r["title"], "url": r["url"], "status": r.get("link_status"), "reason": "dead link"}); continue
        if nk(key) in excl or nk(r["url"]) in excl: continue
        srcs = r["sources"]
        stars = g.get("stars", 0) if g else 0
        only_fyi = srcs == ["recomp.fyi"]
        if only_fyi and (stars < 10 or g.get("fork")):
            dropped.append({"title": r["title"], "url": url, "status": r.get("link_status"), "reason": "recomp.fyi-only, <10 stars or fork"}); continue
        if srcs == ["awesome-game-remakes"] and (stars or 0) < 20:
            dropped.append({"title": r["title"], "url": url, "status": r.get("link_status"), "reason": "awesome-game-remakes-only, <20 stars"}); continue
        if key in seen:  # canonical-URL dedupe (renamed repos)
            prev = seen[key]
            prev["sources"] = sorted(set(prev["sources"]) | set(srcs)); continue
        desc = (g.get("description") or r.get("description") or "").strip()
        text = " ".join([r["title"], url, desc, " ".join(g.get("topics", [])), r.get("description", "")]).lower()
        tu = " ".join([r["title"], url]).lower()
        e = {
         "id": re.sub(r"[^a-z0-9]+", "-", (g.get("repo") or r["title"]).lower()).strip("-"),
         "title": r["title"], "game_key": r["game_key"], "platform": r.get("platform") or "",
         "type": "", "url": url, "repo": g.get("repo"), "description": desc[:300],
         "stars": g.get("stars") if g else None, "forks": g.get("forks") if g else None,
         "last_commit": g.get("last_commit") if g else None, "archived": g.get("archived", False),
         "license": g.get("license"), "release": g.get("release"), "release_date": g.get("release_date"),
         "release_url": g.get("release_url"), "releases": g.get("releases", 0),
         "homepage": g.get("homepage") or None, "og_image": g.get("og_image"), "thumb_src": r.get("thumb_src"),
         "progress": r.get("progress"), "progress_functions": r.get("progress_functions"), "decompdev_url": r.get("decompdev_url"),
         "play_url": r.get("play_url"), "info_url": r.get("info_url"), "needs_assets": r.get("assets"),
         "multiplayer": r.get("multiplayer"), "ai_flag": r.get("ai_flag", False),
         "sources": sorted(srcs), "link_status": r.get("link_status"), "link_ok": ok, "checked_at": r.get("checked_at"),
        }
        e["type"] = classify(r, text, tu)
        if not e["platform"]:
            for pat, p in PLAT_GUESS:
                if re.search(pat, text): e["platform"] = p; break
        ov = oset.get(nk(e["url"])) or oset.get(nk(r["url"])) or {}
        e.update(ov)
        if "title" in ov and "game_key" not in ov:
            e["game_key"] = re.sub(r"[^a-z0-9]+", "", re.sub(r"\(.*?\)", "", e["title"].lower()))
        bst = bstatus.get(e.get("play_url") or "", {})
        e["play_status"] = None if not e.get("play_url") else ("ok" if bst.get("ok", True) else (bst.get("reason") or "not working"))
        e["ratings"], e["score"] = rate(e)
        m = media.get(e["url"], {})
        e["screenshot"] = m.get("screenshot"); e["video"] = m.get("video")
        e["screenshot_score"] = int(m.get("screenshot_score") or (3 if e["screenshot"] else 0))
        e["note"] = m.get("note")
        pst = r.get("links_checked", {}).get("play_url", r.get("link_status") or 0)
        e["browser_playable"] = bool(e.get("play_url")) and (200 <= pst < 400 or pst in (401, 403, 429)) and bst.get("ok", True)
        seen[key] = e; out.append(e)
    # top playable picks: pinned ranks from data/media.json first, then fill by score (one per game)
    picks, games = [], set()
    pinned = sorted([e for e in out if isinstance(media.get(e["url"], {}).get("top_pick"), int)], key=lambda e: media[e["url"]]["top_pick"])
    for e in pinned:
        if e["game_key"] not in games: picks.append(e); games.add(e["game_key"])
    for e in sorted([e for e in out if e["ratings"]["playability"] >= 4 and e["link_ok"]], key=lambda e: -e["score"]):
        if len(picks) >= max(12, len(pinned)): break
        if e["game_key"] not in games: picks.append(e); games.add(e["game_key"])
    for i, e in enumerate(picks): e["top_pick"] = i + 1
    for e in out: e.setdefault("top_pick", None)
    out.sort(key=lambda e: (e["top_pick"] is None, e["top_pick"] or 0, ORDER.index(e["type"]), -e["score"], e["title"].lower()))
    doc_browser = sum(1 for e in out if e["browser_playable"])
    counts = {t: sum(1 for e in out if e["type"] == t) for t in ORDER}
    doc = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "total": len(out), "browser_playable": doc_browser, "unique_games": len({e["game_key"] for e in out}), "counts": counts,
           "topics": {k: {"name": v[0], "description": v[1]} for k, v in TOPICS.items()},
           "sources": SOURCES, "games": out}
    json.dump(doc, open(D("data/games.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(dropped, open(D("data/dropped.json"), "w"), indent=1, ensure_ascii=False)
    print(f"games: {len(out)} (unique titles {doc['unique_games']}), dropped {len(dropped)}; counts {counts}")

SOURCES = [
 {"name": "SamidyFR/Game-Decompilations", "url": "https://github.com/SamidyFR/Game-Decompilations"},
 {"name": "CharlotteCross1998/awesome-game-decompilations", "url": "https://github.com/CharlotteCross1998/awesome-game-decompilations"},
 {"name": "decomp.dev", "url": "https://decomp.dev/"},
 {"name": "recompiledgames.com", "url": "https://recompiledgames.com/"},
 {"name": "recomp.fyi (entries with >=10 stars)", "url": "https://recomp.fyi/"},
 {"name": "radek-sprta/awesome-game-remakes", "url": "https://github.com/radek-sprta/awesome-game-remakes"},
 {"name": "X post by @RadiantOpti (browser games list)", "url": "https://x.com/RadiantOpti/status/2108068632991256995"},
 {"name": "BlueInterlude/awesome-recompilations", "url": "https://github.com/BlueInterlude/awesome-recompilations"},
]
if __name__ == "__main__": main()
