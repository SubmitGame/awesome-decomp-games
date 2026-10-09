#!/usr/bin/env bash
# Download raw source lists into raw/ (not committed).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p raw
raw() { gh api "repos/$1/readme" -H "Accept: application/vnd.github.raw" > "raw/$2.tmp" && mv "raw/$2.tmp" "raw/$2" || echo "WARN: could not fetch $1" >&2; }
get() { curl -fsSL -m 60 -A "Mozilla/5.0 awesome-decomp-games-refresh" "$1" -o "raw/$2.tmp" && mv "raw/$2.tmp" "raw/$2" || echo "WARN: could not fetch $1" >&2; }
raw SamidyFR/Game-Decompilations samidy.md
raw CharlotteCross1998/awesome-game-decompilations charlotte.md
raw BlueInterlude/awesome-recompilations blueinterlude.md
raw radek-sprta/awesome-game-remakes remakes.md
get https://decomp.dev/projects.json decompdev.json
get https://recompiledgames.com/ recompiledgames.html
get https://recomp.fyi/ recompfyi.html
echo "sources fetched"
