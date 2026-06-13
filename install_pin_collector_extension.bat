@echo off
chcp 65001 >nul
cd /d "%~dp0"

set CHROME=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe
if not defined CHROME if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe

echo.
echo Chrome extension folder:
echo %cd%\tools\pinterest-board-collector-extension
echo.
echo 1. Turn on Developer mode.
echo 2. Click Load unpacked.
echo 3. Select the folder above.
echo.

if defined CHROME (
  start "" "%CHROME%" "chrome://extensions"
) else (
  echo Chrome was not found automatically.
  echo Open Chrome manually and go to:
  echo chrome://extensions
)
pause
