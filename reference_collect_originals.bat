@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment was not found.
  echo Expected: .venv\Scripts\python.exe
  pause
  exit /b 1
)

".venv\Scripts\python.exe" "scripts\collect_pinterest_originals.py"
echo.
pause

