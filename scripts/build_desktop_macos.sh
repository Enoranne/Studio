#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m pip install -e '.[packaging]'
bash scripts/build_desktop_backend.sh

cd desktop
npm install
npx tauri icon app-icon.svg
npm run tauri build -- --bundles app,dmg

echo "PISTE Studio desktop build terminé."
echo "Bundles : desktop/src-tauri/target/release/bundle/"
