@echo off
echo Starting Productivity Agent Frontend...
cd /d "%~dp0"
"C:\Users\jayes\AppData\Local\Programs\Python\Python311\Scripts\streamlit.exe" run frontend/app.py
pause
