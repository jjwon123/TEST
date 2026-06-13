@echo off
setlocal

set "EVENT_DIR=%~1"
if "%EVENT_DIR%"=="" set "EVENT_DIR=events\sample"

set "QUERY_LIMIT=%~2"
if "%QUERY_LIMIT%"=="" set "QUERY_LIMIT=1"

set "PER_QUERY_LIMIT=%~3"
if "%PER_QUERY_LIMIT%"=="" set "PER_QUERY_LIMIT=3"

set "SELECT_COUNT=%~4"
if "%SELECT_COUNT%"=="" set "SELECT_COUNT=1"

set "REVIEW_LIMIT=%~5"
if "%REVIEW_LIMIT%"=="" set "REVIEW_LIMIT=1"

echo Running event automation with AI-reviewed references...
echo Event: %EVENT_DIR%

".venv\Scripts\python.exe" scripts\run_event_with_reference_ai.py ^
  --event "%EVENT_DIR%" ^
  --query-limit %QUERY_LIMIT% ^
  --per-query-limit %PER_QUERY_LIMIT% ^
  --select-count %SELECT_COUNT% ^
  --review-limit %REVIEW_LIMIT%

endlocal
