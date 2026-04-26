@echo off
setlocal

set "ROOT=%~dp0.."
cd /d "%ROOT%"

if not exist "venv\Scripts\Activate.ps1" (
  echo [ERROR] venv not found: venv\Scripts\Activate.ps1
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\send_claude_signal.ps1"

endlocal
