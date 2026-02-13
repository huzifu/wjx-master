Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "[setup] project: $PSScriptRoot\.."
Set-Location (Join-Path $PSScriptRoot "..")

function Get-UsablePythonCommand {
    $candidates = @(
        @("py", "-3"),
        @("python")
    )

    foreach ($cmd in $candidates) {
        try {
            if ($cmd.Count -eq 2) {
                & $cmd[0] $cmd[1] -c "import sys; print(sys.executable)" *> $null
            } else {
                & $cmd[0] -c "import sys; print(sys.executable)" *> $null
            }
            if ($LASTEXITCODE -eq 0) {
                return $cmd
            }
        } catch {
            continue
        }
    }
    return $null
}

$pythonCmd = Get-UsablePythonCommand
if (-not $pythonCmd) {
    Write-Error "No usable Python found. Install Python 3.10+ from python.org and re-open terminal."
}

if (-not (Test-Path ".venv")) {
    Write-Host "[setup] creating .venv"
    if ($pythonCmd.Count -eq 2) {
        & $pythonCmd[0] $pythonCmd[1] -m venv .venv
    } else {
        & $pythonCmd[0] -m venv .venv
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path ".venv")) {
        Write-Error "Failed to create .venv. Check local Python installation."
    }
}

$python = Join-Path (Resolve-Path ".venv").Path "Scripts\python.exe"
$pip = Join-Path (Resolve-Path ".venv").Path "Scripts\pip.exe"

Write-Host "[setup] upgrading pip"
& $python -m pip install -U pip

Write-Host "[setup] installing requirements"
& $pip install -r requirements.txt

Write-Host "[setup] done"
