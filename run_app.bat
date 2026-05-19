@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment was not found.
  echo Running first-time setup...
  call "scripts\setup_windows.bat"
  if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" scripts\check_runtime.py >nul 2>nul
if errorlevel 1 (
  echo Virtual environment dependencies are incomplete.
  echo Running setup to repair the environment...
  call "scripts\setup_windows.bat"
  if errorlevel 1 (
    echo Setup failed. Trying system Python as a fallback...
    python scripts\check_runtime.py
    if errorlevel 1 (
      echo.
      echo Runtime is still incomplete. Please run scripts\setup_windows.bat manually and check the error above.
      pause
      exit /b 1
    )
    python -m src.app
    exit /b %errorlevel%
  )
)

".venv\Scripts\python.exe" scripts\check_runtime.py
if errorlevel 1 (
  echo.
  echo Runtime is still incomplete after setup.
  pause
  exit /b 1
)

if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" -m src.app
) else (
  start "" ".venv\Scripts\python.exe" -m src.app
)

endlocal
