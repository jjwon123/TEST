@echo off
setlocal

set "TABLE=%~1"
if "%TABLE%"=="" set "TABLE=runs\_reference_search_benchmark\benchmark-evaluation.csv"

set "OUTPUT=%~2"
if "%OUTPUT%"=="" set "OUTPUT=assets\references\feedback.jsonl"

set "MODE=%~3"
if "%MODE%"=="" set "MODE=human"

echo Appending filled human feedback rows...
echo Table: %TABLE%
echo Output: %OUTPUT%
echo Mode: %MODE%

if /I "%MODE%"=="ai" (
  ".venv\Scripts\python.exe" scripts\reference_vision.py feedback-from-table --table "%TABLE%" --output "%OUTPUT%" --include-ai-decisions
) else (
  ".venv\Scripts\python.exe" scripts\reference_vision.py feedback-from-table --table "%TABLE%" --output "%OUTPUT%"
)
endlocal
