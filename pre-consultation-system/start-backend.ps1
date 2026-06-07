$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot\backend

Write-Host "> 杀掉占用8000端口的进程..." -ForegroundColor Yellow
$pid8000 = (netstat -ano | Select-String ":8000" | Select-String "LISTENING").Line -replace ".*(\d+)$", '$1' | Select-Object -First 1
if ($pid8000) { taskkill /PID $pid8000 /F 2>$null; Write-Host "  已杀掉 PID $pid8000" -ForegroundColor Green }

Write-Host "> 检查依赖..." -ForegroundColor Yellow
$installed = pip list 2>$null | Out-String
$missing = $false
Get-Content requirements.txt | ForEach-Object {
    $pkg = $_ -replace '[<>=!~].*$', ''
    if ($pkg -and $installed -notmatch [regex]::Escape($pkg)) {
        $missing = $true
    }
}
if ($missing) {
    Write-Host "  安装依赖包..." -ForegroundColor Cyan
    pip install -r requirements.txt
} else {
    Write-Host "  依赖已就绪" -ForegroundColor Green
}

Write-Host "> 初始化种子数据..." -ForegroundColor Yellow
python -m seed.seed_data
if ($LASTEXITCODE -ne 0) {
    Write-Host "  种子数据初始化失败，跳过（可能已存在）" -ForegroundColor DarkYellow
}

Write-Host "> 启动 FastAPI 服务 http://localhost:8000" -ForegroundColor Green
Write-Host "  API文档: http://localhost:8000/docs`n" -ForegroundColor Cyan
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
