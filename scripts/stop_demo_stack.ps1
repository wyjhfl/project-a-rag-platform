$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$tmpDir = Join-Path $repoRoot "tmp"
$backendPidPath = Join-Path $tmpDir "demo_backend.pid"
$frontendPidPath = Join-Path $tmpDir "demo_frontend.pid"
$defaultDemoEnvPath = Join-Path $repoRoot ".env.demo"
$demoExamplePath = Join-Path $repoRoot ".env.demo.example"

function Stop-ProcessFromPidFile {
    param([string]$PidFile)
    if (-not (Test-Path $PidFile)) {
        return
    }

    $pidValue = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
    if ($pidValue) {
        $proc = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $proc.Id -Force
            Write-Host "Stopped PID $($proc.Id)"
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

function Import-DotEnvFile {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return
    }

    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        $parts = $trimmed.Split("=", 2)
        if ($parts.Count -ne 2) {
            continue
        }

        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

function Stop-ProcessFromPort {
    param([int]$Port)
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) {
        return
    }

    $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pidValue in $pids) {
        $proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $proc.Id -Force
            Write-Host "Stopped port $Port owner PID $($proc.Id)"
        }
    }
}

if (Test-Path $defaultDemoEnvPath) {
    Import-DotEnvFile -Path $defaultDemoEnvPath
} else {
    Import-DotEnvFile -Path $demoExamplePath
}

$backendPort = if ($env:DEMO_BACKEND_PORT) { [int]$env:DEMO_BACKEND_PORT } else { 18082 }
$frontendPort = if ($env:DEMO_FRONTEND_PORT) { [int]$env:DEMO_FRONTEND_PORT } else { 4175 }

Stop-ProcessFromPidFile -PidFile $frontendPidPath
Stop-ProcessFromPidFile -PidFile $backendPidPath
Stop-ProcessFromPort -Port $frontendPort
Stop-ProcessFromPort -Port $backendPort
