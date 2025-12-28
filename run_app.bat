@echo off
REM AI Supply Assistant Launcher
REM This script starts the Streamlit application

echo Starting AI Supply Assistant...
echo.
echo Note: First run may take longer as the LLM model loads.
echo.

REM Check for .env file
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Please copy .env.example to .env and configure your settings.
    echo.
    copy .env.example .env
    echo Created .env from template. Please edit it with your database credentials.
    pause
)

REM Check for models
if not exist "models\*.gguf" (
    echo WARNING: No GGUF model found in models/ folder.
    echo For Local LLM, download a model from HuggingFace.
    echo Recommended: Qwen2.5-3B-Instruct (~2GB)
    echo.
)

REM Start the application
streamlit run main.py --server.headless true --server.port 8501

pause
