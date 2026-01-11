"""
PyInstaller Build Script for AI Supply Assistant.
Creates a portable Windows executable (.exe) that can be distributed without Python installation.

Usage:
    python build_exe.py

Requirements:
    pip install pyinstaller

Output:
    dist/AI_Supply_Assistant.exe
"""

import os
import shutil
import subprocess
import sys


def check_requirements():
    """Check if PyInstaller is installed."""
    try:
        import PyInstaller

        print(f"✅ PyInstaller version: {PyInstaller.__version__}")
        return True
    except ImportError:
        print("❌ PyInstaller not installed. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        return True


def clean_build_dirs():
    """Clean previous build artifacts."""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🧹 Cleaned {dir_name}/")


def create_spec_file():
    """Create PyInstaller spec file with optimized settings."""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for AI Supply Assistant

import os
import sys

block_cipher = None

# Project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(SPEC))

# Data files to include
datas = [
    # Include .env.example as template
    (os.path.join(PROJECT_ROOT, '.env.example'), '.'),
    # Include models folder (user places GGUF files here)
    (os.path.join(PROJECT_ROOT, 'models'), 'models'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'streamlit',
    'streamlit.web.cli',
    'streamlit.runtime',
    'streamlit.runtime.scriptrunner',
    'pandas',
    'plotly',
    'plotly.express',
    'plotly.graph_objects',
    'sqlalchemy',
    'sqlalchemy.dialects.mssql',
    'pyodbc',
    'sklearn',
    'sklearn.linear_model',
    'sklearn.ensemble',
    'statsmodels',
    'statsmodels.tsa.holtwinters',
    'google.generativeai',
    'llama_cpp',
    'pydantic',
    'dotenv',
    'bcrypt',
    'cryptography',
    # Project modules
    'src.db_connector',
    'src.services.mrp_simulator',
    'src.services.alerts',
    'src.ai_engine.local_llm',
    'src.gui.views.mrp_view',
    'src.gui.views.assistant',
    'src.security.auth',
]

a = Analysis(
    ['main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AI_Supply_Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for Streamlit output
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path if available
)
"""

    with open("ai_supply_assistant.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    print("📝 Created ai_supply_assistant.spec")


def create_launcher_script():
    """Create a launcher batch file for the packaged app."""
    launcher_content = """@echo off
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
if not exist "models\\*.gguf" (
    echo WARNING: No GGUF model found in models/ folder.
    echo For Local LLM, download a model from HuggingFace.
    echo Recommended: Qwen2.5-3B-Instruct (~2GB)
    echo.
)

REM Start the application
streamlit run main.py --server.headless true --server.port 8501

pause
"""

    with open("run_app.bat", "w", encoding="utf-8") as f:
        f.write(launcher_content)
    print("📝 Created run_app.bat launcher")


def create_readme_deployment():
    """Create deployment README."""
    readme_content = """# AI Supply Assistant - Deployment Guide

## Quick Start

1. **Configure Database**
   - Copy `.env.example` to `.env`
   - Edit `.env` with your SQL Server credentials:
     ```
     DB_CONN_STR=mssql+pyodbc://user:password@SERVER\\INSTANCE/database?driver=ODBC+Driver+17+for+SQL+Server
     ```

2. **Configure AI (Optional)**
   - For Google Gemini: Add `GEMINI_API_KEY` to `.env`
   - For Local LLM: Download a GGUF model to `models/` folder

3. **Run the Application**
   - Double-click `run_app.bat`
   - Or run: `streamlit run main.py`
   - Open http://localhost:8501 in your browser

## Local LLM Setup

For fully offline operation:

1. Download a GGUF model:
   - Recommended: [Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF)
   - File: `qwen2.5-3b-instruct-q4_k_m.gguf` (~2GB)

2. Place in `models/` folder

3. Update `.env`:
   ```
   LOCAL_LLM_PATH=models/qwen2.5-3b-instruct-q4_k_m.gguf
   ```

## Requirements

- Windows 10/11
- ODBC Driver 17 for SQL Server
- 4GB+ RAM (8GB+ recommended for Local LLM)

## Troubleshooting

### Database Connection Failed
- Verify SQL Server is running
- Check firewall allows TCP/IP connections
- Ensure ODBC Driver 17 is installed

### Local LLM Not Working
- Verify `LOCAL_LLM_PATH` points to valid .gguf file
- Check you have enough RAM
- Try smaller model (Qwen2-1.5B: 1.1GB)
"""

    with open("DEPLOYMENT.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("📝 Created DEPLOYMENT.md")


def build_executable():
    """Run PyInstaller to create the executable."""
    print("\n🔨 Building executable...")
    print("This may take several minutes...\n")

    # Use spec file if exists, otherwise use basic command
    if os.path.exists("ai_supply_assistant.spec"):
        cmd = [sys.executable, "-m", "PyInstaller", "ai_supply_assistant.spec", "--clean"]
    else:
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--name=AI_Supply_Assistant",
            "--onefile",  # Single executable
            "--console",  # Show console for Streamlit
            "--clean",
            "main.py",
        ]

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print("\n✅ Build successful!")
        print("📦 Output: dist/AI_Supply_Assistant.exe")
        return True
    else:
        print("\n❌ Build failed!")
        return False


def main():
    """Main build process."""
    print("=" * 50)
    print("AI Supply Assistant - Build Script")
    print("=" * 50)
    print()

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Ask user for clean build
    print()
    print("Options:")
    print("1. Full build (clean + compile)")
    print("2. Create packaging files only")
    print("3. Build only (keep existing files)")
    print()

    choice = input("Select option [1-3]: ").strip()

    if choice == "1":
        clean_build_dirs()
        create_spec_file()
        create_launcher_script()
        create_readme_deployment()
        build_executable()
    elif choice == "2":
        create_spec_file()
        create_launcher_script()
        create_readme_deployment()
        print("\n✅ Packaging files created!")
        print("Run 'pyinstaller ai_supply_assistant.spec' to build.")
    elif choice == "3":
        build_executable()
    else:
        print("Invalid option. Exiting.")
        sys.exit(1)


if __name__ == "__main__":
    main()
