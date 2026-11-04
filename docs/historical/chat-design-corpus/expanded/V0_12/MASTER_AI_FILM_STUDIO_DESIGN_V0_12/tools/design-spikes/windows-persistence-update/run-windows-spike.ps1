param(
  [string]$Python = "python",
  [string]$OutDir = ".\spike-output"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "MASTER STUDIO — Windows Persistence/Update Design Spike"
Write-Host "This is a DESIGN SPIKE. It does not modify production project data."

$script = Join-Path $PSScriptRoot "windows_persistence_spike.py"
& $Python $script --out $OutDir

if ($LASTEXITCODE -ne 0) {
  throw "Spike failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Results:"
Get-Content (Join-Path $OutDir "windows_persistence_spike_results.json")
