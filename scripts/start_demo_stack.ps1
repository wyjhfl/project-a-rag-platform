param(
    [string]$DemoEnvFile = ".env.demo",
    [switch]$StopExisting
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$tmpDir = Join-Path $repoRoot "tmp"
$backendPidPath = Join-Path $tmpDir "demo_backend.pid"
$frontendPidPath = Join-Path $tmpDir "demo_frontend.pid"
$backendOutLogPath = Join-Path $tmpDir "demo_backend.out.log"
$backendErrLogPath = Join-Path $tmpDir "demo_backend.err.log"
$frontendOutLogPath = Join-Path $tmpDir "demo_frontend.out.log"
$frontendErrLogPath = Join-Path $tmpDir "demo_frontend.err.log"

if (-not (Test-Path $tmpDir)) {
    New-Item -ItemType Directory -Path $tmpDir | Out-Null
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

        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

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
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 60
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "Timed out waiting for $Url"
}

$defaultEnvPath = Join-Path $repoRoot ".env"
$demoEnvPath = Join-Path $repoRoot $DemoEnvFile
$demoExamplePath = Join-Path $repoRoot ".env.demo.example"

Import-DotEnvFile -Path $defaultEnvPath
if (Test-Path $demoEnvPath) {
    Import-DotEnvFile -Path $demoEnvPath
    $activeDemoEnvPath = $demoEnvPath
} else {
    Import-DotEnvFile -Path $demoExamplePath
    $activeDemoEnvPath = $demoExamplePath
}

if (-not $env:DEEPSEEK_API_KEY) {
    throw "DEEPSEEK_API_KEY is missing. Put it in .env before starting the public demo stack."
}

$env:LLM_PROVIDER = "deepseek"
$env:LLM_MODEL = if ($env:LLM_MODEL) { $env:LLM_MODEL } else { "deepseek-chat" }
$env:LLM_API_KEY = $env:DEEPSEEK_API_KEY
$env:LLM_BASE_URL = if ($env:DEEPSEEK_BASE_URL) { $env:DEEPSEEK_BASE_URL } else { "https://api.deepseek.com/v1" }
$env:STORAGE_BACKEND = "sqlite"
$env:VECTOR_BACKEND = "chroma"
$env:CACHE_ENABLED = "false"
$env:GRAPH_RETRIEVAL_ENABLED = "false"
$env:MULTIMODAL_BACKEND = if ($env:MULTIMODAL_BACKEND) { $env:MULTIMODAL_BACKEND } else { "sidecar" }

$backendHost = if ($env:DEMO_BACKEND_HOST) { $env:DEMO_BACKEND_HOST } else { "127.0.0.1" }
$backendPort = if ($env:DEMO_BACKEND_PORT) { $env:DEMO_BACKEND_PORT } else { "18082" }
$frontendHost = if ($env:DEMO_FRONTEND_HOST) { $env:DEMO_FRONTEND_HOST } else { "127.0.0.1" }
$frontendPort = if ($env:DEMO_FRONTEND_PORT) { $env:DEMO_FRONTEND_PORT } else { "4175" }
$env:VITE_API_BASE_URL = "http://${backendHost}:${backendPort}"

if ($StopExisting) {
    Stop-ProcessFromPidFile -PidFile $backendPidPath
    Stop-ProcessFromPidFile -PidFile $frontendPidPath
}

$backendArgs = @(
    "-m", "uvicorn",
    "app.main:app",
    "--app-dir", "backend",
    "--host", $backendHost,
    "--port", $backendPort
)
$backendProcess = Start-Process -FilePath "python" `
    -ArgumentList $backendArgs `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $backendOutLogPath `
    -RedirectStandardError $backendErrLogPath `
    -PassThru
Set-Content -Path $backendPidPath -Value $backendProcess.Id -Encoding utf8

try {
    Wait-HttpReady -Url "http://${backendHost}:${backendPort}/health"
} catch {
    Stop-ProcessFromPidFile -PidFile $backendPidPath
    throw "Backend failed to become ready. See $backendOutLogPath and $backendErrLogPath"
}

$frontendCommand = ".\node_modules\.bin\vite.cmd --host $frontendHost --port $frontendPort"
$frontendProcess = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", $frontendCommand `
    -WorkingDirectory (Join-Path $repoRoot "frontend") `
    -WindowStyle Hidden `
    -RedirectStandardOutput $frontendOutLogPath `
    -RedirectStandardError $frontendErrLogPath `
    -PassThru
Set-Content -Path $frontendPidPath -Value $frontendProcess.Id -Encoding utf8

try {
    Wait-HttpReady -Url "http://${frontendHost}:${frontendPort}/"
} catch {
    Stop-ProcessFromPidFile -PidFile $frontendPidPath
    Stop-ProcessFromPidFile -PidFile $backendPidPath
    throw "Frontend failed to become ready. See $frontendOutLogPath and $frontendErrLogPath"
}

Write-Host "Demo env file: $activeDemoEnvPath"
Write-Host "Backend:  http://${backendHost}:${backendPort}/health"
Write-Host "Frontend: http://${frontendHost}:${frontendPort}/"
Write-Host "Logs:"
Write-Host "  $backendOutLogPath"
Write-Host "  $backendErrLogPath"
Write-Host "  $frontendOutLogPath"
Write-Host "  $frontendErrLogPath"
