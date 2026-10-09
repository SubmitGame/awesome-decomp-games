# Contributing

Thanks for helping! This list is **generated**. Please don't edit `README.md` or the tables by hand; they're rebuilt daily from `data/`.

## Add a project
Open a PR that appends to [`data/additions.json`](data/additions.json):

```json
{"title": "Game Name", "url": "https://github.com/owner/repo", "platform": "N64", "type": "decomp", "description": "One line"}
```

`type` is a hint: `decomp`, `recomp`, `port`, `remake`, `browser` or `tool`. Stars, last commit, decomp.dev progress, link status and ratings are filled in automatically.

**What qualifies**
- A decompilation, disassembly, static recompilation, source port, engine reimplementation/remake, or browser port of a **commercially released** game (or a notable freeware one).
- Public source code or a public project page.
- No mods, ROM hacks or fan games. Projects that their source list flags as AI-generated get marked ⚠️.

**What is never accepted**
- Links to ROMs, ISOs, BIOS files, extracted assets, or sites that host them.
- Repos that ship copyrighted game data.

## Fix an entry
Use [`data/overrides.json`](data/overrides.json):
- `"exclude": ["https://github.com/owner/repo"]` removes an entry.
- `"set": {"https://github.com/owner/repo": {"type": "source-port", "platform": "PS2"}}` overrides any field.

Screenshots, video links and top-pick notes are in [`data/media.json`](data/media.json). Screenshots go in `screenshots/` as JPEG, about 1280 px wide and under 300 KB, and must be your own captures or come from the project's own README.

## Run it locally
```bash
pip install requests Pillow
gh auth login           # GraphQL enrichment uses gh
scripts/refresh         # fetch, enrich, rate, regenerate README.md + data/games.json
```
Open `index.html` through a local server (`python3 -m http.server`) to preview the site.

## Rights holders
If you want an entry removed, open an issue and we'll take it down.
