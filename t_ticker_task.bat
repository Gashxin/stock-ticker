@echo off
chcp 65001 >nul
echo ========================================
echo    V90 做T提醒器 - 自动任务
echo ========================================
echo.

python "%~dp0t_ticker_v2.py"

echo.
echo 任务完成
pause
