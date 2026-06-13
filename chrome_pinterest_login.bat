@echo off
chcp 65001 >nul
cd /d "%~dp0"

set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe
if not exist "%CHROME%" (
  echo Chrome was not found at:
  echo %CHROME%
  pause
  exit /b 1
)

echo.
echo This opens a normal Chrome window with remote debugging enabled.
echo IMPORTANT: close all other Chrome windows first if the browser does not open correctly.
echo.
echo 1. Log in to Pinterest in the Chrome window.
echo 2. Open the target board once.
echo 3. Return to this window and press Enter.
echo.

start "Pinterest Chrome" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\Google\Chrome\User Data" "https://www.pinterest.com/login/"
pause

if not exist ".venv\Scripts\python.exe" (
  echo Python virtual environment was not found.
  echo Expected: .venv\Scripts\python.exe
  pause
  exit /b 1
)

".venv\Scripts\python.exe" "scripts\save_pinterest_session_from_chrome.py"
echo.
".venv\Scripts\python.exe" "scripts\check_pinterest_session.py"
echo.
pause
