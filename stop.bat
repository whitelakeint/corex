@echo off
REM Stop the background Building Concierge server (Windows). Mirrors stop.sh.
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PORT=8001"
set "STOPPED="

REM --- Kill whatever is LISTENING on the port, tree-wise (worker + reloader) ---
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%PORT% .*LISTENING"') do (
    echo Stopping server PID %%P ...
    taskkill /PID %%P /T /F >nul 2>&1
    set "STOPPED=1"
)

REM --- Also close the launcher window from start.bat, if still around ---
taskkill /FI "WINDOWTITLE eq corex-server*" /T /F >nul 2>&1

REM --- Clean up the stale PID file left by start.sh, if any ---
if exist "%~dp0server.pid" del "%~dp0server.pid" >nul 2>&1

if defined STOPPED (
    echo Server stopped.
) else (
    echo No server running on port %PORT%.
)
endlocal
