@echo off
chcp 65001 >nul
title OmniVoice TTS - 环境配置

echo ============================================
echo   OmniVoice 本地 TTS 环境配置
echo ============================================
echo.

REM 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo       下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [检测] Python 版本:
python --version
echo.

REM 检查 CUDA
echo [检测] CUDA 可用性:
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')" 2>nul
if %errorlevel% neq 0 (
    echo         PyTorch 未安装或 CUDA 不可用，将使用 CPU 推理（较慢）
)
echo.

echo [安装] OmniVoice 及依赖...
echo         （国内用户建议先设置: set HF_ENDPOINT=https://hf-mirror.com）
echo.

pip install omnivoice soundfile fastapi uvicorn[standard] numpy --upgrade
if %errorlevel% neq 0 (
    echo [错误] 安装失败，请检查网络连接
    pause
    exit /b 1
)

echo.
echo [预加载] 首次运行会下载模型到 HuggingFace 缓存目录
echo          （约 14GB，请耐心等待）
echo.
echo ============================================
echo   配置完成！
echo   运行 start-all.bat 启动全部服务
echo ============================================
pause
