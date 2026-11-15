# Flow Kit - persistent agent launcher
#
# Starts the Python agent as a fully detached Windows process so it keeps
# running after this PowerShell window (or the shell that launched it)
# closes. Safe to re-run: it checks /health first and does nothing if an
# agent is already listening on port 8100.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File start_agent.ps1
#   powershell -ExecutionPolicy Bypass -File start_agent.ps1 -FlowProjectId <uuid>

param(
    [string]$FlowProjectId = $env:FLOW_PROJECT_ID
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$PythonExe = Join-Path $RepoRoot "venv\Scripts\python.exe"
$OutLog = Join-Path $RepoRoot "agent_out.log"
$ErrLog = Join-Path $RepoRoot "agent_err.log"

try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8100/health" -TimeoutSec 2
    if ($resp.status -eq "ok") {
        Write-Host "Agent already running (uptime $($resp.ws.uptime_s)s). Nothing to do."
        exit 0
    }
} catch {
    # Not running - fall through and start it.
}

if (-not $FlowProjectId) {
    Write-Error "FLOW_PROJECT_ID not set. Pass -FlowProjectId <uuid> or set the env var first."
    exit 1
}

if (-not (Test-Path $PythonExe)) {
    Write-Error "venv not found at $PythonExe. Run setup first (see README.md)."
    exit 1
}

$env:FLOW_PROJECT_ID = $FlowProjectId

$proc = Start-Process -FilePath $PythonExe `
    -ArgumentList "-m", "agent.main" `
    -WorkingDirectory $RepoRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -PassThru

Start-Sleep -Seconds 3

try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8100/health" -TimeoutSec 5
    Write-Host "Agent started (PID $($proc.Id)). Status: $($resp.status)"
} catch {
    Write-Warning "Agent process started (PID $($proc.Id)) but /health did not respond yet. Check $ErrLog"
}
