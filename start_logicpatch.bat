@echo off
REM ============================================================
REM LogicPatch Startup Script
REM Starts all services and auto-registers webhook if needed
REM ============================================================

echo.
echo ========================================
echo   LogicPatch Automation Startup
echo ========================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Run: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM ============================================================
REM Step 1: Start ngrok in background
REM ============================================================
echo [1/4] Starting ngrok tunnel...
start "ngrok" /min cmd /c "ngrok http 8000"

REM Wait for ngrok to initialize
timeout /t 5 /nobreak > nul

REM ============================================================
REM Step 2: Get ngrok public URL
REM ============================================================
echo [2/4] Fetching ngrok public URL...

REM Use PowerShell to get the URL
for /f "delims=" %%i in ('powershell -Command "(Invoke-RestMethod http://localhost:4040/api/tunnels).tunnels[0].public_url"') do set NGROK_URL=%%i

if "%NGROK_URL%"=="" (
    echo [ERROR] Could not get ngrok URL. Is ngrok running?
    pause
    exit /b 1
)

echo    URL: %NGROK_URL%

REM ============================================================
REM Step 3: Register/Update Webhook
REM ============================================================
echo [3/4] Registering FILE_COMMENT webhook with Figma...
python scripts/register_webhook.py --url %NGROK_URL% --event FILE_UPDATE

REM ============================================================
REM Step 4: Start services
REM ============================================================
echo [4/4] Starting services...

REM Start webhook server in new window
start "Webhook Server" cmd /k "call venv\Scripts\activate.bat && python webhook_server.py"

REM Wait a moment for server to start
timeout /t 3 /nobreak > nul

REM Start automation worker in new window
start "Automation Worker" cmd /k "call venv\Scripts\activate.bat && python automation_worker.py"

echo.
echo ========================================
echo   All services started!
echo ========================================
echo.
echo   ngrok URL: %NGROK_URL%
echo.
echo   Windows:
echo   - ngrok (minimized)
echo   - Webhook Server
echo   - Automation Worker
echo.
echo   To test: Add a comment "!sync" on a Figma frame
echo ========================================
echo.

pause
