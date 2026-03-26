@echo off
REM Engram CLI Windows Wrapper
set PYTHONPATH=%CD%
python app/cli.py %*
