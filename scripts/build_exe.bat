@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  call "scripts\setup_windows.bat"
  if errorlevel 1 exit /b 1
)

".venv\Scripts\python.exe" scripts\check_runtime.py
if errorlevel 1 (
  call "scripts\setup_windows.bat"
  if errorlevel 1 exit /b 1
)

echo Installing build dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1

echo Building executable...
".venv\Scripts\python.exe" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --noconsole ^
  --onedir ^
  --name BatchVideoDownloader ^
  --add-data "config.example.json;." ^
  --collect-all playwright ^
  app_launcher.py
if errorlevel 1 exit /b 1

if exist "tools\N_m3u8DL-CLI_v3.0.2.exe" (
  if not exist "dist\BatchVideoDownloader\tools" mkdir "dist\BatchVideoDownloader\tools"
  copy /Y "tools\N_m3u8DL-CLI_v3.0.2.exe" "dist\BatchVideoDownloader\tools\N_m3u8DL-CLI_v3.0.2.exe" >nul
)

if exist "%LOCALAPPDATA%\ms-playwright\chromium-1140" (
  if not exist "dist\BatchVideoDownloader\ms-playwright" mkdir "dist\BatchVideoDownloader\ms-playwright"
  xcopy /E /I /Y "%LOCALAPPDATA%\ms-playwright\chromium-1140" "dist\BatchVideoDownloader\ms-playwright\chromium-1140" >nul
)

if not exist "dist\BatchVideoDownloader\downloads" mkdir "dist\BatchVideoDownloader\downloads"

echo.
echo Build completed:
echo dist\BatchVideoDownloader\BatchVideoDownloader.exe
endlocal
