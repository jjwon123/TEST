@echo off
setlocal

set "CASE_ID=%~1"
if "%CASE_ID%"=="" set "CASE_ID=tube-spring"

set "QUERY_LIMIT=%~2"
if "%QUERY_LIMIT%"=="" set "QUERY_LIMIT=1"

set "PER_QUERY_LIMIT=%~3"
if "%PER_QUERY_LIMIT%"=="" set "PER_QUERY_LIMIT=3"

set "SELECT_COUNT=%~4"
if "%SELECT_COUNT%"=="" set "SELECT_COUNT=2"

set "REVIEW_LIMIT=%~5"
if "%REVIEW_LIMIT%"=="" set "REVIEW_LIMIT=3"

echo Running Pinterest reference search + Qwen-VL review...
echo Case: %CASE_ID%
echo Query limit: %QUERY_LIMIT%
echo Per-query limit: %PER_QUERY_LIMIT%
echo Select count: %SELECT_COUNT%
echo Review limit: %REVIEW_LIMIT%

".venv\Scripts\python.exe" scripts\reference_search_benchmark.py ^
  --prepare ^
  --run ^
  --case "%CASE_ID%" ^
  --query-limit %QUERY_LIMIT% ^
  --per-query-limit %PER_QUERY_LIMIT% ^
  --select-count %SELECT_COUNT% ^
  --reviewer qwen ^
  --review-limit %REVIEW_LIMIT%

echo.
echo Outputs:
echo runs\_reference_search_benchmark\benchmark-report.md
echo runs\_reference_search_benchmark\benchmark-evaluation.csv
echo runs\_reference_search_benchmark\%CASE_ID%\references\qwen-reviewed-candidates.json
endlocal
