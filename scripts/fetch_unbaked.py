#!/usr/bin/env python3
"""Fetch the public unbaked.games registry (https://unbaked.games/api, documented in /llms.txt) -> raw/unbaked.json.
Reads /api/games.json, then /api/games/{slug}.json for games whose best project has 10+ stars, and keeps only
GitHub projects that are game decomps/recomps/reimplementations/ports/disassemblies. Skips general tools,
multi-game emulators/engines (covers_games), reimplementation-only projects (clones, servers, fan games), unvetted submissions, archive-only methods (readable bytecode,
agent environment, RE candidate, plain source release, native port) and slugs in overrides.json "unbaked_exclude".
Stars here are unbaked's own numbers and only pre-filter; build.py re-applies the 10-star bar on live GitHub data."""
import json, os, re, time, requests
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://unbaked.games/api"
UA = {"User-Agent": "awesome-decomp-games-refresh (+https://github.com/SubmitGame/awesome-decomp-games)"}
KEEP = {"Matching decomp": "decomp", "Decomp": "decomp", "AI-assisted decomp": "decomp", "Static recomp": "recomp",
        "Reimplementation": "remake", "Source port": "port", "Disassembly": "disasm"}
BAD = re.compile(r"\b(emulator|emu|launcher|toolkit|rom ?hack|romhack|iso|roms?)\b", re.I)
def main():
    over = json.load(open(os.path.join(ROOT, "data", "overrides.json")))
    skip = set(over.get("unbaked_exclude", []))
    s = requests.Session(); s.headers.update(UA)
    games = s.get(API + "/games.json", timeout=60).json()["games"]
    cand = [g for g in games if g.get("has_public_code") and (g.get("stars") or 0) >= 10 and g["slug"] not in skip
            and set(g.get("methods", [])) & set(KEEP)]
    out, fails = [], 0
    for g in cand:
        try:
            d = s.get(f"{API}/games/{g['slug']}.json", timeout=30).json()
        except Exception as ex:
            fails += 1; print("WARN detail", g["slug"], ex); continue
        for p in d.get("projects", []):
            u = (p.get("url") or "").rstrip("/")
            if not re.match(r"https://github\.com/[^/]+/[^/]+", u): continue
            if p.get("general_tool") or p.get("covers_games") or p.get("new_unvetted") or p.get("archived"): continue
            if (p.get("stars") or 0) < 10: continue
            ms = [m for m in p.get("methods", []) if m in KEEP]
            if not ms or ms == ["Reimplementation"]: continue  # reimplementation-only = mostly clones/servers/fan games
            if BAD.search(f"{p.get('name','')} {p.get('description') or ''}"): continue
            out.append({"slug": g["slug"], "game": d.get("title") or g["title"], "name": p.get("name"), "url": u,
                        "platform": d.get("platform") or g.get("platform") or "", "hint": KEEP[ms[0]], "methods": p.get("methods", []),
                        "ai": "AI-assisted decomp" in p.get("methods", []), "description": p.get("description") or "",
                        "unbaked_url": d.get("url") or g.get("url")})
        time.sleep(0.1)
    if fails > len(cand) // 4: raise SystemExit(f"too many detail failures ({fails}); keeping previous raw/unbaked.json")
    os.makedirs(os.path.join(ROOT, "raw"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "raw", "unbaked.json"), "w"), indent=1, ensure_ascii=False)
    print(f"unbaked: {len(games)} games, {len(cand)} candidates, {len(out)} github projects kept")
if __name__ == "__main__": main()
