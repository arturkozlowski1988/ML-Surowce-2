@echo off
REM ============================================
REM AI Supply Assistant - Uninstaller Launcher
REM ============================================

echo.
echo ========================================
echo   AI Supply Assistant - Uninstaller
echo ========================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Requesting Administrator privileges...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo [OK] Running with Administrator privileges
echo.
echo This will remove the Windows Service and firewall rules.
echo Application files will NOT be deleted.
echo.

set /p confirm="Continue? (Y/n): "
if /i "%confirm%"=="n" (
    echo Cancelled.
    exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Uninstall-AISupplyAssistant.ps1" -RemoveFirewall

pause
