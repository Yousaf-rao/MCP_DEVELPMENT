@echo off
REM ngrok Tunnel Startup Script for Figma Webhooks
REM This creates a public URL that forwards to localhost:8000

echo.
echo ========================================
echo   Figma Webhook Tunnel (ngrok)
echo ========================================
echo.
echo Starting ngrok tunnel to localhost:8000...
echo.
echo IMPORTANT: Copy the "Forwarding" URL (https://xxx.ngrok-free.app)
echo and use it to register your Figma webhook.
echo.
echo The webhook endpoint will be: [ngrok-url]/figma-webhook
echo.

ngrok http 8000
