#!/usr/bin/env bash
# Download raw source lists into raw/ (not committed).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p raw
raw() { gh api "repos/$1/readme" -H "Accept: application/vnd.github.raw" > "raw/$2"; }
raw SamidyFR/Game-Decompilations samidy.md
raw CharlotteCross1998/awesome-game-decompilations charlotte.md
raw BlueInterlude/awesome-recompilations blueinterlude.md
raw radek-sprta/awesome-game-remakes remakes.md
curl -fsSL https://decomp.dev/projects.json -o raw/decompdev.json
curl -fsSL https://recompiledgames.com/ -o raw/recompiledgames.html
curl -fsSL https://recomp.fyi/ -o raw/recompfyi.html
echo "sources fetched"
