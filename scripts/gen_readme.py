#!/usr/bin/env python3
"""Generate README.md from data/games.json. Do not edit README.md by hand."""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
doc = json.load(open(os.path.join(ROOT, "data", "games.json")))
G, T = doc["games"], doc["topics"]
SITE = "https://submitgame.github.io/awesome-decomp-games/"
SING = {"static-recomp": "Static recompilation", "source-port": "Source port", "engine-remake": "Engine remake", "browser-port": "Browser port",
        "decompilation": "Decompilation", "disassembly": "Disassembly", "tool": "Tool"}
def esc(s): return (s or "").replace("|", "\\|").replace("\n", " ").strip()
def stars(n): return "" if n is None else (f"{n/1000:.1f}k" if n >= 1000 else str(n))
def date(s): return (s or "")[:10]
def anchor(name): return re.sub(r"[^a-z0-9 -]", "", name.lower()).replace(" ", "-")
def links(e):
    l = []
    if e.get("play_url"): l.append(f"[play]({e['play_url']})")
    if e.get("release_url"): l.append(f"[release]({e['release_url']})")
    if e.get("decompdev_url"): l.append(f"[progress]({e['decompdev_url']})")
    if e.get("video"): l.append(f"[video]({e['video']})")
    return " · ".join(l)
def title(e):
    t = f"[{esc(e['title'])}]({e['url']})"
    if e.get("ai_flag"): t += " ⚠️"
    if e.get("archived"): t += " 🗄️"
    return t

L = []
L += ["<!-- GENERATED FILE: edit data/ and run scripts/refresh, not this file -->",
"# Awesome Decomp Games [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)", "",
"> A rated, auto-refreshed list of **decompiled, recompiled and reverse-engineered games**: matching decompilations, static recompilations, source ports, engine remakes, disassemblies and browser ports.", "",
f"**{doc['total']} projects** covering **{doc['unique_games']} games** · updated {date(doc['generated_at'])} · browse and filter on the **[website]({SITE})** · data in [`data/games.json`](data/games.json)", "",
"> [!IMPORTANT]",
"> This list only links to source code and project pages. It does **not** host or link to ROMs, ISOs, game assets or other copyrighted material. Most projects need files from a copy of the game you own. See the [disclaimer](#disclaimer).", "",
"## Contents", "", "- [Top playable picks](#top-playable-picks)"]
for k in T:
    if doc["counts"].get(k): L.append(f"- [{T[k]['name']}](#{anchor(T[k]['name'])}) ({doc['counts'][k]})")
L += ["- [How entries are rated](#how-entries-are-rated)", "- [Sources](#sources)", "- [Contributing](#contributing)", "- [Disclaimer](#disclaimer)", "- [License](#license)", ""]

picks = sorted([e for e in G if e.get("top_pick")], key=lambda e: e["top_pick"])
L += ["## Top playable picks", "", "Projects with the best mix of playability, completeness, activity and popularity that you can actually play today (bring your own game files where needed).", ""]
for i, e in enumerate(picks, 1):
    L.append(f"### {i}. {esc(e['title'])}")
    meta = f"**{SING.get(e['type'], e['type'])}** · {e['platform'] or 'n/a'} · ⭐ {stars(e['stars']) or 'n/a'} · score **{e['score']:.1f}/5**"
    L.append(meta + "  ")
    note = e.get("note") or e.get("description") or ""
    if note: L.append(esc(note) + "  ")
    lk = " · ".join(x for x in [f"[project]({e['url']})", links(e)] if x)
    L.append(lk)
    if e.get("screenshot"):
        L += ["", f'<a href="{e["url"]}"><img src="{e["screenshot"]}" width="480" alt="{esc(e["title"])} screenshot"></a>']
    L.append("")

for k in T:
    rows = sorted([e for e in G if e["type"] == k], key=lambda e: (-e["score"], e["title"].lower()))
    if not rows: continue
    L += [f"## {T[k]['name']}", "", T[k]["description"], "",
          "| Game | Platform | Score | ⭐ | Last commit | Progress | Links |", "|---|---|---|---|---|---|---|"]
    for e in rows:
        prog = f"{e['progress']:.1f}%" if e.get("progress") is not None else ""
        L.append(f"| {title(e)} | {esc(e['platform'])} | {e['score']:.1f} | {stars(e['stars'])} | {date(e['last_commit'])} | {prog} | {links(e)} |")
    L.append("")

L += ["## How entries are rated", "",
"Every entry gets four 1-5 sub-scores, computed by [`scripts/build.py`](scripts/build.py) from GitHub metadata and decomp.dev:", "",
"- **Playability**: can an end user play it today? Releases, a working browser link, or a finished decomp score high; early research repos score low.",
"- **Completeness**: decomp.dev matched-code %, release history, and stated status.",
"- **Activity**: age of the last commit (archived repos get 1).",
"- **Popularity**: GitHub stars.", "",
"`score = 0.35·playability + 0.25·completeness + 0.2·activity + 0.2·popularity` (minus 0.2 for projects their source list flags as AI-generated ⚠️). 🗄️ = archived repo. Links are checked on every refresh and dead ones are dropped (see [`data/dropped.json`](data/dropped.json)).", "",
"## Sources", "", "Seeded from, and refreshed against, these lists (thank you to their maintainers):", ""]
for s in doc["sources"]: L.append(f"- [{s['name']}]({s['url']})")
L += ["", "## Contributing", "", "Missing a project, or found a wrong rating? See [CONTRIBUTING.md](CONTRIBUTING.md). Additions go in [`data/additions.json`](data/additions.json), fixes in [`data/overrides.json`](data/overrides.json). README.md and the site are generated.", "",
"## Disclaimer", "",
"This repository is an index of third-party open-source projects. It does **not** distribute ROMs, ISOs, BIOS files, game assets, or any copyrighted game content, and it does not link to sites that do. Projects listed here are made by their own authors, under their own licenses and responsibility; inclusion is not an endorsement or a legal opinion. Most of them need data from a legally obtained copy of the original game. All trademarks and game names belong to their respective owners. If you are a rights holder and want an entry removed, open an issue.", "",
"## License", "", "The list and data are released under [CC0 1.0](LICENSE). The scripts and website code are under the [MIT License](LICENSE-CODE).", ""]
open(os.path.join(ROOT, "README.md"), "w").write("\n".join(L))
print("README.md written:", len("\n".join(L)) // 1024, "KB")
