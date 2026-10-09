#!/usr/bin/env python3
"""Parse raw source lists (raw/) into data/collected.json: one record per project URL, deduped."""
import json, re, html, os, sys
from urllib.parse import unquote
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")

PLAT = {
 "n64":"N64","nintendo 64":"N64","gc":"GameCube","gamecube":"GameCube","nintendo gamecube":"GameCube",
 "wii":"Wii","nintendo wii":"Wii","wiiu":"Wii U","wii u":"Wii U","nds":"DS","nintendo ds":"DS","ds":"DS",
 "3ds":"3DS","nintendo 3ds":"3DS","switch":"Switch","nintendo switch":"Switch","gba":"GBA",
 "gameboy advance":"GBA","game boy advance":"GBA","gb":"Game Boy","gameboy":"Game Boy","game boy":"Game Boy",
 "gbc":"Game Boy Color","gameboy colour":"Game Boy Color","game boy color":"Game Boy Color",
 "nes":"NES","nes / famicom":"NES","snes":"SNES","snes / super famicom":"SNES","super nintendo":"SNES",
 "ps1":"PS1","psx":"PS1","playstation":"PS1","playstation 1":"PS1","ps2":"PS2","playstation 2":"PS2",
 "ps3":"PS3","playstation 3":"PS3","ps4":"PS4","psp":"PSP","vita":"PS Vita","ps vita":"PS Vita",
 "xbox":"Xbox","xbox 360":"Xbox 360","x360":"Xbox 360","pc":"PC","win32":"PC","windows":"PC",
 "pc (windows)":"PC","pc (dos)":"DOS","dos":"DOS","ms-dos":"DOS","arcade":"Arcade","genesis":"Genesis",
 "mega drive":"Genesis","sega genesis / mega drive":"Genesis","megadrive":"Genesis","saturn":"Saturn",
 "dreamcast":"Dreamcast","dc":"Dreamcast","sega cd":"Sega CD","master system":"Master System",
 "game gear":"Game Gear","android":"Mobile","ios":"Mobile","mobile":"Mobile","j2me":"Mobile",
 "mac":"Mac","amiga":"Amiga","atari 2600":"Atari 2600","pc engine":"PC Engine","n-gage":"N-Gage",
}
def norm_plat(p):
    if not p: return ""
    k = p.strip().lower()
    return PLAT.get(k, p.strip())

def url_key(u):
    u = unquote(u.strip()).rstrip("/")
    u = re.sub(r"^https?://(www\.)?", "", u, flags=re.I)
    u = re.sub(r"\.git$", "", u)
    u = re.sub(r"#.*$", "", u)
    return u.lower()

def clean_title(t):
    t = html.unescape(t).replace("⚠️", "").replace("\u26a0", "").replace("\ufe0f", "")
    t = re.sub(r"\*+", "", t)
    return re.sub(r"\s+", " ", t).strip()

def game_key(t):
    t = t.lower()
    t = re.sub(r"\((recomp|recompiled|decomp|port|native port|pc port|x360|ps2|ps1|n64|jp|us|eu)[^)]*\)", "", t)
    t = re.sub(r"\b(recomp(iled)?|decomp(ilation)?|decompiled|remake|port)\b", "", t)
    t = t.replace("é", "e").replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "", t)

records = {}
def add(src, title, url, platform="", hint="", desc="", extra=None):
    if not url or not re.match(r"https?://", url): return
    title = clean_title(title)
    if not title: return
    k = url_key(url)
    r = records.get(k)
    if r is None:
        r = records[k] = {"title": title, "url": url.strip().rstrip("/"), "platform": norm_plat(platform),
                          "sources": [], "hints": [], "description": desc.strip(), "ai_flag": False}
    if src not in r["sources"]: r["sources"].append(src)
    if hint and hint not in r["hints"]: r["hints"].append(hint)
    if not r["platform"] and platform: r["platform"] = norm_plat(platform)
    if not r["description"] and desc: r["description"] = desc.strip()
    if extra: 
        for kk, vv in extra.items():
            if vv not in (None, ""): r.setdefault(kk, vv)
    return r

LINK = re.compile(r"^\s*[-*]\s+\[([^\]]+)\]\(([^)\s]+)\)\s*(?:[-–—:]\s*(.*))?$")

def parse_md(fn, src, plat_from_section=False, hint_fn=None):
    sec = ""
    for line in open(os.path.join(RAW, fn), encoding="utf-8"):
        h = re.match(r"^#{2,4}\s+(.*)", line)
        if h: sec = h.group(1).strip(); continue
        m = LINK.match(line)
        if not m: continue
        title, url, desc = m.group(1), m.group(2), (m.group(3) or "")
        if url.startswith("#") or "samidy.com" in url: continue
        ai = "⚠" in title
        hint = hint_fn(title, url, desc, sec) if hint_fn else ""
        plat = sec if plat_from_section and sec.strip().lower() in PLAT else ""
        t2 = re.sub(r"\s*\((recomp|recompiled|recompilation)\)\s*$", "", title, flags=re.I)
        if t2 != title: hint = hint or "recomp"
        urls = [u for u in re.split(r"(?=https?://)", url) if u]  # some source lines glue two URLs together
        for u in urls:
            r = add(src, t2, u, plat, hint, desc)
            if r and ai: r["ai_flag"] = True

# 1. Samidy
if os.path.exists(os.path.join(RAW, "samidy.md")): parse_md("samidy.md", "samidy")
# 2. Charlotte (sections are consoles)
parse_md("charlotte.md", "charlotte", plat_from_section=True)
# 3. awesome-game-remakes (engine remakes / source ports / recomps)
def remake_hint(t, u, d, sec):
    dl = d.lower()
    if re.search(r"\brecomp", dl): return "recomp"
    if re.search(r"javascript|browser|web\b|wasm", dl): return "browser"
    if re.search(r"source port|\bport\b", dl): return "port"
    return "remake"
parse_md("remakes.md", "awesome-game-remakes", hint_fn=remake_hint)
# 4. BlueInterlude awesome-recompilations: headings = game, bare github links
sec, plat = "", ""
for line in open(os.path.join(RAW, "blueinterlude.md"), encoding="utf-8"):
    h = re.match(r"^(#{3,4})\s+(.*)", line)
    if h:
        if h.group(1) == "###": plat = h.group(2).strip()
        sec = h.group(2).strip(); continue
    for u in re.findall(r"\[(https://github\.com/[^\]]+)\]", line):
        if sec.lower() in ("template", "mods"): continue
        add("awesome-recompilations", sec, u, plat if plat in ("N64", "Xbox 360") else "", "recomp")
# 5. decomp.dev
dd = json.load(open(os.path.join(RAW, "decompdev.json")))["projects"]
for p in dd:
    m = p.get("measures") or {}
    add("decomp.dev", p["name"], p["repo_url"], p.get("platform", ""), "decomp", "",
        {"decompdev_id": p["id"], "progress": round(m.get("matched_code_percent", 0) or 0, 2),
         "progress_functions": round(m.get("matched_functions_percent", 0) or 0, 2),
         "decompdev_url": f"https://decomp.dev/{p['owner']}/{p['repo']}"})
# 6. recompiledgames.com (browser ports in data-* attrs)
h = open(os.path.join(RAW, "recompiledgames.html"), encoding="utf-8").read()
for li in re.findall(r'<li class="row"(.*?)</li>', h, re.S):
    attrs = dict(re.findall(r'data-(\w+)="([^"]*)"', li))
    name = re.search(r'class="c-game"><a href="([^"]+)">([^<]+)</a>', li)
    play = re.search(r'class="play[^"]*" href="([^"]+)"', li)
    thumb = re.search(r'<img src="([^"]+)"', li)
    if not name: continue
    slug = name.group(1).strip("/")
    page = "https://recompiledgames.com/" + slug + "/"
    kind = attrs.get("kind", "")
    hint = {"browser": "browser", "native": "recomp", "tool": "tool"}.get(kind, "browser")
    url = play.group(1) if play else page
    add("recompiledgames.com", name.group(2), url, attrs.get("plat", ""), hint, "",
        {"play_url": play.group(1) if play else None, "info_url": page, "assets": attrs.get("assets"),
         "multiplayer": attrs.get("mp") == "1", "rg_ok": attrs.get("ok") == "1",
         "thumb_src": ("https://recompiledgames.com" + thumb.group(1)) if thumb else None})
# 7. recomp.fyi table
if "--no-recompfyi" not in sys.argv:
    h = open(os.path.join(RAW, "recompfyi.html"), encoding="utf-8").read()
    for tr in re.findall(r'<tr class="data-row"(.*?)</tr>', h, re.S):
        g = re.search(r'class="game-link">([^<]+)', tr)
        sysm = re.search(r'class="system-tag">([^<]+)', tr)
        typ = re.search(r'data-type="([^"]+)"', tr)
        proj = re.search(r'<a href="([^"]+)" rel="noopener" class="project-link">', tr)
        act = re.search(r'data-activity="([^"]+)"', tr)
        if not (g and proj): continue
        t = typ.group(1) if typ else ""
        add("recomp.fyi", g.group(1), proj.group(1), sysm.group(1) if sysm else "",
            {"decomp": "decomp", "recomp": "recomp", "port": "port"}.get(t, ""), "",
            {"recompfyi_activity": act.group(1) if act else None})

# 8. manual additions (data/additions.json): [{"title","url","platform","type","description"}]
ap = os.path.join(ROOT, "data", "additions.json")
if os.path.exists(ap):
    for a in json.load(open(ap)):
        add("manual", a["title"], a["url"], a.get("platform", ""), a.get("type", ""), a.get("description", ""))

out = sorted(records.values(), key=lambda r: r["title"].lower())
for r in out: r["game_key"] = game_key(r["title"])
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "data", "collected.json"), "w"), indent=1, ensure_ascii=False)
from collections import Counter
c = Counter(s for r in out for s in r["sources"])
print("projects:", len(out), "unique games:", len({r['game_key'] for r in out}), dict(c))
