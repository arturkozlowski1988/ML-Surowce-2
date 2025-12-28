# -*- mode: python ; coding: utf-8 -*-
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
    'pandas',
    'plotly',
    'plotly.express',
    'sqlalchemy',
    'pyodbc',
    'sklearn',
    'statsmodels',
    'google.generativeai',
    'llama_cpp',
    'pydantic',
    'dotenv',
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
