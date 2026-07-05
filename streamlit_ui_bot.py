"""
基于千问+RAG的医疗聊天机器人 - 医疗主题
连接FastAPI后端 | 支持 RAG（检索增强生成）| 显示知识来源和置信度
支持文件上传更新知识库
"""

import streamlit as st
import requests
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import uuid
import logging
import json
import os
from dotenv import load_dotenv

load_dotenv()

# ========== 页面配置 ==========
st.set_page_config(
    page_title="基于千问+RAG的医疗聊天机器人",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 医疗主题CSS ==========
st.markdown("""
<style>
    :root {
        --primary: #0891b2;
        --primary-dark: #0e7490;
        --primary-light: #22d3ee;
        --primary-soft: #cffafe;
        --primary-bg: #ecfeff;
        --text-dark: #1e293b;
        --text-light: #64748b;
        --white: #ffffff;
    }
    
    .stApp {
        background: linear-gradient(180deg, #ecfeff 0%, #cffafe 100%) !important;
    }
    
    header { display: none !important; }
    .stApp > div:first-child { padding-top: 0 !important; }
    
    .main .block-container {
        background: linear-gradient(135deg, rgba(8, 145, 178, 0.05) 0%, rgba(34, 211, 238, 0.03) 100%) !important;
        backdrop-filter: blur(8px);
        border-radius: 20px;
        padding: 0.5rem 1.2rem 0.5rem 1.2rem !important;
        margin: 0.2rem auto !important;
        max-width: 1000px;
        border: 1px solid rgba(8, 145, 178, 0.15);
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(207, 250, 254, 0.95) 100%) !important;
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(8, 145, 178, 0.3) !important;
        padding-top: 0.3rem !important;
    }
    
    [data-testid="stSidebar"] .stButton button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 4px 8px !important;
        font-size: 12px !important;
        width: 100% !important;
    }
    
    .title-container {
        text-align: center;
        padding: 0.2rem 0 0.2rem 0 !important;
    }
    
    .title-icon {
        width: 36px !important;
        height: 36px !important;
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        border-radius: 12px !important;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem !important;
        margin-bottom: 0.15rem !important;
    }
    
    .title-text {
        font-size: 1.2rem !important;
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        margin: 0 !important;
    }
    
    .title-subtitle {
        color: var(--text-light);
        font-size: 0.65rem !important;
    }
    
    .message-container {
        display: flex;
        align-items: flex-start;
        margin-bottom: 12px !important;
        width: 100%;
        animation: fadeIn 0.25s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(4px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .message-container.user { justify-content: flex-end; }
    .message-container.ai { justify-content: flex-start; }
    
    .message-content { display: flex; flex-direction: column; max-width: 75%; }
    
    .user-bubble {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        border-radius: 14px 14px 4px 14px;
        padding: 8px 14px !important;
        font-size: 13px;
        line-height: 1.45;
    }
    
    .ai-bubble {
        background: var(--white);
        color: var(--text-dark);
        border-radius: 14px 14px 14px 4px;
        padding: 8px 14px !important;
        border: 1px solid rgba(8, 145, 178, 0.15);
        font-size: 13px;
        line-height: 1.45;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    /* 确保时间戳可见 */
    .time-right, .time-left {
        font-size: 0.6rem !important;
        color: #64748b !important;
        margin-top: 4px !important;
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
    }
    .time-right { text-align: right; }
    .time-left { text-align: left; }
    
    .avatar-user, .avatar-ai {
        width: 32px !important;
        height: 32px !important;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.9rem !important;
        flex-shrink: 0;
    }
    
    .avatar-user {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        margin-left: 8px;
    }
    
    .avatar-ai {
        background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
        margin-right: 8px;
    }
    
    .knowledge-card {
        margin-top: 10px;
        padding: 10px;
        background: #f0fdf4;
        border-radius: 10px;
        border-left: 4px solid #22c55e;
    }
    
    .knowledge-title {
        font-size: 0.7rem;
        font-weight: bold;
        color: #0891b2;
        margin-bottom: 8px;
    }
    
    .knowledge-item {
        margin-bottom: 8px;
        padding: 6px;
        background: white;
        border-radius: 8px;
        font-size: 0.7rem;
    }
    
    .knowledge-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
    }
    
    .knowledge-dept {
        font-weight: bold;
        color: #0e7490;
    }
    
    .knowledge-score {
        background: #0891b2;
        color: white;
        padding: 0 6px;
        border-radius: 10px;
        font-size: 0.65rem;
    }
    
    .knowledge-question {
        color: #64748b;
        font-size: 0.65rem;
    }
    
    .knowledge-answer {
        color: #475569;
        font-size: 0.65rem;
        margin-top: 4px;
    }
    
    .stChatInput {
        padding: 4px 0 !important;
        margin: 0 !important;
        background: transparent !important;
        position: sticky !important;
        bottom: 0 !important;
    }
    
    .stChatInput > div > div > input {
        background: var(--white) !important;
        border: 1.5px solid var(--primary) !important;
        border-radius: 24px !important;
        padding: 8px 16px !important;
        height: 42px !important;
    }
    
    .stChatInput > div > div > button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%) !important;
        border-radius: 50% !important;
        width: 34px !important;
        height: 34px !important;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: var(--primary-soft); border-radius: 2px; }
    ::-webkit-scrollbar-thumb { background: var(--primary-light); border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# ========== 后端配置 ==========
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:6066")
BACKEND_PORT = os.getenv("BACKEND_PORT", "6066")

if not BACKEND_URL or BACKEND_URL == "":
    BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"

CHAT_URL = f"{BACKEND_URL}/chat"
HEALTH_URL = f"{BACKEND_URL}/health"
SEARCH_URL = f"{BACKEND_URL}/search"
UPLOAD_KNOWLEDGE_URL = f"{BACKEND_URL}/upload_knowledge_file"
UPLOAD_MULTIPLE_URL = f"{BACKEND_URL}/upload_multiple_files"
KNOWLEDGE_STATS_URL = f"{BACKEND_URL}/knowledge_base_stats"
CLEAR_KNOWLEDGE_URL = f"{BACKEND_URL}/clear_knowledge"
RELOAD_KNOWLEDGE_URL = f"{BACKEND_URL}/reload_knowledge"
EXPORT_URL = f"{BACKEND_URL}/export_conversation"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========== 数据模型 ==========
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    knowledge_sources: Optional[List[dict]] = None

    @classmethod
    def create(cls, role: MessageRole, content: str, knowledge_sources: Optional[List[dict]] = None):
        return cls(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
            timestamp=datetime.now(),
            knowledge_sources=knowledge_sources
        )


@dataclass
class ChatSession:
    session_id: str
    messages: List[Message] = field(default_factory=list)

    def add_message(self, message: Message):
        self.messages.append(message)

    def get_display_messages(self, limit: Optional[int] = None):
        if limit:
            return self.messages[-limit:]
        return self.messages

    def clear(self):
        self.messages = []


# ========== 系统提示词 ==========
MEDICAL_SYSTEM_PROMPT = """你是一名专业的医疗问答助手。

【回答规则】
1. 优先使用知识库中检索到的医疗知识来回答用户问题
2. 如果知识库中有相关信息，请基于这些信息回答
3. 对于严重的医疗问题，请提醒用户及时就医
4. 不能替代专业医生的诊断

【注意事项】
- 你是AI医疗助手，不能替代专业医生的诊断
- 对于紧急情况，建议立即就医"""


@dataclass
class AppSettings:
    model: str = "qwen-plus"
    temperature: float = 0.7
    max_length: int = 1024
    stream_mode: bool = False
    show_timestamp: bool = True
    max_history: int = 50
    system_prompt: str = MEDICAL_SYSTEM_PROMPT
    use_rag: bool = True
    rag_top_k: int = 3
    rag_threshold: float = 0.5


# ========== 状态管理 ==========
class SessionStateManager:
    @classmethod
    def initialize(cls):
        if "initialized" not in st.session_state:
            st.session_state.session = ChatSession(session_id=str(uuid.uuid4()))
            st.session_state.settings = AppSettings()
            st.session_state.initialized = True

            welcome_msg = Message.create(
                MessageRole.ASSISTANT,
                "🏥 **你好！我是基于千问+RAG的医疗聊天机器人**\n\n"
                "我是基于通义千问大模型和 BGE 向量检索的专业医疗问答系统。\n\n"
                "💡 **我可以帮助你：**\n"
                "• 解答疾病症状相关问题\n"
                "• 提供治疗方案参考\n"
                "• 回答用药指导问题\n"
                "• 📁 支持上传CSV文件更新知识库\n\n"
                "⚙️ **技术架构：**\n"
                "• 大模型：通义千问 (qwen-plus)\n"
                "• 向量检索：BGE-Large-ZH-V1.5\n"
                "• RAG增强：检索增强生成\n\n"
                "⚠️ **温馨提示：** 不能替代专业医生诊断，紧急情况请就医！\n\n"
                "有什么医疗问题需要帮助吗？😊"
            )
            st.session_state.session.add_message(welcome_msg)

    @classmethod
    def get_session(cls):
        return st.session_state.session

    @classmethod
    def get_settings(cls):
        return st.session_state.settings

    @classmethod
    def update_settings(cls, **kwargs):
        for key, value in kwargs.items():
            if hasattr(st.session_state.settings, key):
                setattr(st.session_state.settings, key, value)

    @classmethod
    def add_message(cls, role: MessageRole, content: str, knowledge_sources: Optional[List[dict]] = None):
        msg = Message.create(role, content, knowledge_sources)
        st.session_state.session.add_message(msg)
        return msg

    @classmethod
    def clear_session(cls):
        st.session_state.session.clear()
        cls.add_message(MessageRole.ASSISTANT, "✨ 对话已清空！有什么医疗问题我可以帮你？😊")


# ========== 消息渲染 ==========
def render_message_user(content: str, timestamp: datetime, show_time: bool = True):
    time_html = f'<div class="time-right">{timestamp.strftime("%H:%M")}</div>' if show_time else ''
    st.markdown(f"""
    <div class="message-container user">
        <div class="message-content">
            <div class="user-bubble">{content}</div>
            {time_html}
        </div>
        <div class="avatar-user">👤</div>
    </div>
    """, unsafe_allow_html=True)


def render_message_ai(content: str, timestamp: datetime, show_time: bool = True, knowledge_sources: Optional[List[dict]] = None):
    # 使用Streamlit原生布局
    col1, col2 = st.columns([1, 12])

    with col1:
        st.markdown('<div class="avatar-ai">🏥</div>', unsafe_allow_html=True)

    with col2:
        # AI消息内容
        st.markdown(f'<div class="ai-bubble">{content}</div>', unsafe_allow_html=True)

        # 知识来源
        if knowledge_sources and isinstance(knowledge_sources, list) and len(knowledge_sources) > 0:
            st.markdown('<div class="knowledge-card"><div class="knowledge-title">📚 参考知识来源</div>', unsafe_allow_html=True)
            for i, src in enumerate(knowledge_sources, 1):
                dept = src.get("department", "未知")
                score = src.get("score", 0)
                question = src.get("question", "")[:80]
                answer = src.get("answer", "")[:150]
                st.markdown(f'''
                <div class="knowledge-item">
                    <div class="knowledge-header">
                        <span class="knowledge-dept">{i}. 【{dept}】</span>
                        <span class="knowledge-score">置信度: {score:.2%}</span>
                    </div>
                    <div class="knowledge-question">📝 {question}{"..." if len(src.get("question", "")) > 80 else ""}</div>
                    <div class="knowledge-answer">💡 {answer}{"..." if len(answer) >= 150 else ""}</div>
                </div>
                ''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # 时间戳
        if show_time:
            st.markdown(f'<div class="time-left">{timestamp.strftime("%H:%M")}</div>', unsafe_allow_html=True)


def render_messages(messages: List[Message], show_timestamp: bool = True):
    for msg in messages:
        if msg.role == MessageRole.USER:
            render_message_user(msg.content, msg.timestamp, show_timestamp)
        else:
            render_message_ai(msg.content, msg.timestamp, show_timestamp, msg.knowledge_sources)


# ========== API调用 ==========
def check_backend_health():
    try:
        r = requests.get(HEALTH_URL, timeout=3)
        if r.status_code == 200:
            data = r.json()
            return {
                "status": "healthy",
                "knowledge_base_size": data.get("knowledge_base_size", 0)
            }
        return {"status": "error"}
    except:
        return {"status": "error"}


def search_knowledge(query: str, top_k: int = 3, threshold: float = 0.5):
    try:
        r = requests.post(SEARCH_URL, json={"query": query, "top_k": top_k, "threshold": threshold}, timeout=10)
        if r.status_code == 200:
            return r.json().get("results", [])
        return []
    except Exception as e:
        print(f"[ERROR] 搜索知识库失败: {e}")
        return []


def send_chat(query: str):
    settings = st.session_state.settings
    session = st.session_state.session

    data = {
        "query": query,
        "sys_prompt": settings.system_prompt,
        "history_len": max(1, settings.max_history // 2),
        "history": [{"role": m.role.value, "content": m.content} for m in session.get_display_messages(settings.max_history)],
        "temperature": settings.temperature,
        "top_p": 0.8,
        "max_tokens": settings.max_length,
        "stream": settings.stream_mode,
        "model": settings.model,
        "use_rag": settings.use_rag,
        "rag_top_k": settings.rag_top_k,
        "rag_threshold": settings.rag_threshold,
    }

    try:
        return requests.post(CHAT_URL, json=data, stream=settings.stream_mode, timeout=180)
    except:
        return None


def export_conversation():
    """导出对话记录"""
    session = st.session_state.session
    messages = session.get_display_messages()

    if not messages:
        return None, None

    # 构建对话数据
    conversation = []
    for msg in messages:
        conversation.append({
            "role": msg.role.value,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        })

    try:
        response = requests.post(
            EXPORT_URL,
            json={"conversation": conversation},
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("txt_content"), data.get("json_content")
        else:
            return None, None
    except Exception as e:
        print(f"[ERROR] 导出失败: {e}")
        return None, None


# ========== 知识库管理函数 ==========
def upload_csv_to_knowledge_base(file, max_per_file: int = 100):
    """上传CSV文件到知识库"""
    try:
        files = {"file": (file.name, file.getvalue(), "text/csv")}
        data = {"max_per_file": max_per_file}

        response = requests.post(
            UPLOAD_KNOWLEDGE_URL,
            files=files,
            data=data,
            timeout=60
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "message": f"上传失败: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def upload_multiple_csvs(files, max_per_file: int = 100):
    """批量上传CSV文件到知识库"""
    try:
        files_list = []
        for file in files:
            files_list.append(("files", (file.name, file.getvalue(), "text/csv")))

        response = requests.post(
            f"{UPLOAD_MULTIPLE_URL}?max_per_file={max_per_file}",
            files=files_list,
            timeout=180
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "message": f"上传失败: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_knowledge_base_stats():
    """获取知识库统计信息"""
    try:
        response = requests.get(KNOWLEDGE_STATS_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def clear_knowledge_base():
    """清空知识库"""
    try:
        response = requests.post(CLEAR_KNOWLEDGE_URL, timeout=30)
        if response.status_code == 200:
            return response.json()
        return {"status": "error"}
    except:
        return {"status": "error"}


def reload_knowledge_base():
    """重新加载知识库"""
    try:
        response = requests.post(RELOAD_KNOWLEDGE_URL, timeout=60)
        if response.status_code == 200:
            return response.json()
        return {"status": "error"}
    except:
        return {"status": "error"}


# ========== UI构建 ==========
def build_sidebar():
    settings = st.session_state.settings

    with st.sidebar:
        st.markdown("### 🏥 服务状态")
        health = check_backend_health()
        if health.get("status") == "healthy":
            st.success("✅ 后端服务正常")
            kb_size = health.get("knowledge_base_size", 0)
            if kb_size > 0:
                st.info(f"📚 医疗知识库: {kb_size} 条")
            else:
                st.warning("📚 知识库为空")
        else:
            st.error("❌ 后端服务异常")

        st.divider()

        # ========== 知识库管理部分 ==========
        st.markdown("### 📁 知识库管理")

        # 显示详细统计
        stats = get_knowledge_base_stats()
        if stats:
            with st.expander("📊 知识库统计", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("总文档数", stats.get("total_documents", 0))
                with col2:
                    st.metric("有效向量", stats.get("valid_vectors", 0))

                dept_stats = stats.get("department_stats", {})
                if dept_stats:
                    st.markdown("**科室分布:**")
                    for dept, count in dept_stats.items():
                        st.text(f"  {dept}: {count} 条")

                cache_info = f"缓存: {stats.get('cache_size', 0)} | 命中: {stats.get('cache_hits', 0)}"
                st.caption(cache_info)

        # 文件上传（单个文件）
        st.markdown("**📤 上传CSV文件**")
        uploaded_file = st.file_uploader(
            "选择CSV文件",
            type=['csv'],
            key="csv_uploader",
            help="支持CSV格式，自动识别问答案列"
        )

        if uploaded_file is not None:
            col1, col2 = st.columns(2)
            with col1:
                max_records = st.number_input("最大记录数", 10, 500, 100, 10, key="max_records")
            with col2:
                if st.button("📤 上传到知识库", use_container_width=True):
                    with st.spinner(f"正在上传 {uploaded_file.name}..."):
                        result = upload_csv_to_knowledge_base(uploaded_file, max_records)

                        if result and result.get("status") == "success":
                            st.success(f"✅ {result.get('message', '上传成功')}")
                            st.info(f"知识库总数: {result.get('total_knowledge_base', 0)} 条")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('message', '上传失败')}")

        # 批量上传
        with st.expander("📦 批量上传", expanded=False):
            uploaded_files = st.file_uploader(
                "选择多个CSV文件",
                type=['csv'],
                accept_multiple_files=True,
                key="multi_uploader",
                help="可同时上传多个CSV文件"
            )

            if uploaded_files:
                col1, col2 = st.columns(2)
                with col1:
                    max_records_batch = st.number_input("最大记录数/文件", 10, 500, 100, 10, key="batch_max_records")
                with col2:
                    if st.button("📦 批量上传", use_container_width=True):
                        with st.spinner(f"正在上传 {len(uploaded_files)} 个文件..."):
                            result = upload_multiple_csvs(uploaded_files, max_records_batch)

                            if result and result.get("status") == "success":
                                st.success(f"✅ 成功添加 {result.get('total_added', 0)} 条知识")
                                st.info(f"知识库总数: {result.get('total_knowledge_base', 0)} 条")

                                for res in result.get("results", []):
                                    if res.get("status") == "success":
                                        st.text(f"  📄 {res['file_name']}: +{res['added_count']}条")
                                    elif res.get("status") == "error":
                                        st.error(f"  ❌ {res['file_name']}: {res.get('message', '失败')}")

                                st.rerun()
                            else:
                                st.error(f"❌ {result.get('message', '上传失败')}")

        # 知识库操作按钮
        st.markdown("**🛠️ 知识库操作**")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🗑️ 清空", use_container_width=True, help="清空所有知识库数据"):
                result = clear_knowledge_base()
                if result and result.get("status") == "success":
                    st.success("✅ 知识库已清空")
                    st.rerun()
                else:
                    st.error("❌ 清空失败")

        with col2:
            if st.button("🔄 重载", use_container_width=True, help="从缓存重新加载知识库"):
                result = reload_knowledge_base()
                if result and result.get("status") == "success":
                    st.success(f"✅ {result.get('message', '重载成功')}")
                    st.rerun()
                else:
                    st.error("❌ 重载失败")

        with col3:
            if st.button("📊 刷新", use_container_width=True, help="刷新统计信息"):
                st.rerun()

        st.divider()

        # ========== 对话导出功能（上下排列）==========
        st.markdown("### 📄 对话管理")

        # 获取当前对话数量
        msg_count = len(st.session_state.session.get_display_messages())

        # 显示消息数量卡片
        st.markdown(f"""
        <div style="
            background: rgba(8, 145, 178, 0.08);
            border-radius: 10px;
            padding: 6px 12px;
            margin-bottom: 10px;
            text-align: center;
        ">
            <span style="font-size: 11px; color: #64748b;">📝 当前对话消息数</span><br>
            <span style="font-size: 16px; font-weight: 700; color: #0891b2;">{msg_count}</span>
        </div>
        """, unsafe_allow_html=True)

        # 导出按钮 - 上下排列（垂直）
        if st.button("📥 导出为 TXT", use_container_width=True, key="export_txt_btn"):
            txt_content, _ = export_conversation()
            if txt_content:
                st.download_button(
                    label="⬇️ 点击下载",
                    data=txt_content,
                    file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="download_txt_btn"
                )
            else:
                st.warning("暂无对话内容")

        if st.button("📋 导出为 JSON", use_container_width=True, key="export_json_btn"):
            _, json_content = export_conversation()
            if json_content:
                json_str = json.dumps(json_content, ensure_ascii=False, indent=2)
                st.download_button(
                    label="⬇️ 点击下载",
                    data=json_str,
                    file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_json_btn"
                )
            else:
                st.warning("暂无对话内容")

        st.divider()

        # ========== 原有配置部分 ==========
        st.markdown("### 🤖 模型配置")
        settings.model = st.selectbox("选择模型", ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-long"],
                                       index=0 if settings.model == "qwen-plus" else 0)

        st.markdown("### ⚙️ 参数调节")
        settings.temperature = st.slider("温度", 0.0, 2.0, settings.temperature, 0.1)
        settings.max_length = st.slider("最大回复长度", 256, 2048, settings.max_length, 128)

        st.markdown("### 📚 RAG 设置")
        settings.use_rag = st.checkbox("启用知识库检索", value=settings.use_rag)

        col1, col2 = st.columns(2)
        with col1:
            settings.rag_top_k = st.number_input("检索文档数", 1, 5, settings.rag_top_k, 1)
        with col2:
            settings.rag_threshold = st.slider("相似度阈值", 0.3, 0.9, settings.rag_threshold, 0.05)

        st.markdown("### 🎨 界面设置")
        settings.show_timestamp = st.checkbox("显示时间戳", value=settings.show_timestamp)
        settings.max_history = st.number_input("保留历史记录", 10, 100, settings.max_history, 10)

        st.markdown("### 🔧 高级设置")
        settings.stream_mode = st.checkbox("流式输出", value=settings.stream_mode,
                                            help="逐字显示回复，像打字机效果")
        settings.system_prompt = st.text_area("系统提示词", settings.system_prompt, height=100)

        st.divider()

        if st.button("🗑️ 清空对话", use_container_width=True):
            SessionStateManager.clear_session()
            st.rerun()


def build_header():
    st.markdown("""
    <div class="title-container">
        <div class="title-icon">🏥</div>
        <h1 class="title-text">基于千问+RAG的医疗聊天机器人</h1>
        <p class="title-subtitle">通义千问 + BGE 向量检索 | RAG 增强生成 | 专业医疗问答</p>
    </div>
    """, unsafe_allow_html=True)


# ========== 主应用 ==========
def main():
    SessionStateManager.initialize()
    build_sidebar()

    settings = st.session_state.settings
    session = st.session_state.session

    build_header()

    # RAG 状态提示
    health = check_backend_health()
    if settings.use_rag:
        if health.get("status") == "healthy":
            stats = get_knowledge_base_stats()
            kb_size = stats.get("total_documents", 0) if stats else health.get("knowledge_base_size", 0)

            if kb_size > 0:
                st.success(f"📚 RAG 模式已启用 - 知识库 {kb_size} 条")
                if stats and stats.get("department_stats"):
                    depts = list(stats["department_stats"].keys())
                    st.caption(f"科室: {', '.join(depts[:3])}{'...' if len(depts) > 3 else ''}")
            else:
                st.warning("📚 RAG 模式已启用 - 知识库为空，请上传CSV文件")
        else:
            st.warning("⚠️ RAG 模式已启用 - 后端连接失败")
    else:
        st.info("💬 普通对话模式 - RAG 已禁用")

    # 聊天消息区域
    chat_container = st.container()
    with chat_container:
        render_messages(session.get_display_messages(settings.max_history), settings.show_timestamp)

    # 输入框
    user_input = st.chat_input("输入医疗相关问题...", key="main_input")

    if user_input:
        # 显示用户消息
        SessionStateManager.add_message(MessageRole.USER, user_input)
        with chat_container:
            render_message_user(user_input, datetime.now(), settings.show_timestamp)

        # 第一步：检索知识库
        search_results = []
        if settings.use_rag:
            with st.spinner("🔍 正在检索医疗知识库..."):
                search_results = search_knowledge(
                    user_input,
                    top_k=settings.rag_top_k,
                    threshold=settings.rag_threshold
                )

            # 显示知识来源
            if search_results:
                with chat_container:
                    st.markdown("---")
                    st.markdown("📚 **【参考知识（来自本地知识库）】**")
                    for i, src in enumerate(search_results, 1):
                        dept = src.get("department", "未知")
                        q = src.get("question", "")[:60]
                        score = src.get("score", 0)
                        ans = src.get("answer", "")[:200]
                        with st.expander(f"{i}. 【{dept}】{q}（置信度 {score:.2%}）"):
                            st.write(ans + ("..." if len(ans) >= 200 else ""))
                    st.markdown("---")
                    st.info("🤖 **【AI回答】**")

        # 第二步：获取AI回答
        with st.spinner("🏥 正在生成回答..."):
            response = send_chat(user_input)

        if response is None or response.status_code != 200:
            with chat_container:
                st.error("❌ 请求失败")
        else:
            if settings.stream_mode:
                full_response = ""
                ph = st.empty()
                try:
                    for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
                        if chunk:
                            full_response += chunk
                            ph.markdown(f"""
                            <div class="message-container ai">
                                <div class="avatar-ai">🏥</div>
                                <div class="message-content">
                                    <div class="ai-bubble">{full_response} ▌</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    ph.empty()
                except Exception as e:
                    ph.empty()
                    with chat_container:
                        st.error(f"❌ 流式读取错误: {str(e)}")
            else:
                full_response = response.text

            if full_response:
                # 移除后端自动添加的免责声明
                display_response = full_response.replace("\n\n---\n⚠️ **本系统仅供参考，不能替代专业医疗诊断与建议。**", "")

                with chat_container:
                    render_message_ai(
                        content=display_response,
                        timestamp=datetime.now(),
                        knowledge_sources=search_results,
                        show_time=settings.show_timestamp
                    )

                # 保存到历史（包含知识来源）
                SessionStateManager.add_message(MessageRole.ASSISTANT, display_response, search_results)

                with chat_container:
                    st.caption("⚠️ **本系统仅供参考，不能替代专业医疗诊断与建议。**")

        st.rerun()


if __name__ == "__main__":
    main()