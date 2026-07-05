"""
医疗聊天机器人 - 统一启动入口
支持：Hugging Face Spaces、Render、本地运行
"""
import os
import subprocess
import sys
import time

def main():
    mode = os.getenv("RUN_MODE", "combined")
    
    if mode == "backend":
        run_backend()
    elif mode == "frontend":
        run_frontend()
    else:
        run_combined()

def run_backend():
    print("🚀 启动 FastAPI 后端服务...")
    port = int(os.getenv("PORT", 6066))
    os.environ["PORT"] = str(port)
    
    from fastapi_bot import app
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

def run_frontend():
    print("🌐 启动 Streamlit 前端服务...")
    port = int(os.getenv("PORT", 8501))
    os.environ["STREAMLIT_SERVER_PORT"] = str(port)
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "streamlit_ui_bot.py", 
        "--server.port", str(port),
        "--server.address", "0.0.0.0",
        "--server.headless", "true"
    ])

def run_combined():
    print("🚀 启动医疗聊天机器人（合并模式）...")
    
    backend_port = int(os.getenv("BACKEND_PORT", 6066))
    frontend_port = int(os.getenv("PORT", 8501))
    
    os.environ["BACKEND_URL"] = f"http://127.0.0.1:{backend_port}"
    
    backend_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "fastapi_bot:app",
        "--host", "127.0.0.1",
        "--port", str(backend_port),
        "--log-level", "info"
    ])
    
    print(f"⏳ 等待后端服务启动...")
    time.sleep(15)
    
    frontend_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run",
        "streamlit_ui_bot.py",
        "--server.port", str(frontend_port),
        "--server.address", "0.0.0.0",
        "--server.headless", "true"
    ])
    
    print(f"✅ 服务启动完成！")
    print(f"   前端: http://localhost:{frontend_port}")
    print(f"   后端: http://localhost:{backend_port}")
    
    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务...")
        frontend_process.terminate()
        backend_process.terminate()

if __name__ == "__main__":
    main()