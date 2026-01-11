@echo off
REM ============================================
REM AI Supply Assistant - Network Server Launcher
REM For Windows Server deployment
REM ============================================
REM
REM This script starts the Streamlit server configured
REM for network access from other computers on the LAN.
REM
REM PREREQUISITES:
REM   1. Python 3.9+ installed
REM   2. Dependencies: pip install -r requirements.txt
REM   3. .env file configured with database credentials
REM   4. Windows Firewall rule for port 8501
REM
REM FIREWALL SETUP (run as Administrator):
REM   netsh advfirewall firewall add rule name="AI Supply Assistant" ^
REM       dir=in action=allow protocol=tcp localport=8501
REM
REM ============================================

setlocal EnableDelayedExpansion

echo.
echo ========================================
echo   AI Supply Assistant - Network Server
echo ========================================
echo.

REM Get computer IP address for display
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    set IP=!IP:~1!
    goto :found_ip
)
:found_ip

echo Server IP Address: %IP%
echo Default Port: 8501
echo.
echo Users can access the application at:
echo   http://%IP%:8501
echo.

REM Check for .env file
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo Please copy .env.example to .env and configure your settings.
    echo.
    if exist ".env.example" (
        copy .env.example .env
        echo Created .env from template. Please edit it with your database credentials.
    )
    pause
    exit /b 1
)

REM Check for models
if not exist "models\*.gguf" (
    echo [INFO] No GGUF model found in models/ folder.
    echo For Local LLM, download a model from HuggingFace.
    echo Recommended: Qwen2.5-7B-Instruct
    echo.
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.9+
    pause
    exit /b 1
)

echo Starting Streamlit server...
echo Press Ctrl+C to stop the server.
echo.

REM Start Streamlit with network configuration
REM Configuration is loaded from .streamlit/config.toml
REM Override address explicitly to ensure network access
streamlit run main.py --server.address 0.0.0.0 --server.port 8501 --server.headless true

pause
