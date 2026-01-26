@echo off
REM Cloudflare Tunnel Startup Script
REM Reads TUNNEL_TOKEN from .env and starts the tunnel

echo Loading TUNNEL_TOKEN from .env...

for /f "tokens=2 delims==" %%a in ('findstr /B "TUNNEL_TOKEN=" .env') do set TUNNEL_TOKEN=%%a

REM Remove quotes if present
set TUNNEL_TOKEN=%TUNNEL_TOKEN:"=%

if "%TUNNEL_TOKEN%"=="" (
    echo ERROR: TUNNEL_TOKEN is not set in .env
    echo Please add your token from Cloudflare Zero Trust Dashboard
    pause
    exit /b 1
)

echo Starting Cloudflare Tunnel...
cloudflared.exe tunnel run --token %TUNNEL_TOKEN%
