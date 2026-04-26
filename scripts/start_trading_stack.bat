@echo off
setlocal
title Trading AI Suite
color 0A
cls

rem Unified launcher:
rem 1) TradingView app (optional, via tradingview-mcp launcher)
rem 2) Uvicorn bot server
rem 3) ngrok public tunnel
rem 4) Claude JSON signal sender

set "ROOT=%~dp0.."
pushd "%ROOT%"

set "TV_MCP_LAUNCHER=C:\Users\kenyb\Desktop\OTROS\tradingview-mcp\launch_msix.ps1"

echo.
echo  ============================================
echo    TRADING AI SUITE - Keny
echo  ============================================
echo.
echo  Stack unificado:
echo    [*] TradingView app
echo    [*] Bot FastAPI/Uvicorn
echo    [*] ngrok tunnel
echo    [*] Signal Sender (Plan B)
echo.

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

if exist "%TV_MCP_LAUNCHER%" (
  echo [INFO] Launching TradingView app...
  start "TradingView App" powershell -NoProfile -ExecutionPolicy Bypass -File "%TV_MCP_LAUNCHER%"
) else (
  echo [WARN] TradingView launcher not found: %TV_MCP_LAUNCHER%
)

echo [INFO] Starting Trading Bot stack...
echo [INFO] Project root: %ROOT%
echo [INFO] ngrok domain: %NGROK_DOMAIN%

start "Trading Bot (Uvicorn)" cmd /k "cd /d ""%ROOT%"" && call venv\Scripts\activate.bat && python -m uvicorn bot:app --host 0.0.0.0 --port 8000 --reload"
start "ngrok Tunnel" cmd /k "cd /d ""%ROOT%"" && ngrok http --domain=%NGROK_DOMAIN% 8000"
start "Signal Sender (Paste Claude JSON)" cmd /k "cd /d ""%ROOT%\scripts"" && powershell -NoProfile -ExecutionPolicy Bypass -File .\send_claude_signal.ps1"

echo [OK] Unified stack windows launched:
echo      - TradingView App ^(if launcher exists^)
echo      - Trading Bot ^(Uvicorn^)
echo      - ngrok Tunnel
echo      - Signal Sender ^(paste JSON from Claude + END^)
echo.
echo Keep bot and ngrok windows open while Claude Routine is running.

popd
endlocal
