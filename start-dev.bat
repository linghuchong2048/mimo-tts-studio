@echo off
chcp 65001 >nul
title MiMo Audio Workstation - 开发模式

echo ============================================
echo   铸光音频工作站 - 开发模式
echo   （仅启动前后端，不含本地 TTS）
echo ============================================
echo.

REM 检查 node_modules
if not exist "node_modules\" (
    echo [安装] npm 依赖...
    call npm install
    echo.
)

echo 启动中...
echo   前端: http://localhost:5173
echo   后端: http://localhost:3001
echo.

call npm run dev
pause
