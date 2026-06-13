@echo off
setlocal

set "PORT=%~1"
if "%PORT%"=="" set "PORT=5177"

set "PYTHON_EXE=.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo Starting Brand Event Console on http://127.0.0.1:%PORT%
"%PYTHON_EXE%" scripts\console_server.py --port %PORT%

endlocal
