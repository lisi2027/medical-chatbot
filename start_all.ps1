Write-Host "========================================"
Write-Host "🚀 医疗聊天机器人 - 一键启动脚本"
Write-Host "========================================"

$env:PYTHONPATH = "$PWD"

Write-Host "`n📡 启动 FastAPI 后端服务..."
Start-Process -FilePath "$PWD\venv\Scripts\python.exe" -ArgumentList "$PWD\fastapi_bot.py" -WindowStyle Minimized

Write-Host "⏳ 等待后端服务启动..."
Start-Sleep -Seconds 15

Write-Host "`n🌐 启动 Streamlit 前端服务..."
Start-Process -FilePath "$PWD\venv\Scripts\streamlit.exe" -ArgumentList "run", "$PWD\streamlit_ui_bot.py", "--server.port", "8501" -WindowStyle Minimized

Write-Host "`n========================================"
Write-Host "✅ 服务启动完成！"
Write-Host "`n📊 服务地址:"
Write-Host "   前端界面: http://localhost:8501"
Write-Host "   后端 API: http://localhost:6066"
Write-Host "   API 文档: http://localhost:6066/docs"
Write-Host "`n💡 提示: 请确保 .env 文件中已配置 DASHSCOPE_API_KEY"
Write-Host "========================================"