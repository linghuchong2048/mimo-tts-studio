@echo off
chcp 65001 >nul
title OmniVoice Local TTS Server

set "PYTHON=F:\OmniVoice多人配音20260425\OmniVoice-srt\OmniVoice\py312\python.exe"
set "MODEL_PATH=F:\OmniVoice多人配音20260425\OmniVoice-srt\OmniVoice\checkpoints"
set "OMNIVOICE_ROOT=F:\OmniVoice多人配音20260425\OmniVoice-srt\OmniVoice"

echo ============================================
echo   OmniVoice 本地 TTS 服务
echo ============================================
echo.
echo   模型:  %MODEL_PATH%
echo   Python: %PYTHON%
echo   端口: 8000
echo.

REM 检查 Python 是否存在
if not exist "%PYTHON%" (
    echo [错误] Python 未找到: %PYTHON%
    pause
    exit /b 1
)

REM 检查模型是否存在
if not exist "%MODEL_PATH%\model.safetensors" (
    echo [错误] 模型未找到: %MODEL_PATH%
    pause
    exit /b 1
)

echo [启动] 加载模型并启动 API 服务...
echo         首次加载约需 30 秒，请耐心等待...
echo         API 文档: http://localhost:8000/docs
echo.
cd /d "%~dp0omnivoice-server"

set PYTHONPATH=%OMNIVOICE_ROOT%;%PYTHONPATH%

"%PYTHON%" server.py --model-path "%MODEL_PATH%" --port 8000 --host 127.0.0.1

pause
