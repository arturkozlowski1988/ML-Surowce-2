@echo off
REM ============================================
REM AI Supply Assistant - Installer Launcher
REM ============================================
REM This script launches the PowerShell installer
REM with Administrator privileges
REM ============================================

echo.
echo ========================================
echo   AI Supply Assistant - Installer
echo ========================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Requesting Administrator privileges...
    echo.
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo [OK] Running with Administrator privileges
echo.

REM Check if PowerShell is available
powershell -Command "Write-Host 'PowerShell OK'" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PowerShell is not available!
    echo Please install Windows PowerShell 5.1 or later.
    pause
    exit /b 1
)

REM Run the PowerShell installer script
echo Starting installation...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Install-AISupplyAssistant.ps1" -InstallPath "%~dp0"

echo.
echo Installation complete.
pause
