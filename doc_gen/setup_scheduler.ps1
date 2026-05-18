# setup_scheduler.ps1
# ============================================================
#  Register a Windows Task Scheduler job:
#    Task name : TaiwanWater_DocGen
#    Runs      : doc_generator.py --once
#    Schedule  : Daily at 10:00 AM
#
#  How to run:
#    Double-click  (if .ps1 opens with PowerShell)
#    - OR -
#    powershell -ExecutionPolicy Bypass -File "setup_scheduler.ps1"
# ============================================================

$ErrorActionPreference = "Stop"

$TaskName   = "TaiwanWater_DocGen"
$TaskDesc   = "Taiwan Water - Auto-generate Architecture and Design Document (Word) daily at 10:00 AM"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ScriptPath = Join-Path $ScriptDir "doc_generator.py"
$OutputDir  = Join-Path $ScriptDir "..\docs\generated"

# ── Validate Python ────────────────────────────────────────────────────────────
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Host "[ERROR] Python not found in PATH." -ForegroundColor Red
    Write-Host "        Install Python 3.9+ from https://python.org"
    Read-Host "Press Enter to exit"
    exit 1
}

# ── Check python-docx ─────────────────────────────────────────────────────────
$null = & $PythonExe -c "import docx" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[INFO] Installing python-docx ..." -ForegroundColor Yellow
    & $PythonExe -m pip install python-docx --quiet
}

# ── Ensure output dir exists ──────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$OutputDirFull = (Resolve-Path $OutputDir).Path

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Task   : $TaskName"
Write-Host " Python : $PythonExe"
Write-Host " Script : $ScriptPath"
Write-Host " Output : $OutputDirFull"
Write-Host " Time   : 10:00 AM daily"
Write-Host "============================================"
Write-Host ""

# ── Remove old task ────────────────────────────────────────────────────────────
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# ── Build task ────────────────────────────────────────────────────────────────
$Action = New-ScheduledTaskAction `
    -Execute          $PythonExe `
    -Argument         "`"$ScriptPath`" --once" `
    -WorkingDirectory $ScriptDir

$Trigger = New-ScheduledTaskTrigger -Daily -At "10:00AM"

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit  (New-TimeSpan -Minutes 30) `
    -MultipleInstances   IgnoreNew `
    -RunOnlyIfNetworkAvailable:$false

# ── Register (try elevated, fall back to normal) ──────────────────────────────
$registered = $false

# Attempt 1: current user, RunLevel Highest (needs local admin)
try {
    $principal = New-ScheduledTaskPrincipal `
        -UserId    ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
        -LogonType Interactive `
        -RunLevel  Highest

    Register-ScheduledTask `
        -TaskName    $TaskName `
        -Description $TaskDesc `
        -Action      $Action `
        -Trigger     $Trigger `
        -Settings    $Settings `
        -Principal   $principal `
        -Force `
        -ErrorAction Stop | Out-Null

    $registered = $true
    Write-Host "[OK] Registered with RunLevel Highest (admin privileges detected)." -ForegroundColor Green
} catch {
    Write-Host "[INFO] RunLevel Highest failed ($($_.Exception.Message -replace '\r?\n',' '))" -ForegroundColor Yellow
    Write-Host "       Retrying with RunLevel Normal (no admin required)..." -ForegroundColor Yellow
}

# Attempt 2: current user, RunLevel Normal (no admin needed)
if (-not $registered) {
    try {
        $principal = New-ScheduledTaskPrincipal `
            -UserId    ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
            -LogonType Interactive `
            -RunLevel  Limited

        Register-ScheduledTask `
            -TaskName    $TaskName `
            -Description $TaskDesc `
            -Action      $Action `
            -Trigger     $Trigger `
            -Settings    $Settings `
            -Principal   $principal `
            -Force `
            -ErrorAction Stop | Out-Null

        $registered = $true
        Write-Host "[OK] Registered with RunLevel Normal." -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Could not register task: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Manual alternative - run this in an Administrator PowerShell:" -ForegroundColor Yellow
        Write-Host "  schtasks /Create /TN `"$TaskName`" /TR `"`"$PythonExe`" `"$ScriptPath`" --once`" /SC DAILY /ST 10:00 /F"
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# ── Verify ─────────────────────────────────────────────────────────────────────
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host ""
    Write-Host "=== Task registered OK ===" -ForegroundColor Green
    Write-Host "  Name  : $($task.TaskName)"
    Write-Host "  State : $($task.State)"
    Write-Host "  Output: $OutputDirFull"
    Write-Host ""
    Write-Host "--- Useful commands ---" -ForegroundColor Cyan
    Write-Host "  Run now    : Start-ScheduledTask -TaskName '$TaskName'"
    Write-Host "  Last result: Get-ScheduledTask '$TaskName' | Get-ScheduledTaskInfo | Select LastRunTime,LastTaskResult"
    Write-Host "  View log   : Get-Content '$OutputDirFull\doc_gen.log' -Tail 30"
    Write-Host "  Remove     : Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
} else {
    Write-Host "[WARN] Task may not have registered correctly. Check Task Scheduler manually." -ForegroundColor Yellow
}

# ── Offer test run ─────────────────────────────────────────────────────────────
Write-Host ""
$ans = Read-Host "Run a test generation RIGHT NOW? [Y/n]"
if ($ans -eq '' -or $ans -match '^[Yy]') {
    Write-Host ""
    Write-Host "Running doc_generator.py --once ..." -ForegroundColor Cyan
    & $PythonExe $ScriptPath --once
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[OK] Document generated. Check: $OutputDirFull" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Generation failed. Check log: $OutputDirFull\doc_gen.log" -ForegroundColor Red
    }
}

Write-Host ""
Read-Host "Press Enter to close"
