@echo off
REM Engram Single-Command Entry Point
REM This script initializes the backend and launches the TUI environment.
REM Usage: .\engram.bat

setlocal
set PYTHONPATH=%~dp0
python "%~dp0app\cli.py" %*
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Engram failed to start. 
    echo Please ensure all dependencies are installed: pip install -r requirements.txt
    pause
)
endlocal
