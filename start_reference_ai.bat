@echo off
setlocal

set "OLLAMA_EXE=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not exist "%OLLAMA_EXE%" set "OLLAMA_EXE=C:\tmp\ollama\ollama.exe"

if not exist "%OLLAMA_EXE%" (
  echo [ERROR] Ollama not found: %OLLAMA_EXE%
  echo Install Ollama or set OLLAMA_EXE to its executable path.
  exit /b 1
)

echo Starting local reference AI server...
start "Reference AI - Ollama" /min "%OLLAMA_EXE%" serve
powershell -NoProfile -Command "Start-Sleep -Seconds 5"

echo Checking local AI health...
".venv\Scripts\python.exe" scripts\reference_vision.py health
endlocal
