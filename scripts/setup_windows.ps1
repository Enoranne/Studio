$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
py -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
Write-Host ""
Write-Host "PISTE Studio V0.11 installé."
Write-Host "Active ensuite l'environnement avec: .\.venv\Scripts\Activate.ps1"
Write-Host "Puis: piste-studio --help"
