# ============================================================
#  Lite3 Robot Monitor 后端一键启动脚本（Windows / PowerShell）
#  用法：右键 -> 使用 PowerShell 运行
#        或在 PowerShell 中执行 .\start-backend.ps1
#  端口覆盖：$env:PORT = 9000; .\start-backend.ps1
# ============================================================

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$Venv = Join-Path $Root ".venv"
$Py = Join-Path $Venv "Scripts\python.exe"
$Uvicorn = Join-Path $Venv "Scripts\uvicorn.exe"
$Port = "8000"
if ($env:PORT) { $Port = $env:PORT }

if (-not (Test-Path $Py)) {
    Write-Host "[1/3] 未发现虚拟环境，正在创建 .venv ..." -ForegroundColor Cyan
    python -m venv $Venv
    if (-not (Test-Path $Py)) {
        Write-Host "创建失败：请确认已安装 Python 3.10 以上版本并加入 PATH。" -ForegroundColor Red
        Read-Host "按回车退出"
        exit 1
    }
}

if (-not (Test-Path $Uvicorn)) {
    Write-Host "[2/3] 正在安装后端依赖（首次较慢）..." -ForegroundColor Cyan
    & $Py -m pip install --disable-pip-version-check -r (Join-Path $Root "backend\requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "依赖安装失败：请检查网络或手动执行" -ForegroundColor Red
        Write-Host "  .venv\Scripts\python.exe -m pip install -r backend\requirements.txt"
        Read-Host "按回车退出"
        exit 1
    }
}

Write-Host "[3/3] 启动后端 http://localhost:$Port  接口文档 http://localhost:$Port/docs" -ForegroundColor Green
Write-Host "      停止服务请按 Ctrl+C" -ForegroundColor DarkGray

Set-Location (Join-Path $Root "backend")
& $Py -m uvicorn main:app --host 0.0.0.0 --port $Port
