# AI Supply Assistant - Deployment Guide

## Quick Start

1. **Configure Database**
   - Copy `.env.example` to `.env`
   - Edit `.env` with your SQL Server credentials:
     ```
     DB_CONN_STR=mssql+pyodbc://user:password@SERVER\INSTANCE/database?driver=ODBC+Driver+17+for+SQL+Server
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
