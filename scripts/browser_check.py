#!/usr/bin/env python3
"""Load every browser play_url in headless Chrome and flag pages that render as takedowns/errors.
Writes data/browser_status.json {play_url: {"ok": bool, "title": str, "checked": iso}}; build.py hides
entries with ok=false from the browser section. Skips silently if Playwright is unavailable."""
import json, os, re, shutil, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAD = re.compile(r"content removed|taken down|copyright notice|dmca takedown|error 10\d\d|cname cross-user|site not found|"
                 r"deployment not found|application error|404 not found|this site can.t be reached|domain .* for sale|suspended", re.I)
def main():
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("playwright missing, skipping browser check"); return
    doc = json.load(open(os.path.join(ROOT, "data", "games.json")))
    urls = sorted({e["play_url"] for e in doc["games"] if e.get("play_url")})
    sp = os.path.join(ROOT, "data", "browser_status.json")
    status = json.load(open(sp)) if os.path.exists(sp) else {}
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome, args=["--no-sandbox"]) if chrome else p.chromium.launch()
        for u in urls:
            pg = b.new_page()
            try:
                pg.goto(u, timeout=45000, wait_until="domcontentloaded"); pg.wait_for_timeout(7000)
                title = pg.title(); body = pg.inner_text("body")[:1500]
                bad = BAD.search(title + " " + body)
                status[u] = {"ok": not bad, "title": title[:120], "reason": bad.group(0) if bad else None,
                             "checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            except Exception as ex:
                prev = status.get(u, {})
                status[u] = {**prev, "ok": False, "reason": "load error", "error": str(ex)[:120], "checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            print(("OK  " if status[u].get("ok", True) else "BAD ") + u, status[u].get("reason") or "")
            pg.close()
        b.close()
    json.dump(status, open(sp, "w"), indent=1, ensure_ascii=False)
if __name__ == "__main__": main()
