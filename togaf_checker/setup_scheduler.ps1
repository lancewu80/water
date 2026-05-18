# setup_scheduler.ps1
# --------------------
# Registers a Windows Task Scheduler task to run the TOGAF Checker daily at 10:00.
# Double-click setup_scheduler.bat to invoke this script, or run directly:
#   powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1
#
# Task name : TaiwanWater_TOGAFChecker
# Trigger   : Daily at 10:00
# Action    : python  <path>\togaf_checker\main.py  --once
# Run as    : current user (no admin required)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$TaskName    = "TaiwanWater_TOGAFChecker"
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$MainScript  = Join-Path $ScriptDir "main.py"
$ProjectRoot = Split-Path -Parent $ScriptDir
$OutputDir   = Join-Path $ProjectRoot "docs\generated"

# Resolve python executable
$PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Host "[ERROR] python.exe not found in PATH. Install Python 3.9+ and retry." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================================"
Write-Host "  TOGAF Checker — Windows Task Scheduler Setup"
Write-Host "========================================================"
Write-Host "  Task name   : $TaskName"
Write-Host "  Python      : $PythonExe"
Write-Host "  Script      : $MainScript"
Write-Host "  Project root: $ProjectRoot"
Write-Host "  Output dir  : $OutputDir"
Write-Host "  Schedule    : Daily at 10:00"
Write-Host "========================================================"
Write-Host ""

# Remove existing task if present
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[INFO] Removing existing task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$Action  = New-ScheduledTaskAction `
               -Execute $PythonExe `
               -Argument "`"$MainScript`" --once --root `"$ProjectRoot`" --out `"$OutputDir`"" `
               -WorkingDirectory $ScriptDir

$Trigger = New-ScheduledTaskTrigger -Daily -At "10:00"

$Settings = New-ScheduledTaskSettingsSet `
                -StartWhenAvailable `
                -RunOnlyIfNetworkAvailable:$false `
                -ExecutionTimeLimit (New-TimeSpan -Hours 1)

$Principal = New-ScheduledTaskPrincipal `
                 -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
                 -LogonType Interactive `
                 -RunLevel Limited

# Attempt 1: Register with Limited privilege (no UAC prompt)
Write-Host "[INFO] Registering scheduled task..."
try {
    Register-ScheduledTask `
        -TaskName  $TaskName `
        -Action    $Action `
        -Trigger   $Trigger `
        -Settings  $Settings `
        -Principal $Principal `
        -Force `
        -ErrorAction Stop | Out-Null

    Write-Host "[OK] Task '$TaskName' registered successfully." -ForegroundColor Green
}
catch {
    Write-Host "[WARN] Limited registration failed: $_" -ForegroundColor Yellow
    Write-Host "[INFO] Retrying with Highest RunLevel (admin may be required)..."

    $PrincipalAdmin = New-ScheduledTaskPrincipal `
                          -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
                          -LogonType Interactive `
                          -RunLevel Highest

    try {
        Register-ScheduledTask `
            -TaskName  $TaskName `
            -Action    $Action `
            -Trigger   $Trigger `
            -Settings  $Settings `
            -Principal $PrincipalAdmin `
            -Force `
            -ErrorAction Stop | Out-Null

        Write-Host "[OK] Task '$TaskName' registered with Highest RunLevel." -ForegroundColor Green
    }
    catch {
        Write-Host "[ERROR] Registration failed: $_" -ForegroundColor Red
        Write-Host "        Try running this script as Administrator." -ForegroundColor Yellow
        exit 1
    }
}

# Verify registration
$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($task) {
    Write-Host ""
    Write-Host "Task details:"
    Write-Host "  State   : $($task.State)"
    Write-Host "  Next run: $(($task | Get-ScheduledTaskInfo).NextRunTime)"
    Write-Host ""
}

# Ask user whether to do a test run
Write-Host "========================================================"
$answer = Read-Host "Run a test now? (Y/N)"
if ($answer -match '^[Yy]') {
    Write-Host ""
    Write-Host "[INFO] Starting test run..." -ForegroundColor Cyan
    & $PythonExe $MainScript --once --root $ProjectRoot --out $OutputDir
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Test run completed successfully." -ForegroundColor Green
        Write-Host "     Report saved to: $OutputDir" -ForegroundColor Green
    }
    else {
        Write-Host "[ERROR] Test run failed (exit code $LASTEXITCODE)." -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Setup complete. Press any key to close..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
