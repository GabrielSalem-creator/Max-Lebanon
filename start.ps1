$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "Starting MAX on Windows..." -ForegroundColor Cyan

# Install deps if needed
if (-not (Get-Command uvicorn -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt -q
    python -m playwright install chromium 2>$null
}

# Create required directories
New-Item -ItemType Directory -Force -Path "data","static\img","static\files" | Out-Null

Write-Host "MAX running at http://localhost:8000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray
python main.py
