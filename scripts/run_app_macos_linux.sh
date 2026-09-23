#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 /chemin/vers/PROJET_PISTE_STUDIO"
  exit 2
fi
python3 -m piste_studio.app --project "$1"
