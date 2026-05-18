@echo off
chcp 65001 >nul 2>&1
REM ============================================================
REM  setup_scheduler.bat  --  launcher for setup_scheduler.ps1
REM
REM  Double-click this file OR run from cmd.exe.
REM  It calls the PowerShell script which handles everything.
REM ============================================================

SET PS_SCRIPT=%~dp0setup_scheduler.ps1

powershell.exe -NoLogo -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

IF %ERRORLEVEL% NEQ 0 (
    ECHO.
    ECHO [ERROR] PowerShell script exited with error %ERRORLEVEL%.
    ECHO         Make sure PowerShell 5.1+ is installed.
    PAUSE
)
