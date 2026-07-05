Write-Host "========================================"
Write-Host "🚀 医疗聊天机器人 - 内网穿透启动脚本"
Write-Host "========================================"

$env:PYTHONPATH = "$PWD"

Write-Host "`n📡 启动 FastAPI 后端服务..."
Start-Process -FilePath "$PWD\venv\Scripts\python.exe" -ArgumentList "$PWD\fastapi_bot.py" -WindowStyle Minimized

Write-Host "⏳ 等待后端服务启动..."
Start-Sleep -Seconds 15

Write-Host "`n🌐 启动 Streamlit 前端服务..."
Start-Process -FilePath "$PWD\venv\Scripts\streamlit.exe" -ArgumentList "run", "$PWD\streamlit_ui_bot.py", "--server.port", "8501" -WindowStyle Minimized

Write-Host "⏳ 等待前端服务启动..."
Start-Sleep -Seconds 10

Write-Host "`n🔗 启动 Caddy 反向代理..."
Start-Process -FilePath "caddy" -ArgumentList "run", "--config", "$PWD\Caddyfile" -WindowStyle Minimized

Write-Host "⏳ 等待 Caddy 启动..."
Start-Sleep -Seconds 5

Write-Host "`n🌍 启动 cpolar 内网穿透..."
Start-Process -FilePath "cpolar" -ArgumentList "http", "80" -WindowStyle Minimized

Write-Host "`n========================================"
Write-Host "✅ 所有服务启动完成！"
Write-Host "`n📊 本地服务地址:"
Write-Host "   Caddy 入口: http://localhost"
Write-Host "   前端界面: http://localhost:8501"
Write-Host "   后端 API: http://localhost/api"
Write-Host "`n🌍 公网访问地址（由 cpolar 提供）:"
Write-Host "   打开 http://localhost:9200 查看隧道状态"
Write-Host "   cpolar 会生成类似: https://xxxxxx.cpolar.app"
Write-Host "`n💡 提示: 公网地址每次启动可能会变化（免费版）"
Write-Host "========================================"