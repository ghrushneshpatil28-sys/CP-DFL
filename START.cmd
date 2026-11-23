@echo off
cd /d "%~dp0"
if not exist "backend\venv\Scripts\python.exe" (
  echo Python environment missing. Follow README.md to install dependencies.
  pause
  exit /b 1
)
"backend\venv\Scripts\python.exe" -m backend.dev %*
if errorlevel 1 pause
