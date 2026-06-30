@echo off
echo Starting Productivity Agent Frontend...
cd /d "%~dp0"
call .venv\Scripts\activate.bat
streamlit run frontend/app.py
pause