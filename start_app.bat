@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  call "scripts\setup_windows.bat"
  if errorlevel 1 (
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" scripts\check_runtime.py >nul 2>nul
if errorlevel 1 (
  call "scripts\setup_windows.bat"
  if errorlevel 1 (
    pause
    exit /b 1
  )
)

start "" ".venv\Scripts\pythonw.exe" -m src.app
endlocal
