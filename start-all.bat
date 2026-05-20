@echo off
set "PATH=C:\Windows\System32;C:\Windows;C:\Program Files\nodejs;%PATH%"
set "NPM=C:\Program Files\nodejs\npm.cmd"
set "ROOT=%~dp0"

if not exist "%NPM%" (
    echo [ERROR] Node.js not found at %NPM%
    pause
    exit /b 1
)

if not exist "%ROOT%node_modules" (
    echo Installing npm packages...
    cd /d "%ROOT%"
    call "%NPM%" install
)

echo Starting dev server...
echo   Frontend: http://localhost:5173
echo   Backend : http://localhost:3001
echo   TTS     : auto (if "local" selected in settings)
echo.

cd /d "%ROOT%"
call "%NPM%" run dev
pause
