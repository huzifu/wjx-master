Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$venvPython = ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[doctor] .venv not found. Run: .\\scripts\\setup_env.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "[doctor] python:"
& $venvPython -V

Write-Host "[doctor] core dependencies:"
& $venvPython -m pip show selenium webdriver-manager requests numpy openai pillow beautifulsoup4 | Out-Host

Write-Host "[doctor] driver files:"
if (Test-Path "chromedriver.exe") {
    Write-Host "  - chromedriver.exe found"
} else {
    Write-Host "  - chromedriver.exe not found (will fallback to webdriver-manager)" -ForegroundColor Yellow
}
if (Test-Path "chromedriver-win64") {
    Write-Host "  - chromedriver-win64 folder found"
}

Write-Host "[doctor] entry:"
if (Test-Path "wjx_auto_fill.py") {
    Write-Host "  - wjx_auto_fill.py found"
} else {
    Write-Host "  - wjx_auto_fill.py missing" -ForegroundColor Red
    exit 1
}

Write-Host "[doctor] done"
