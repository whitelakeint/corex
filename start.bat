@echo off
REM Start the Building Concierge server in the background (Windows).
REM Mirrors start.sh. Runs uvicorn on port 8001 with --reload; logs to server.log.
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PORT=8001"
set "LOGFILE=%~dp0server.log"

REM --- Already running on this port? ---
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    echo Server is already running on port %PORT% ^(PID %%P^)
    echo Use stop.bat to stop it first.
    exit /b 1
)

REM --- Pick interpreter: prefer the project venv ---
if exist "%~dp0venv\Scripts\python.exe" (
    set "PY=%~dp0venv\Scripts\python.exe"
) else (
    echo WARNING: venv not found at venv\Scripts\python.exe - using system "python".
    echo          Make sure backend deps are installed ^(pip install -r backend\requirements.txt^).
    set "PY=python"
)

echo Starting Building Concierge server on port %PORT% ...

REM Launch in a titled background window so stop.bat can find + kill the tree.
start "corex-server" /min cmd /c ""%PY%" -m uvicorn backend.app:app --host 0.0.0.0 --port %PORT% --reload > "%LOGFILE%" 2>&1"

echo   Running on http://localhost:%PORT%
echo   Logs:  %LOGFILE%
echo   Stop with: stop.bat
endlocal
