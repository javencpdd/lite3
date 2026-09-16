@echo off
chcp 65001 >nul
setlocal

REM ============================================================
REM  Lite3 Robot Monitor 前端开发服务器（Windows / cmd）
REM  首次运行会执行 npm install；之后直接启动 Vite 开发服务器
REM ============================================================

set ROOT=%~dp0

where npm >nul 2>nul
if errorlevel 1 (
    echo 未找到 npm：请确认已安装 Node.js 18 以上版本并加入 PATH。
    pause
    exit /b 1
)

if not exist "%ROOT%frontend\node_modules" (
    echo [1/2] 首次运行，正在安装前端依赖 ...
    pushd "%ROOT%frontend"
    call npm install --no-audit --no-fund
    if errorlevel 1 (
        echo 依赖安装失败，请检查网络。
        popd
        pause
        exit /b 1
    )
    popd
)

echo [2/2] 启动前端  http://localhost:5173
echo       停止服务请按 Ctrl+C
echo.
cd /d "%ROOT%frontend"
call npm run dev
pause
