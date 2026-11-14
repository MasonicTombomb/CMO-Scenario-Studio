@echo off
rem Start CMO Scenario Studio from the project folder (creates the virtual environment on first run).
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Creating virtual environment...
    python -m venv .venv || goto :error
    .venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error
)
start "" .venv\Scripts\pythonw.exe run_studio.py %*
exit /b 0
:error
echo Setup failed. Install 64-bit Python 3.10+ and try again.
pause
