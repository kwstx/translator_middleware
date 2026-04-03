@echo off
REM Engram Self-Healing Entry Point
REM This script initializes the backend, handles dependencies, and launches the TUI environment.
REM Usage: .\engram.bat

setlocal
set PYTHONPATH=%~dp0

REM 1. Initialize Virtual Environment if missing
if not exist "%~dp0venv" (
    echo [INFO] Virtual environment NOT found. Creating one...
    python -m venv "%~dp0venv"
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create venv. Please ensure Python is installed and in your PATH.
        exit /b 1
    )
)

set PY_EXE="%~dp0venv\Scripts\python.exe"

REM 2. Dependency Check (Fast Import Test)
echo [INFO] Checking dependencies...
%PY_EXE% -c "import keyring, typer, rich, httpx, jwt, pydantic, yaml" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] Missing or broken dependencies. Synchronizing environment...
    %PY_EXE% -m pip install --upgrade pip >nul 2>&1
    %PY_EXE% -m pip install -r "%~dp0requirements.txt"
    REM Double-check imports before failing, as pip may return 1 for minor warnings
    %PY_EXE% -c "import keyring, typer, rich, httpx, jwt, pydantic, yaml" >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Environment synchronization failed. Check your internet connection or requirements.txt.
        exit /b 1
    )
    echo [SUCCESS] Environment synchronized.
)

REM 3. Run the Engram CLI
%PY_EXE% "%~dp0app\cli.py" %*

REM 4. Error Handling
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Engram exited with code %ERRORLEVEL%.
    echo TIP: If the error persists, try deleting the 'venv' folder and running this script again.
    echo.
    pause
)
endlocal
