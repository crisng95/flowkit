# Windows Persistence / Update Design Spike Harness

This is a **design-evidence harness**, not product code.

## Prerequisites

- Windows 10/11
- Python 3.11+ available as `python`
- run from PowerShell

## Run

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\run-windows-spike.ps1
```

Optional:

```powershell
.\run-windows-spike.ps1 -Python "py" -OutDir ".\results"
```

## What it tests

1. SQLite WAL + FULL with 12 concurrent writer threads.
2. committed vs uncommitted transaction behavior after abrupt child-process exit.
3. interrupted migration marker + deterministic resume.
4. SQLite backup/restore integrity.
5. refusal to write a schema newer than the supported maximum.

## What it does NOT prove

- physical power-cut durability through disk controller caches;
- Electron updater behavior;
- provider networking;
- user production data safety.

Run it only in its own test folder.
