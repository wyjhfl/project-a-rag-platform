# final_production_acceptance.ps1
# Production Landing acceptance script with full coverage.
# Docker is MANDATORY. All steps must pass.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\final_production_acceptance.ps1 `
#       -PythonExe "D:\codex安装\tools\Python312\python.exe" `
#       -NpmCmd "D:\codex安装\tools\nodejs\npm.cmd" `
#       -RunFullE2E
#
# Tool discovery order:
#   1. Command-line parameters (-PythonExe / -NpmCmd)
#   2. Environment variables (PROJECT_A_PYTHON_EXE / PROJECT_A_NPM_CMD)
#   3. scripts/acceptance.defaults.json
#   4. PATH lookup (filtering WindowsApps python alias)

param(
    [string]$PythonExe = "",
    [string]$NpmCmd = "",
    [switch]$RunFullE2E
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")

# --- Tool Discovery (mirrors final_acceptance.ps1) ---
$DefaultsFile = Join-Path $ScriptDir "acceptance.defaults.json"
$Defaults = $null
if (Test-Path $DefaultsFile) {
    $Defaults = Get-Content -Path $DefaultsFile -Raw -Encoding UTF8 | ConvertFrom-Json
}

# Python
if (-not $PythonExe) { $PythonExe = $env:PROJECT_A_PYTHON_EXE }
if (-not $PythonExe -and $Defaults -and $Defaults.python_exe) { $PythonExe = $Defaults.python_exe }
if (-not $PythonExe) {
    $candidates = @()
    $found = Get-Command python -ErrorAction SilentlyContinue
    if ($found) { $candidates += @($found.Source) }
    $found = Get-Command python3 -ErrorAction SilentlyContinue
    if ($found) { $candidates += @($found.Source) }
    foreach ($c in $candidates) {
        if ($c -notmatch "WindowsApps") {
            $PythonExe = $c
            break
        }
    }
}

# npm
if (-not $NpmCmd) { $NpmCmd = $env:PROJECT_A_NPM_CMD }
if (-not $NpmCmd -and $Defaults -and $Defaults.npm_cmd) { $NpmCmd = $Defaults.npm_cmd }
if (-not $NpmCmd) {
    $found = Get-Command npm -ErrorAction SilentlyContinue
    if ($found) { $NpmCmd = $found.Source }
}

Write-Host "=== Production Acceptance Script ===" -ForegroundColor Cyan
Write-Host "ProjectRoot : $ProjectRoot"
Write-Host "PythonExe   : $PythonExe"
Write-Host "NpmCmd      : $NpmCmd"
Write-Host "RunFullE2E  : $RunFullE2E"
Write-Host ""

# --- Pre-flight Checks ---
Write-Host "--- Pre-flight Checks ---" -ForegroundColor Yellow

function Test-Executable {
    param(
        [string]$Label,
        [string]$ExePath,
        [string[]]$TestArgs
    )
    if (-not $ExePath -or -not (Test-Path $ExePath -ErrorAction SilentlyContinue)) {
        # Try as PATH command
        $cmd = Get-Command $ExePath -ErrorAction SilentlyContinue
        if (-not $cmd) {
            Write-Host "FATAL: $Label not found at '$ExePath'" -ForegroundColor Red
            return $false
        }
        $ExePath = $cmd.Source
    }
    try {
        $output = & $ExePath @TestArgs 2>&1
        $verLine = ($output | Where-Object { $_ -match "\d+\.\d+" } | Select-Object -First 1)
        Write-Host "  $Label : $verLine" -ForegroundColor Gray
        return $true
    } catch {
        Write-Host "FATAL: $Label at '$ExePath' could not execute: $_" -ForegroundColor Red
        return $false
    }
}

$preOk = $true

if (-not (Test-Executable -Label "Python" -ExePath $PythonExe -TestArgs @("--version"))) { $preOk = $false }
if (-not (Test-Executable -Label "npm" -ExePath $NpmCmd -TestArgs @("--version"))) { $preOk = $false }

# Docker - MANDATORY
$dockerExe = $null
$dockerFound = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerFound) { $dockerExe = $dockerFound.Source }
if (-not $dockerExe) {
    Write-Host "FATAL: docker command not found. Docker is required for production acceptance." -ForegroundColor Red
    $preOk = $false
} else {
    try {
        $dv = & docker --version 2>&1
        $verLine = ($dv | Where-Object { $_ -match "\d+\.\d+" } | Select-Object -First 1)
        Write-Host "  docker : $verLine" -ForegroundColor Gray
        & docker compose version 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FATAL: docker compose not available" -ForegroundColor Red
            $preOk = $false
        }
    } catch {
        Write-Host "FATAL: docker could not execute: $_" -ForegroundColor Red
        $preOk = $false
    }
}

if (-not $preOk) {
    Write-Host ""
    Write-Host "FATAL: Pre-flight checks failed. Cannot continue." -ForegroundColor Red
    exit 1
}

Write-Host "Pre-flight checks PASSED" -ForegroundColor Green
Write-Host ""

# Make child npm scripts use the same verified tools. This is required on
# Windows where the PATH `python` command can be a Microsoft Store alias.
$env:PROJECT_A_PYTHON_EXE = $PythonExe
$env:PROJECT_A_NPM_CMD = $NpmCmd

# --- Step Runner ---
$StepNames = [System.Collections.Specialized.OrderedDictionary]::new()

function Run-Step {
    param([string]$Name, [scriptblock]$Block)
    $StepNames[$Name] = $false
    Write-Host "--- $Name ---" -ForegroundColor Yellow
    $savedEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Block
        if ($LASTEXITCODE -eq 0) {
            Write-Host "PASSED" -ForegroundColor Green
            $StepNames[$Name] = $true
        } else {
            Write-Host "FAILED (exit code $LASTEXITCODE)" -ForegroundColor Red
        }
    } catch {
        Write-Host "FAILED (exception: $_)" -ForegroundColor Red
    } finally {
        $ErrorActionPreference = $savedEAP
    }
}

# --- Steps ---

Run-Step "1. Full Backend Tests" {
    Set-Location $ProjectRoot
    & $PythonExe -m pytest backend/tests -q 2>&1 | Out-Null
}

Run-Step "2. Ruff Check" {
    Set-Location $ProjectRoot
    & $PythonExe -m ruff check backend 2>&1 | Out-Null
}

Run-Step "3. Frontend Build" {
    Set-Location "$ProjectRoot\frontend"
    & $NpmCmd run build 2>&1 | Out-Null
}

Run-Step "4. OpenAPI Drift Check" {
    Set-Location "$ProjectRoot\frontend"
    & $NpmCmd run api:check 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "api:check failed with exit code $LASTEXITCODE" }
    Set-Location $ProjectRoot
    git diff --exit-code docs/openapi.json frontend/src/api/generated.ts 2>&1 | Out-Null
}

Run-Step "5. E2E List" {
    Set-Location "$ProjectRoot\frontend"
    & $NpmCmd run e2e -- --list 2>&1 | Out-Null
}

Run-Step "6. Secret Scan" {
    Set-Location $ProjectRoot
    & $PythonExe scripts/secret_scan.py --dir . 2>&1 | Out-Null
}

Run-Step "7. Docker Compose Production Config" {
    Set-Location $ProjectRoot
    docker compose config 2>&1 | Out-Null
}

Run-Step "8. Docker Compose Demo Config" {
    Set-Location $ProjectRoot
    docker compose -f docker-compose.demo.yml config 2>&1 | Out-Null
}

Run-Step "9. PostgreSQL Smoke" {
    Set-Location $ProjectRoot
    # Let the script auto-start Docker Postgres; ensure psycopg_pool is importable
    $env:PYTHONPATH = "$ProjectRoot\.pg_deps;" + $env:PYTHONPATH
    Remove-Item Env:\SKIP_DOCKER -ErrorAction SilentlyContinue
    Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
    & $PythonExe scripts/postgres_job_smoke.py 2>&1 | Out-Null
}

Run-Step "10. Redis Rate Limit Unit Tests" {
    Set-Location $ProjectRoot
    & $PythonExe -m pytest backend/tests/test_redis_rate_limit.py -q 2>&1 | Out-Null
}

Run-Step "11. Redis Rate Limit Smoke" {
    Set-Location $ProjectRoot
    $env:PYTHONPATH = "$ProjectRoot;$ProjectRoot\backend;$ProjectRoot\.pg_deps;" + $env:PYTHONPATH
    & $PythonExe scripts/redis_rate_limit_smoke.py 2>&1 | Out-Null
}

Run-Step "12. PostgreSQL Worker Stress" {
    Set-Location $ProjectRoot
    $env:PYTHONPATH = "$ProjectRoot\.pg_deps;" + $env:PYTHONPATH
    & $PythonExe scripts/postgres_worker_stress.py --jobs 20 --workers 4 2>&1 | Out-Null
}

# Full E2E (required for v1.0.0 tag gate)
if ($RunFullE2E) {
    Run-Step "13. Full E2E" {
        Set-Location $ProjectRoot
        & powershell -ExecutionPolicy Bypass -File "$ProjectRoot\scripts\run_full_e2e_demo.ps1" -PythonExe $PythonExe -NpmCmd $NpmCmd 2>&1 | Out-Null
    }
}

Set-Location $ProjectRoot

# --- Summary ---
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "PRODUCTION ACCEPTANCE SUMMARY"
Write-Host "=====================================" -ForegroundColor Cyan

$allPassed = $true
foreach ($key in $StepNames.Keys) {
    $val = $StepNames[$key]
    if ($val) { $status = "PASSED" } else { $status = "FAILED" }
    if ($val) { $color = "Green" } else { $color = "Red" }
    Write-Host "  ${key}: $status" -ForegroundColor $color
    if (-not $val) { $allPassed = $false }
}

Write-Host "=====================================" -ForegroundColor Cyan

if ($allPassed) {
    Write-Host "ALL CHECKS PASSED" -ForegroundColor Green
    exit 0
} else {
    Write-Host "SOME CHECKS FAILED" -ForegroundColor Red
    exit 1
}
