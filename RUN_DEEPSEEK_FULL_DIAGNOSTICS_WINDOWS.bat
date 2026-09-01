@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV_PY%" goto :noenv
set "PYTHONPATH=%CD%"
"%VENV_PY%" scripts\full_deepseek_diagnostics.py
if errorlevel 1 goto :fail
pause
endlocal
exit /b 0
:noenv
echo [INFO] Python environment not ready. Run START_HERE_WINDOWS.bat once first.
pause
endlocal
exit /b 1
:fail
echo.
echo [FAILED] Please read the error above.
pause
endlocal
exit /b 1
