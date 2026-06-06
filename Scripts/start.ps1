# Start the CV Analyser API (creates .venv on first run).
# Usage: .\scripts\start.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

$Python = "C:\Program Files\Python312\python.exe"
if (-not (Test-Path $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment in .venv ..."
    & $Python -m venv .venv
    & $VenvPython -m pip install -r requirements.txt
}

$env:OLLAMA_MODEL = "llama3.2:3b-gpu"
$env:OLLAMA_NUM_GPU = "-1"

Write-Host "Model: $env:OLLAMA_MODEL | num_gpu: $env:OLLAMA_NUM_GPU"
Write-Host "Starting API at http://127.0.0.1:8000/docs"
& $VenvPython -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
