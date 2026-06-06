$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "=== GTX 1650 4GB: use llama3.2:3b (~2GB), NOT qwen 7b (5GB = 100% CPU) ===" -ForegroundColor Yellow
Write-Host ""

# ollama stop requires a model name — unload whatever is running
$running = ollama ps 2>$null | Select-Object -Skip 1
foreach ($line in $running) {
    if ($line -match "^\s*(\S+)") {
        $name = $Matches[1]
        Write-Host "Stopping $name ..."
        ollama stop $name 2>$null
    }
}

Write-Host "Pulling llama3.2:3b..."
ollama pull llama3.2:3b

Write-Host "Creating llama3.2:3b-gpu (all layers on GPU)..."
$modelfile = Join-Path $ProjectRoot "Modelfile.gpu"
ollama create llama3.2:3b-gpu -f $modelfile 2>$null
if ($LASTEXITCODE -ne 0) {
    ollama create llama3.2:3b-gpu -f $modelfile --force
}

Write-Host ""
Write-Host "Loading model to test GPU..."
ollama run llama3.2:3b-gpu "ok"

Write-Host ""
Write-Host "Check PROCESSOR column (must NOT say 100% CPU):" -ForegroundColor Cyan
ollama ps

Write-Host ""
Write-Host "Start API: .\scripts\start.ps1"
