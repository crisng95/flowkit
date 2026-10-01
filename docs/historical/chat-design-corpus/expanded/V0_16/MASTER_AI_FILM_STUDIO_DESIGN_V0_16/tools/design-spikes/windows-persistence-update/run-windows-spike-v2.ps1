param(
  [string]$Python = "python",
  [string]$OutDir = ".\spike-output-v2"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "MASTER STUDIO - Windows Persistence/Update Design Spike V2"
Write-Host "Design spike only. Does not modify production project data."

$ScriptPath = Join-Path $PSScriptRoot "windows_persistence_spike_v2.py"
& $Python $ScriptPath --out $OutDir

if ($LASTEXITCODE -ne 0) {
  throw "Spike failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Results:"
Get-Content (Join-Path $OutDir "windows_persistence_spike_results_v2.json")
