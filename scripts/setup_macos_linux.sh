#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
echo
echo "PISTE Studio V0.11 installé."
echo "Active ensuite l'environnement avec: source .venv/bin/activate"
echo "Puis: piste-studio --help"
