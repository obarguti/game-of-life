# Launches Conway's Game of Life, creating the venv and installing deps on first run.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Setting up virtual environment..."
    python -m venv .venv
    & $python -m pip install --quiet -r requirements.txt
}

& $python -m conway
