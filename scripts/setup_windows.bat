@echo off
setlocal
cd /d "%~dp0\.."

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Please install Python 3.10+ from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 exit /b 1
)

echo Ensuring pip is available...
".venv\Scripts\python.exe" -m ensurepip --upgrade
if errorlevel 1 exit /b 1

echo Installing Python dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Installing Playwright Chromium...
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 exit /b 1

if not exist "downloads" mkdir downloads
if not exist "tools\N_m3u8DL-CLI" mkdir tools\N_m3u8DL-CLI

echo.
echo Setup completed.
echo Put N_m3u8DL-CLI.exe into tools\N_m3u8DL-CLI, or choose it in the app settings.
endlocal
