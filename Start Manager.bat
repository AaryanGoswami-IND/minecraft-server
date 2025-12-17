@echo off
title Minecraft Server Manager
echo ========================================
echo   Minecraft Server Manager
echo ========================================
echo.

:: Refresh PATH to include new Python installation
set PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts

echo Starting Server Manager...
echo.
python server_manager.py
pause
