@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Exi

where node >nul 2>nul
if errorlevel 1 (
  echo [!] Node.js is not installed.
  echo     Install the LTS version from https://nodejs.org and run this file again.
  start "" https://nodejs.org
  pause
  exit /b 1
)

if not exist node_modules (
  echo [1/2] Installing packages - first run only, takes 1-3 minutes...
  call npm install
  if errorlevel 1 (
    echo [!] npm install failed. Check your internet connection and try again.
    pause
    exit /b 1
  )
)

if not exist .env.local copy .env.example .env.local >nul

echo [2/2] Starting Exi... the browser opens in a few seconds.
echo       Keep this window open while you use Exi. Close it to stop.
start "" cmd /c "timeout /t 10 >nul & start http://localhost:3000"
call npm run dev
pause
