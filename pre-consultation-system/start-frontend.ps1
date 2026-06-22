Set-Location -LiteralPath $PSScriptRoot\frontend

Write-Host "> 检查依赖..." -ForegroundColor Yellow
if (-not (Test-Path "node_modules")) {
    Write-Host "  安装 npm 依赖..." -ForegroundColor Cyan
    npm install
} else {
    Write-Host "  依赖已就绪" -ForegroundColor Green
}

Write-Host "> 启动 Vite 开发服务器 http://localhost:5173`n" -ForegroundColor Green
npm run dev
