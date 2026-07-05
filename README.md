# 🏥 基于 RAG 的智能医疗问答系统

> 集成阿里云通义千问大模型与 BGE 向量检索技术，构建专业的医疗知识问答系统

![Python](https://img.shields.io/badge/Python-3.10-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 项目简介

本项目是一个基于检索增强生成（RAG）技术的智能医疗问答系统，具备以下特点：

- 🧠 **大模型集成**：调用阿里云通义千问（qwen-plus）进行智能问答
- 📚 **向量检索**：使用 BGE-Large-ZH-V1.5 模型实现医疗知识检索
- 🏥 **多科室支持**：涵盖男科、心血管科、妇产科、肿瘤科、儿科、外科 6 个科室
- 💬 **交互界面**：使用 Streamlit 构建友好的对话界面
- 🔄 **流式输出**：支持打字机效果展示 AI 回答
- 📤 **知识库更新**：支持 CSV 文件上传动态更新知识库

## 🎯 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                     用户交互层                              │
│              Streamlit 前端界面 (端口 8501)                  │
│     - 对话消息展示 - 知识来源可视化 - 文件上传               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     服务层                                  │
│              FastAPI 后端服务 (端口 6066)                    │
│     - RAG 检索管道 - 流式输出 - RESTful API                 │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│     向量检索层       │         │      大模型层        │
│   BGE-Large-ZH-V1.5 │         │   通义千问 qwen-plus │
│  (1024维向量)       │         │   (图片分析 qwen-vl) │
└─────────────────────┘         └─────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                     数据层                                  │
│              医疗知识库 (6个科室，600条知识)                 │
│     Andrology / IM / Obstetrics / Oncology / Pediatrics    │
│                        / Surgery                           │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 阿里云百炼 API Key（免费申请）

### 安装步骤

```powershell
# 1. 克隆仓库
git clone https://github.com/lisi2027/medical-chatbot.git
cd medical-chatbot

# 2. 运行一键安装脚本
.\setup.ps1

# 3. 填入 API Key
# 脚本会自动打开 .env 文件，请填入你的阿里云百炼 API Key

# 4. 启动服务
.\start_all.ps1
```

### 手动安装

```powershell
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env 文件，填入 DASHSCOPE_API_KEY

# 启动后端
python fastapi_bot.py

# 启动前端（新终端）
streamlit run streamlit_ui_bot.py --server.port 8501
```

### 访问地址

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:8501 |
| 后端 API | http://localhost:6066 |
| API 文档 | http://localhost:6066/docs |

## 📁 项目结构

```
medical-chatbot/
├── 🚀 核心代码
│   ├── fastapi_bot.py      # FastAPI 后端服务
│   ├── streamlit_ui_bot.py # Streamlit 前端界面
│   ├── app.py              # 统一启动入口
│   └── medical_loader.py   # 医疗数据加载模块
│
├── 📊 知识库数据
│   └── Data/               # 医疗知识 CSV 文件
│       ├── Andrology.csv   # 男科
│       ├── IM.csv          # 心血管科
│       ├── Obstetrics.csv  # 妇产科
│       ├── Oncology.csv    # 肿瘤科
│       ├── Pediatrics.csv  # 儿科
│       └── Surgery.csv     # 外科
│
├── 🧠 向量模型
│   └── bge-large-zh-v1.5/  # BGE 向量模型文件
│
├── ⚙️ 配置文件
│   ├── .env.example        # 环境变量模板
│   ├── .gitignore          # Git 忽略配置
│   ├── Procfile            # Render 部署配置
│   ├── runtime.txt         # Render Python 版本
│   ├── space.yml           # Hugging Face Spaces 配置
│   └── Caddyfile           # Caddy 反向代理配置
│
├── 🚀 启动脚本
│   ├── setup.ps1           # 一键安装脚本
│   ├── start_all.ps1       # 一键启动脚本
│   ├── start_backend.ps1   # 后端启动脚本
│   ├── start_frontend.ps1  # 前端启动脚本
│   ├── start_tunnel.ps1    # 内网穿透启动脚本
│   └── deploy_to_server.ps1# 云服务器部署脚本
│
├── 📖 文档
│   ├── README.md           # 项目说明（本文档）
│   └── DEPLOYMENT.md       # 部署指南
│
└── requirements.txt        # Python 依赖清单
```

## 🔧 RAG 检索流程

```
用户提问
    │
    ▼
┌─────────────────────┐
│ 1. 文本向量化         │  BGE-Large-ZH-V1.5 模型
│    将问题转为向量      │  输出 1024 维向量
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 2. 向量相似度检索     │  余弦相似度计算
│    查找 Top-K 相关文档 │  返回最相关的 3 条知识
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 3. Prompt 增强       │  将检索结果拼接到 Prompt
│    构建上下文         │  作为大模型的参考信息
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 4. LLM 生成回答      │  通义千问 qwen-plus
│    结合上下文生成      │  输出最终回答
└─────────────────────┘
    │
    ▼
用户收到回答（附带知识来源和置信度）
```

## 🌐 部署方案

### 方案一：Render 免费部署（推荐）

1. 注册 Render 账号：https://render.com
2. 创建 Web Service，选择本仓库
3. 设置环境变量：`DASHSCOPE_API_KEY=你的密钥`
4. 部署完成后获得公网地址

### 方案二：Hugging Face Spaces

1. 注册 Hugging Face 账号：https://huggingface.co
2. 创建 Space，选择 Streamlit SDK
3. 配置环境变量
4. 一键部署

### 方案三：内网穿透

使用 cpolar 实现内网穿透，无需云服务器：

```powershell
.\start_tunnel.ps1
```

## 📝 API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/chat` | POST | 对话接口（支持流式输出） |
| `/health` | GET | 健康检查 |
| `/search` | GET | 知识检索 |
| `/upload_knowledge_file` | POST | 上传知识文件 |
| `/knowledge_base_stats` | GET | 知识库统计 |
| `/clear_knowledge` | POST | 清空知识库 |
| `/reload_knowledge` | POST | 重新加载知识库 |
| `/export_conversation` | POST | 导出对话记录 |

## 🔒 安全注意事项

1. **API Key 保密**：不要将 `.env` 文件提交到版本控制
2. **环境变量**：敏感信息通过环境变量配置
3. **CORS**：配置了 CORS 中间件，限制跨域访问
4. **HTTPS**：生产环境建议使用 HTTPS

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [阿里云百炼](https://bailian.console.aliyun.com/) - 提供大模型 API
- [BGE Embedding](https://huggingface.co/BAAI/bge-large-zh-v1.5) - 提供向量模型
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [Streamlit](https://streamlit.io/) - 前端框架