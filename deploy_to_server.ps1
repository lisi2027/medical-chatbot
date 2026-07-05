param(
    [Parameter(Mandatory=$true)]
    [string]$ServerIP,
    
    [Parameter(Mandatory=$true)]
    [string]$Username,
    
    [string]$ProjectPath = "C:\medical-bot",
    [string]$PythonVersion = "3.10"
)

Write-Host "========================================"
Write-Host "🚀 医疗聊天机器人 - 云服务器部署脚本"
Write-Host "========================================"
Write-Host "服务器: $ServerIP"
Write-Host "用户: $Username"
Write-Host "目标路径: $ProjectPath"
Write-Host "========================================"

Write-Host "`n🔍 检查 SSH 连接..."
try {
    $test = ssh -o ConnectTimeout=5 "$Username@$ServerIP" "echo OK"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ SSH 连接失败，请检查服务器IP、用户名和密钥配置"
        exit 1
    }
    Write-Host "✅ SSH 连接正常"
} catch {
    Write-Error "❌ SSH 连接失败: $_"
    exit 1
}

Write-Host "`n📦 创建远程目录..."
ssh "$Username@$ServerIP" "mkdir -p `"$ProjectPath`""
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ 创建目录失败"
    exit 1
}

Write-Host "`n📤 上传项目文件..."

$excludePatterns = @("venv/", "__pycache__/", ".idea/", ".git/", "node_modules/", ".env")

$tarExclude = ($excludePatterns | ForEach-Object { "--exclude=$_" }) -join " "

tar -czf project.tar.gz $tarExclude --exclude="project.tar.gz" .
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ 创建压缩包失败"
    exit 1
}

scp -o "StrictHostKeyChecking=no" `
    -o "UserKnownHostsFile=/dev/null" `
    project.tar.gz "$Username@$ServerIP`:$ProjectPath/"

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ 文件上传失败"
    exit 1
}

ssh "$Username@$ServerIP" "cd `"$ProjectPath`" && tar -xzf project.tar.gz --strip-components=1 && rm project.tar.gz"
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ 解压文件失败"
    exit 1
}

Remove-Item project.tar.gz
Write-Host "✅ 文件上传完成"

Write-Host "`n⚙️ 在服务器上安装依赖..."
$installScript = @"
cd "$ProjectPath"
if (-not (Test-Path "venv")) {
    python$PythonVersion -m venv venv
}
venv\Scripts\activate
pip install -r requirements.txt
"@

ssh "$Username@$ServerIP" $installScript
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ 依赖安装失败"
    exit 1
}
Write-Host "✅ 依赖安装完成"

Write-Host "`n📝 配置环境变量..."
$envConfig = @"
cd "$ProjectPath"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}
Write-Host "请在服务器上编辑 .env 文件，配置 DASHSCOPE_API_KEY"
"@

ssh "$Username@$ServerIP" $envConfig

Write-Host "`n========================================"
Write-Host "✅ 部署完成！"
Write-Host "`n📋 后续步骤:"
Write-Host "1. 登录服务器: ssh $Username@$ServerIP"
Write-Host "2. 进入项目目录: cd $ProjectPath"
Write-Host "3. 编辑环境变量: notepad .env"
Write-Host "4. 启动服务: .\start_all.ps1"
Write-Host "`n🌐 访问地址:"
Write-Host "   前端: http://$ServerIP:8501"
Write-Host "   后端: http://$ServerIP:6066"
Write-Host "========================================"