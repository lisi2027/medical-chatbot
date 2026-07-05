# 医疗聊天机器人 - 部署指南

## 📋 快速开始

### 推荐方案：免费永久部署

以下方案**完全免费、长期可用、有固定域名**：

| 方案 | 平台 | 费用 | 域名 | 适合场景 |
|------|------|------|------|----------|
| **推荐** | Render | 免费 | 免费子域名 + 自定义域名 | 完整 Web 应用 |
| **AI Demo** | Hugging Face Spaces | 免费 | 免费子域名 | AI/机器学习项目 |
| **初学者** | PythonAnywhere | 免费 | 免费子域名（yourname.pythonanywhere.com） | Flask/Django 学习项目 |

---

## 方案一：Render 免费部署（推荐）

### 1.1 优点

- ✅ **永久免费**：提供免费层，无时间限制
- ✅ **固定域名**：免费提供 `xxx.onrender.com` 子域名
- ✅ **自定义域名**：支持绑定自己的域名
- ✅ **自动 HTTPS**：Let's Encrypt 证书自动配置
- ✅ **自动部署**：连接 GitHub，Push 即部署
- ✅ **支持 Python**：原生支持 FastAPI、Flask、Streamlit

### 1.2 准备工作

1. **创建 GitHub 仓库**
   - 注册 GitHub 账号（免费）
   - 创建新仓库，上传项目代码

2. **注册 Render 账号**
   - 访问: https://render.com
   - 使用 GitHub 账号登录

### 1.3 部署步骤

1. **创建 Web Service**
   - 登录 Render → New → Web Service
   - 选择你的 GitHub 仓库
   - 设置:
     - Runtime: Python
     - Branch: main
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `python app.py`

2. **配置环境变量**
   - 在 Render 控制台 → Settings → Environment Variables
   - 添加:
     ```
     DASHSCOPE_API_KEY=你的API密钥
     RUN_MODE=combined
     PORT=8501
     ```

3. **部署**
   - 点击 Deploy
   - 等待构建完成
   - 获取访问地址（类似: https://your-app.onrender.com）

### 1.4 绑定自定义域名（可选）

1. 在 Render → Settings → Custom Domains
2. 添加你的域名（如: medical-bot.yourdomain.com）
3. 在域名 DNS 设置中添加 CNAME 记录指向 Render 提供的地址
4. HTTPS 会自动配置

### 1.5 注意事项

- **休眠机制**：15分钟无访问会休眠，下次访问需要等待几秒唤醒
- **资源限制**：512MB 内存，0.1 CPU
- **数据库**：免费 PostgreSQL 有 90 天试用期，本项目不需要数据库

---

## 方案二：Hugging Face Spaces 部署

### 2.1 优点

- ✅ **永久免费**：免费层无时间限制
- ✅ **硬件强大**：双核 CPU + 16GB RAM（非常大方！）
- ✅ **一键部署**：支持 Streamlit/Gradio 一键部署
- ✅ **社区氛围好**：适合展示 AI 项目

### 2.2 部署步骤

1. **注册 Hugging Face 账号**
   - 访问: https://huggingface.co
   - 注册免费账号

2. **创建 Space**
   - 点击 "New Space"
   - 选择:
     - Space SDK: Streamlit
     - License: MIT
     - Git clone your repo: 粘贴你的 GitHub 仓库地址

3. **配置环境变量**
   - 在 Spaces → Settings → Repository secrets
   - 添加:
     ```
     DASHSCOPE_API_KEY=你的API密钥
     ```

4. **部署完成**
   - 等待构建完成
   - 访问地址: https://huggingface.co/spaces/你的用户名/你的空间名

### 2.3 注意事项

- **暂停机制**：48小时无活动会暂停，点击即可唤醒
- **公开项目**：代码默认开源可见（可设为私有，但额度相同）

---

## 方案三：PythonAnywhere 部署

### 3.1 优点

- ✅ **永久免费**：一个免费 Web 应用
- ✅ **持久化存储**：文件不会因重启丢失
- ✅ **配置简单**：可视化控制面板

### 3.2 部署步骤

1. **注册 PythonAnywhere**
   - 访问: https://www.pythonanywhere.com
   - 注册免费账号

2. **上传代码**
   - 上传项目 ZIP 文件
   - 解压到 `/home/你的用户名/medical-bot`

3. **创建虚拟环境**
   ```bash
   mkvirtualenv medical-bot --python=python3.10
   pip install -r requirements.txt
   ```

4. **配置 WSGI**
   - 进入 Web → Add a new web app
   - 选择 Manual configuration → Python 3.10
   - 修改 WSGI 文件:
     ```python
     import sys
     sys.path.insert(0, '/home/你的用户名/medical-bot')
     from fastapi_bot import app as application
     ```

5. **配置环境变量**
   - 在 Web → Environment variables
   - 添加: `DASHSCOPE_API_KEY=你的API密钥`

6. **访问**
   - 地址: https://你的用户名.pythonanywhere.com

### 3.3 注意事项

- **域名限制**：只能使用 `你的用户名.pythonanywhere.com`
- **网络限制**：免费账户不能向外发起 HTTP 请求（部分白名单除外）
- **不支持 ASGI**：不支持 FastAPI 异步框架（需用 gunicorn）

---

## 方案四：内网穿透（无需云服务器）

适合没有云服务器但需要公网访问的场景。

### 4.1 使用 cpolar

1. **安装 cpolar**
   - 访问: https://www.cpolar.com/download

2. **启动服务**
   ```powershell
   .\start_tunnel.ps1
   ```

3. **获取公网地址**
   - 打开 http://localhost:9200
   - 地址类似: `https://xxxxxx.cpolar.app`

### 4.2 注意事项

- **免费版地址变化**：每次重启地址可能变化
- **付费版**：可获得固定域名

---

## 方案五：Windows 云服务器部署

### 5.1 准备工作

1. 购买 Windows 云服务器（2核4G以上）
2. 开放端口: 80, 443, 8501, 6066
3. 安装 Python 3.10+

### 5.2 部署步骤

```powershell
# 上传项目
scp -r ./* username@server-ip:C:\medical-bot\

# 安装依赖
cd C:\medical-bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
notepad .env

# 启动服务
.\start_all.ps1
```

---

## 项目架构

```
用户访问 (公网)
    │
    ▼
┌─────────────────────────────┐
│    Render/Hugging Face      │
│    (免费平台提供域名)        │
└─────────────────────────────┘
    │
    ▼
┌──────────────────────────────────┐
│         Streamlit 前端 (8501)     │
│         FastAPI 后端 (6066)      │
└──────────────────────────────────┘
         │
         ▼
    阿里云百炼 API
```

---

## 部署检查清单

- [ ] Python 3.10+ 已安装
- [ ] 依赖已安装 (`pip install -r requirements.txt`)
- [ ] `DASHSCOPE_API_KEY` 已配置
- [ ] 向量模型文件 `bge-large-zh-v1.5/` 存在
- [ ] 医疗数据文件 `Data/` 存在
- [ ] 健康检查: `/health` 返回 200

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `app.py` | 统一启动入口（支持多种部署模式） |
| `fastapi_bot.py` | FastAPI 后端服务 |
| `streamlit_ui_bot.py` | Streamlit 前端界面 |
| `requirements.txt` | Python 依赖清单 |
| `.env` | 环境变量配置 |
| `.env.example` | 环境变量模板 |
| `Procfile` | Render 部署配置 |
| `runtime.txt` | Render Python 版本配置 |
| `space.yml` | Hugging Face Spaces 配置 |
| `Caddyfile` | Caddy 反向代理配置 |
| `start_all.ps1` | 本地一键启动脚本 |
| `start_tunnel.ps1` | 内网穿透启动脚本 |

---

## 安全注意事项

1. **API Key 保密**
   - 不要将 `.env` 文件提交到版本控制
   - 使用环境变量存储敏感信息

2. **HTTPS**
   - 免费平台已自动提供 HTTPS

3. **数据备份**
   - 定期备份知识库和医疗数据