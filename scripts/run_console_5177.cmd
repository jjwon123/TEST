@echo off
cd /d C:\tmp\loop-project
".venv\Scripts\python.exe" "scripts\console_server.py" --port 5177 > C:\tmp\loop-console-5177.log 2>&1
