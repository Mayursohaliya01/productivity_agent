@echo off
echo Starting Productivity Agent Backend...
cd /d "%~dp0"
"C:\Users\jayes\AppData\Local\Programs\Python\Python311\Scripts\uvicorn.exe" backend.main:app --host 0.0.0.0 --port 8001 --reload
pause
