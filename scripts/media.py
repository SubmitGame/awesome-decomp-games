#!/usr/bin/env python3
"""Find screenshots + video links for top picks (and optionally all candidates), save JPEGs to screenshots/
(~1280px wide, <300KB) and record them in data/media.json. Images come from each project's own README /
social preview image. Usage: media.py [--missing-only] [--top N]"""
import json, os, re, sys, io, subprocess, hashlib
from urllib.parse import urljoin
import requests
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) awesome-decomp-games/1.0"}
SKIP = re.compile(r"shields\.io|badge|\.svg|logo|icon|discord|patreon|ko-fi|kofi|paypal|sponsor|banner|button|avatar|star-history|contrib\.rocks|emoji|favicon|workflow|codecov|repobeats|wakatime|title|weblate|translat|hosted\.weblate", re.I)
YT = re.compile(r"https?://(?:www\.)?(?:youtube\.com/watch\?v=[\w-]{11}|youtu\.be/[\w-]{11}|youtube\.com/embed/[\w-]{11})")

def readme(repo):
    p = subprocess.run(["gh", "api", f"repos/{repo}/readme"], capture_output=True, text=True)
    if p.returncode: return "", ""
    j = json.loads(p.stdout)
    raw = subprocess.run(["gh", "api", f"repos/{repo}/readme", "-H", "Accept: application/vnd.github.raw"], capture_output=True, text=True).stdout
    base = j.get("download_url") or f"https://raw.githubusercontent.com/{repo}/HEAD/README.md"
    return raw, base

def candidates(md, base):
    urls = re.findall(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)", md) + re.findall(r"<img[^>]+src=[\"']([^\"']+)", md, re.I)
    out = []
    for u in urls:
        u = urljoin(base, u.strip())
        u = re.sub(r"https://github\.com/([^/]+/[^/]+)/blob/", r"https://raw.githubusercontent.com/\1/", u)
        if SKIP.search(u) or u in out: continue
        out.append(u)
    return out

def fetch_img(u):
    try:
        r = requests.get(u, headers=UA, timeout=25)
        if r.status_code != 200 or len(r.content) < 8000: return None
        im = Image.open(io.BytesIO(r.content)); im.seek(0)
        return im.convert("RGB")
    except Exception:
        return None

def quality(im, from_og=False):
    w, h = im.size; ar = w / max(h, 1)
    shot_like = 1.1 <= ar <= 2.1
    if from_og: return 2 if w < 1000 else 3
    if not shot_like: return 2
    return 5 if w >= 1200 else 4 if w >= 800 else 3 if w >= 480 else 2

def save_jpeg(im, path):
    if im.width > 1280: im = im.resize((1280, round(im.height * 1280 / im.width)), Image.LANCZOS)
    for q in (85, 80, 72, 65, 58, 50, 42):
        b = io.BytesIO(); im.save(b, "JPEG", quality=q, optimize=True, progressive=True)
        if b.tell() < 300_000: break
    if b.tell() >= 300_000:  # still too big: shrink
        im = im.resize((960, round(im.height * 960 / im.width)), Image.LANCZOS); b = io.BytesIO(); im.save(b, "JPEG", quality=70, optimize=True)
    open(path, "wb").write(b.getvalue())
    return im.size, b.tell()

def main():
    args = sys.argv[1:]
    top = int(args[args.index("--top") + 1]) if "--top" in args else 40
    doc = json.load(open(os.path.join(ROOT, "data", "games.json")))
    mp = os.path.join(ROOT, "data", "media.json")
    media = json.load(open(mp)) if os.path.exists(mp) else {}
    games = [e for e in doc["games"] if e.get("top_pick")]
    games += sorted([e for e in doc["games"] if not e.get("top_pick") and e["ratings"]["playability"] >= 4], key=lambda e: -e["score"])[:max(0, top - len(games))]
    os.makedirs(os.path.join(ROOT, "screenshots"), exist_ok=True)
    for e in games:
        m = media.setdefault(e["url"], {})
        if "--missing-only" in args and m.get("screenshot") and m.get("checked"): continue
        md, base = readme(e["repo"]) if e.get("repo") else ("", "")
        if not m.get("video"):
            v = YT.search(md or "")
            if v: m["video"] = v.group(0)
        best = None
        if not (m.get("screenshot") and m.get("locked")):
            cands = candidates(md, base)[:8] if md else []
            for u in cands:
                im = fetch_img(u)
                if im is None: continue
                q = quality(im)
                if best is None or (q, im.width) > (best[0], best[1].width): best = (q, im, u)
                if q >= 5: break
            if (best is None or best[0] < 3) and e.get("og_image"):
                im = fetch_img(e["og_image"])
                if im is not None and (best is None or quality(im, True) > best[0]): best = (quality(im, True), im, e["og_image"])
            if best is None and e.get("thumb_src"):
                im = fetch_img(e["thumb_src"].replace("/thumbs/", "/"))
                if im is not None: best = (quality(im), im, e["thumb_src"].replace("/thumbs/", "/"))
            if (best is None or best[0] < 3) and m.get("video"):  # fall back to the video's thumbnail
                vid = re.search(r"(?:v=|youtu\.be/|embed/)([\w-]{11})", m["video"])
                for qn in ("maxresdefault", "sddefault", "hqdefault"):
                    im = fetch_img(f"https://i.ytimg.com/vi/{vid.group(1)}/{qn}.jpg") if vid else None
                    if im is not None:
                        q = min(quality(im), 4)
                        if best is None or q > best[0]: best = (q, im, f"https://i.ytimg.com/vi/{vid.group(1)}/{qn}.jpg")
                        break
            if best:
                fn = f"screenshots/{e['id'][:60]}.jpg"
                size, nbytes = save_jpeg(best[1], os.path.join(ROOT, fn))
                m.update({"screenshot": fn, "screenshot_score": best[0], "screenshot_source": best[2], "screenshot_size": list(size)})
                print(f"{e['title']}: {fn} {size} {nbytes//1024}KB q={best[0]}  video={m.get('video')}")
            else:
                print(f"{e['title']}: no image  video={m.get('video')}")
        if m.get("screenshot") and not m.get("screenshot_score"): m["screenshot_score"] = 3
        m["checked"] = True
    json.dump(media, open(mp, "w"), indent=1, ensure_ascii=False)

if __name__ == "__main__": main()
