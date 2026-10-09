#!/usr/bin/env python3
"""Screenshots for browser-playable entries -> screenshots/browser-*.jpg + data/media.json.
Order: recompiledgames.com full-size image, the play page's og:image, then (if Playwright + Chrome
are available) a live capture of the play page. Usage: browser_media.py [--missing-only]"""
import json, os, re, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import media as M
import requests
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def og_image(url):
    try:
        h = requests.get(url, headers=M.UA, timeout=20).text
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', h) or re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image', h)
        return requests.compat.urljoin(url, m.group(1)) if m else None
    except Exception:
        return None

def capture(urls):
    out = {}
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return out
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"]) if chrome else p.chromium.launch()
        for u in urls:
            pg = b.new_page(viewport={"width": 1280, "height": 720})
            try:
                pg.goto(u, timeout=45000, wait_until="domcontentloaded"); pg.wait_for_timeout(6000)
                fn = "/tmp/_cap.png"; pg.screenshot(path=fn)
                from PIL import Image
                out[u] = Image.open(fn).convert("RGB")
            except Exception as ex:
                print("capture failed", u, str(ex)[:80])
            pg.close()
        b.close()
    return out

def main():
    doc = json.load(open(os.path.join(ROOT, "data", "games.json")))
    mp = os.path.join(ROOT, "data", "media.json"); media = json.load(open(mp))
    todo = []
    for e in doc["games"]:
        if not e.get("browser_playable"): continue
        m = media.setdefault(e["url"], {})
        if m.get("screenshot") and ("--missing-only" in sys.argv or m.get("locked")): continue
        im, src = None, None
        if e.get("thumb_src"):
            src = e["thumb_src"].replace("/thumbs/", "/"); im = M.fetch_img(src)
        if im is None:
            src = og_image(e["play_url"]); im = M.fetch_img(src) if src else None
        if im is None: todo.append(e); continue
        save(e, m, im, src, M.quality(im))
    caps = capture([e["play_url"] for e in todo]) if todo else {}
    for e in todo:
        im = caps.get(e["play_url"])
        if im is not None: save(e, media[e["url"]], im, "live capture of " + e["play_url"], 3)
        else: print("no image:", e["title"])
    json.dump(media, open(mp, "w"), indent=1, ensure_ascii=False)

def save(e, m, im, src, q):
    fn = f"screenshots/browser-{e['id'][:50]}.jpg"
    size, nb = M.save_jpeg(im, os.path.join(ROOT, fn))
    m.update({"screenshot": fn, "screenshot_source": src, "screenshot_size": list(size), "screenshot_score": q})
    print(f"{e['title']}: {fn} {size} {nb//1024}KB ({src})")

if __name__ == "__main__": main()
