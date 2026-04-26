@echo off
setlocal

rem Start full local stack for Trading-bot:
rem 1) Uvicorn bot server
rem 2) ngrok public tunnel
rem 3) Claude JSON signal sender window

set "ROOT=%~dp0.."
pushd "%ROOT%"

if not exist "venv\Scripts\activate.bat" (
  echo [ERROR] Python virtual environment not found at venv\Scripts\activate.bat
  echo Create it first, then install dependencies.
  popd
  exit /b 1
)

if not exist ".env" (
  echo [WARN] .env not found. Copy .env.example to .env and fill your secrets.
)

where ngrok >nul 2>nul
if errorlevel 1 (
  echo [ERROR] ngrok is not installed or not on PATH.
  echo Install ngrok and run: ngrok config add-authtoken YOUR_TOKEN
  popd
  exit /b 1
)

if not exist "scripts\send_claude_signal.ps1" (
  echo [ERROR] scripts\send_claude_signal.ps1 not found.
  popd
  exit /b 1
)

set "NGROK_DOMAIN=shaft-goliath-shakable.ngrok-free.dev"
if not "%~1"=="" set "NGROK_DOMAIN=%~1"

echo [INFO] Starting Trading Bot stack...
echo [INFO] Project root: %ROOT%
echo [INFO] ngrok domain: %NGROK_DOMAIN%

start "Trading Bot (Uvicorn)" cmd /k "cd /d ""%ROOT%"" && call venv\Scripts\activate.bat && python -m uvicorn bot:app --host 0.0.0.0 --port 8000 --reload"
start "ngrok Tunnel" cmd /k "cd /d ""%ROOT%"" && ngrok http --domain=%NGROK_DOMAIN% 8000"
start "Signal Sender (Paste Claude JSON)" cmd /k "cd /d ""%ROOT%\scripts"" && powershell -NoProfile -ExecutionPolicy Bypass -File .\send_claude_signal.ps1"

echo [OK] Three windows launched:
echo      - Trading Bot ^(Uvicorn^)
echo      - ngrok Tunnel
echo      - Signal Sender ^(paste JSON from Claude + END^)
echo.
echo Keep bot and ngrok windows open while Claude Routine is running.

popd
endlocal
