#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v rustc >/dev/null 2>&1; then
  echo "ERROR: rustc est requis pour déterminer la cible Tauri." >&2
  exit 2
fi

python3 -m PyInstaller   --clean   --noconfirm   --onefile   --name piste-studio-backend   --collect-data piste_studio   --hidden-import uvicorn.logging   --hidden-import uvicorn.loops.auto   --hidden-import uvicorn.protocols.http.auto   --hidden-import uvicorn.protocols.websockets.auto   --hidden-import uvicorn.lifespan.on   scripts/desktop_backend_entry.py

TRIPLE="$(rustc --print host-tuple 2>/dev/null || true)"
if [[ -z "$TRIPLE" ]]; then
  TRIPLE="$(rustc -Vv | awk '/host:/ {print $2}')"
fi
if [[ -z "$TRIPLE" ]]; then
  echo "ERROR: impossible de déterminer le target triple Rust." >&2
  exit 3
fi

mkdir -p desktop/src-tauri/binaries
cp "dist/piste-studio-backend" "desktop/src-tauri/binaries/piste-studio-backend-$TRIPLE"
chmod +x "desktop/src-tauri/binaries/piste-studio-backend-$TRIPLE"

echo "SIDECAR READY — $TRIPLE"
echo "desktop/src-tauri/binaries/piste-studio-backend-$TRIPLE"
