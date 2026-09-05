@echo off
chcp 65001 >nul
title FX Collector Server
echo ===================================================
echo    DANG KHOI DONG FX COLLECTOR SERVER...
echo ===================================================

:: Tu dong tat tien trinh cu dang chiem cong 8000 (neu co)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

python server.py
pause
