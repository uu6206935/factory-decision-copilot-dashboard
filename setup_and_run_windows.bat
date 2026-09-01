@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "FDC_PORT=8174"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

rem ---------------------------------------------------------------------------
rem 1) Python virtual environment.
rem    NOTE: .venv\Scripts\activate.bat hard-codes the absolute path of the
rem    folder the venv was first created in, so it breaks as soon as the
rem    project folder is copied or renamed. We call .venv\Scripts\python.exe
rem    directly instead, which is relocation-safe.
rem ---------------------------------------------------------------------------
if not exist "%VENV_PY%" goto :makevenv
"%VENV_PY%" -c "import sys" >nul 2>&1
if errorlevel 1 goto :movevenv
goto :deps

:movevenv
set "BROKEN=.venv_broken_%RANDOM%"
echo [WARN] The existing .venv cannot run. Moving it aside to %BROKEN%
move ".venv" "%BROKEN%" >nul

:makevenv
if exist ".venv" goto :aftercreate
echo [INFO] Creating the Python virtual environment...
py -3 -m venv ".venv" 2>nul
:aftercreate
if not exist "%VENV_PY%" python -m venv ".venv"
if not exist "%VENV_PY%" goto :nopython
goto :deps

:nopython
echo.
echo [ERROR] Python was not found on this PC.
echo         Install Python 3.11 or newer, then run this file again:
echo         https://www.python.org/downloads/windows/
goto :fail

:deps
rem ---------------------------------------------------------------------------
rem Skip pip entirely when requirements.txt has not changed since the last
rem successful install. Even a "nothing to do" pip install/resolve costs real
rem seconds on every launch, so this is what makes repeat startups fast.
rem ---------------------------------------------------------------------------
set "REQ_HASH_FILE=%~dp0.venv\requirements.sha256"
set "REQ_HASH="
for /f "usebackq delims=" %%h in (`powershell -NoProfile -Command "(Get-FileHash '%~dp0requirements.txt' -Algorithm SHA256).Hash" 2^>nul`) do set "REQ_HASH=%%h"
set "STORED_HASH="
if exist "%REQ_HASH_FILE%" set /p STORED_HASH=<"%REQ_HASH_FILE%"
if not "%REQ_HASH%"=="" if /i "%REQ_HASH%"=="%STORED_HASH%" (
    echo [INFO] Dependencies already up to date, skipping pip install.
    goto :rundemo
)

echo [INFO] Checking dependencies. The first run can take several minutes...
"%VENV_PY%" -m pip install --upgrade pip --disable-pip-version-check
"%VENV_PY%" -m pip install -r requirements.txt --disable-pip-version-check
if errorlevel 1 goto :depfail
if not "%REQ_HASH%"=="" echo %REQ_HASH%>"%REQ_HASH_FILE%"

:rundemo

rem ---------------------------------------------------------------------------
rem 2) Open the browser only after the server actually answers.
rem    Application startup takes ~30s, so the old fixed 3 second wait always
rem    landed on a connection-refused page.
rem ---------------------------------------------------------------------------
start "" /min powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='http://127.0.0.1:%FDC_PORT%/'; for($i=0;$i -lt 180;$i++){ try{ $null = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 3; Start-Process $u; break } catch { Start-Sleep -Seconds 2 } }"

echo.
echo Factory Decision Copilot v1.7.4
echo URL: http://127.0.0.1:%FDC_PORT%/
echo.

"%VENV_PY%" run_demo.py
if errorlevel 1 goto :fail

endlocal
exit /b 0

:depfail
echo.
echo [ERROR] Installing the dependencies failed. Check your network connection.
goto :fail

:fail
echo.
echo *** Startup failed. Please read the messages above. ***
pause
endlocal
exit /b 1
