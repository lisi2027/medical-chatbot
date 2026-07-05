Write-Host "========================================"
Write-Host "🚀 医疗聊天机器人 - 一键安装脚本"
Write-Host "========================================"

$projectPath = $PWD
$venvPath = "$projectPath\venv"

Write-Host "`n📦 检查 Python 环境..."
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $python) {
    Write-Error "❌ 未找到 Python，请先安装 Python 3.10+"
    Write-Host "📥 下载地址: https://www.python.org/downloads/"
    exit 1
}

$pythonVersion = & $python --version 2>&1
Write-Host "✅ Python 版本: $pythonVersion"

Write-Host "`n📁 检查虚拟环境..."
if (-not (Test-Path $venvPath)) {
    Write-Host "创建虚拟环境..."
    & $python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ 创建虚拟环境失败"
        exit 1
    }
    Write-Host "✅ 虚拟环境创建成功"
} else {
    Write-Host "✅ 虚拟环境已存在"
}

Write-Host "`n📥 安装项目依赖..."
& "$venvPath\Scripts\pip.exe" install -r "$projectPath\requirements.txt"
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ 依赖安装失败"
    exit 1
}
Write-Host "✅ 依赖安装成功"

Write-Host "`n📝 配置环境变量..."
$envFile = "$projectPath\.env"
$envExample = "$projectPath\.env.example"

if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "✅ 已创建 .env 文件"
} else {
    Write-Host "✅ .env 文件已存在"
}

Write-Host "`n========================================"
Write-Host "✅ 安装完成！"
Write-Host "`n📋 下一步操作:"
Write-Host "1. 编辑环境变量文件，填入 API Key"
Write-Host "   notepad $envFile"
Write-Host ""
Write-Host "2. 启动服务"
Write-Host "   .\start_all.ps1"
Write-Host ""
Write-Host "3. 访问地址"
Write-Host "   前端界面: http://localhost:8501"
Write-Host "   后端 API: http://localhost:6066"
Write-Host ""
Write-Host "💡 提示: 需要先在阿里云百炼申请 API Key"
Write-Host "   申请地址: https://bailian.console.aliyun.com/"
Write-Host "========================================"

Write-Host "`n🔓 是否立即打开 .env 文件配置 API Key? (Y/N)" -NoNewline
$choice = Read-Host
if ($choice -eq "Y" -or $choice -eq "y") {
    Start-Process notepad $envFile
}