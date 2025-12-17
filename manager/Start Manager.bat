@echo off
title Minecraft Server Manager
echo ========================================
echo   Minecraft Server Manager
echo ========================================
echo.
echo Installing dependencies...
cd /d "%~dp0"
call npm install
echo.
echo Starting manager...
echo.
node server.js
pause
