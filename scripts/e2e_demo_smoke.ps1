# e2e_demo_smoke.ps1
# End-to-end demo smoke test: checks backend healthz/readyz and frontend accessibility.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\e2e_demo_smoke.ps1
#
# Exits 0 if all checks pass, 1 otherwise.

$ErrorActionPreference = "Stop"

$BackendHost   = if ($env:BACKEND_HOST) { $env:BACKEND_HOST } else { "localhost" }
$BackendPort   = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }
$FrontendHost  = if ($env:FRONTEND_HOST) { $env:FRONTEND_HOST } else { "localhost" }
$FrontendPort  = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "5173" }

$BackendBase   = "http://${BackendHost}:${BackendPort}"
$FrontendBase  = "http://${FrontendHost}:${FrontendPort}"

$allPassed = $true

function Test-Endpoint {
    param(
        [string]$Label,
        [string]$Url,
        [int]$ExpectedStatus = 200
    )
    try {
        $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        if ($resp.StatusCode -eq $ExpectedStatus) {
            Write-Host "  $Label : PASSED (HTTP $($resp.StatusCode))" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  $Label : FAILED (expected $ExpectedStatus, got $($resp.StatusCode))" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "  $Label : FAILED ($($_.Exception.Message))" -ForegroundColor Red
        return $false
    }
}

Write-Host "=== E2E Demo Smoke Test ===" -ForegroundColor Cyan
Write-Host "  Backend : $BackendBase"
Write-Host "  Frontend: $FrontendBase"
Write-Host ""

# --- Backend checks ---
Write-Host "--- Backend Checks ---" -ForegroundColor Yellow

$healthzOk = Test-Endpoint -Label "GET /healthz" -Url "$BackendBase/healthz"
if (-not $healthzOk) {
    Write-Host "  HINT: Start the backend with:" -ForegroundColor DarkGray
    Write-Host "        cd backend && uvicorn app.main:app --host 0.0.0.0 --port $BackendPort" -ForegroundColor DarkGray
}

$readyzOk = Test-Endpoint -Label "GET /readyz"  -Url "$BackendBase/readyz"
if (-not $readyzOk) {
    Write-Host "  HINT: Ensure all backend dependencies (DB, Redis, etc.) are running." -ForegroundColor DarkGray
}

if (-not ($healthzOk -and $readyzOk)) { $allPassed = $false }

Write-Host ""

# --- Frontend check ---
Write-Host "--- Frontend Check ---" -ForegroundColor Yellow

$frontendOk = Test-Endpoint -Label "GET /" -Url "$FrontendBase/"
if (-not $frontendOk) {
    Write-Host "  HINT: Start the frontend with:" -ForegroundColor DarkGray
    Write-Host "        cd frontend && npm run dev -- --port $FrontendPort" -ForegroundColor DarkGray
}

if (-not $frontendOk) { $allPassed = $false }

Write-Host ""

# --- Summary ---
Write-Host "=====================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "ALL CHECKS PASSED" -ForegroundColor Green
    exit 0
} else {
    Write-Host "SOME CHECKS FAILED" -ForegroundColor Red
    exit 1
}
