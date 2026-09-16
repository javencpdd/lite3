@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM  Lite3 Robot Monitor 后端一键启动脚本（Windows / cmd）
REM  1. 首次运行会在项目根自动创建 .venv 并安装依赖
REM  2. 之后每次直接双击即可启动
REM  3. 端口可用环境变量覆盖：set PORT=9000 后再运行
REM ============================================================

set ROOT=%~dp0
set PY=%ROOT%.venv\Scripts\python.exe
set UVICORN=%ROOT%.venv\Scripts\uvicorn.exe
if "%PORT%"=="" set PORT=8000

if not exist "%PY%" (
    echo [1/3] 未发现虚拟环境，正在创建 .venv ...
    python -m venv "%ROOT%.venv"
    if errorlevel 1 (
        echo 创建失败：请确认已安装 Python 3.10 以上版本并加入 PATH。
        echo 也可以手动指定：py -3.13 -m venv .venv
        pause
        exit /b 1
    )
)

if not exist "%UVICORN%" (
    echo [2/3] 正在安装后端依赖（首次较慢）...
    "%PY%" -m pip install --disable-pip-version-check -r "%ROOT%backend\requirements.txt"
    if errorlevel 1 (
        echo 依赖安装失败：请检查网络或手动执行
        echo   .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
        pause
        exit /b 1
    )
)

echo [3/3] 启动后端  http://localhost:%PORT%   接口文档 http://localhost:%PORT%/docs
echo       停止服务请按 Ctrl+C
echo.
cd /d "%ROOT%backend"
"%PY%" -m uvicorn main:app --host 0.0.0.0 --port %PORT%
pause
