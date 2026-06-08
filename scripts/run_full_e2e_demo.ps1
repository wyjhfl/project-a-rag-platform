# run_full_e2e_demo.ps1
# One-click Full E2E: auto-starts backend + frontend preview, runs Playwright, cleans up.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\run_full_e2e_demo.ps1 `
#       -PythonExe "D:\codex安装\tools\Python312\python.exe" `
#       -NpmCmd "D:\codex安装\tools\nodejs\npm.cmd"

param(
    [string]$PythonExe = "",
    [string]$NpmCmd = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")

# --- Tool Discovery ---
if (-not $PythonExe) { $PythonExe = $env:PROJECT_A_PYTHON_EXE }
if (-not $PythonExe) { $PythonExe = "python" }
if (-not $NpmCmd) { $NpmCmd = $env:PROJECT_A_NPM_CMD }
if (-not $NpmCmd) { $NpmCmd = "npm" }

Write-Host "=== Full E2E Demo Runner ===" -ForegroundColor Cyan
Write-Host "ProjectRoot : $ProjectRoot"
Write-Host "PythonExe   : $PythonExe"
Write-Host "NpmCmd      : $NpmCmd"
Write-Host ""

# Track processes for cleanup
$backendProc = $null
$frontendProc = $null

function Cleanup-Processes {
    Write-Host ""
    Write-Host "--- Cleanup ---" -ForegroundColor Yellow
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Write-Host "  Stopping frontend (PID $($frontendProc.Id))..."
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($backendProc -and -not $backendProc.HasExited) {
        Write-Host "  Stopping backend (PID $($backendProc.Id))..."
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
    # Also kill any leftover uvicorn / vite preview on our ports
    Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Get-NetTCPConnection -LocalPort 4173 -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Write-Host "  Cleanup done." -ForegroundColor Green
}

trap {
    Cleanup-Processes
    break
}

# --- 0. Kill stale processes on our ports ---
Write-Host "--- Cleaning up stale processes ---" -ForegroundColor Yellow
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort 4173 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

# --- 1. Start Backend ---
Write-Host "--- Starting Backend ---" -ForegroundColor Yellow

$env:STORAGE_BACKEND = "sqlite"
$env:AUTH_ENABLED = "false"
$env:RATE_LIMIT_ENABLED = "false"
$env:METRICS_ENABLED = "false"
$env:VECTOR_BACKEND = "chroma"
$env:CHROMA_PERSIST_DIR = "$ProjectRoot\data\chroma_e2e"
$env:APP_DATABASE_PATH = "$ProjectRoot\data\e2e_app.db"
$env:PYTHONPATH = "$ProjectRoot;$ProjectRoot\backend;$ProjectRoot\.pg_deps;" + $env:PYTHONPATH

$backendProc = Start-Process -FilePath $PythonExe `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory "$ProjectRoot\backend" `
    -PassThru -NoNewWindow

Write-Host "  Backend PID: $($backendProc.Id)"

# Wait for backend healthz
$backendReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/healthz" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $backendReady = $true
            break
        }
    } catch {
        # still waiting
    }
    if ($backendProc.HasExited) {
        Write-Host "  FATAL: Backend process exited unexpectedly (exit code $($backendProc.ExitCode))" -ForegroundColor Red
        Cleanup-Processes
        exit 1
    }
}

if (-not $backendReady) {
    Write-Host "  FATAL: Backend did not become healthy within 30s" -ForegroundColor Red
    Cleanup-Processes
    exit 1
}

Write-Host "  Backend ready (healthz 200)" -ForegroundColor Green

# --- 2. Build & Start Frontend Preview ---
Write-Host "--- Building Frontend ---" -ForegroundColor Yellow

Set-Location "$ProjectRoot\frontend"
$savedEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$buildOutput = & $NpmCmd run build 2>&1
$buildExit = $LASTEXITCODE
$ErrorActionPreference = $savedEAP
if ($buildExit -ne 0) {
    Write-Host "  FATAL: Frontend build failed" -ForegroundColor Red
    $buildOutput | Write-Host
    Cleanup-Processes
    exit 1
}

Write-Host "  Frontend build succeeded" -ForegroundColor Green

Write-Host "--- Starting Frontend Preview ---" -ForegroundColor Yellow

$env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:4173"
# Use npx vite preview directly to control port (package.json preview uses port 4173)
$frontendProc = Start-Process -FilePath $NpmCmd `
    -ArgumentList "run", "preview" `
    -WorkingDirectory "$ProjectRoot\frontend" `
    -PassThru -NoNewWindow

Write-Host "  Frontend PID: $($frontendProc.Id)"

# Wait for frontend
$frontendReady = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:4173/" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $frontendReady = $true
            break
        }
    } catch {
        # still waiting
    }
    if ($frontendProc.HasExited) {
        Write-Host "  FATAL: Frontend process exited unexpectedly (exit code $($frontendProc.ExitCode))" -ForegroundColor Red
        Cleanup-Processes
        exit 1
    }
}

if (-not $frontendReady) {
    Write-Host "  FATAL: Frontend did not become accessible within 20s" -ForegroundColor Red
    Cleanup-Processes
    exit 1
}

Write-Host "  Frontend ready (HTTP 200)" -ForegroundColor Green

# --- 3. Run Playwright E2E ---
Write-Host "--- Running Playwright E2E ---" -ForegroundColor Yellow

Set-Location "$ProjectRoot\frontend"
$savedEAP2 = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $NpmCmd run e2e 2>&1 | Out-Null
$e2eExit = $LASTEXITCODE
$ErrorActionPreference = $savedEAP2

# --- 4. Cleanup ---
Cleanup-Processes

# --- 5. Result ---
Write-Host ""
if ($e2eExit -eq 0) {
    Write-Host "=== FULL E2E PASSED ===" -ForegroundColor Green
    exit 0
} else {
    Write-Host "=== FULL E2E FAILED (exit code $e2eExit) ===" -ForegroundColor Red
    exit 1
}
