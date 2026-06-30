@echo off
echo Starting Productivity Agent Backend...
cd /d "%~dp0"
call .venv\Scripts\activate.bat
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
pause