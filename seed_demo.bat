@echo off
REM DEMO ONLY — remove before production
echo Seeding demo data for user Mayur...
cd /d "%~dp0"
python -m backend.seed_demo --force
pause
