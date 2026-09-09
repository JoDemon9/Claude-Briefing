@echo off
cd /d "%~dp0"
python scripts\morning-runner.py >> morning-runner.log 2>&1
