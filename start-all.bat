@echo off
call conda run --no-capture-output -n Common python -u "%~dp0manage_services.py" start
pause
