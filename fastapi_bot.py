"""
FastAPI 聊天机器人后端服务
阿里云百炼（通义千问）大模型调用 + BGE 向量检索（RAG）
医疗聊天机器人专用版 - 每个文件限制100条 - 带持久化缓存 - 支持图片分析
支持文件上传更新知识库
"""

from fastapi import FastAPI, Body, File, UploadFile, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, AsyncGenerator, Optional
import os
from openai import AsyncOpenAI
import numpy as np
from pathlib import Path
from functools import lru_cache
import pickle
import base64
import re
import io
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ========== 向量模型相关导入 ==========
from transformers import AutoModel, AutoTokenizer
import torch
import pandas as pd

# ========== 配置 ==========
# 阿里云百炼 API Key 配置（优先从环境变量读取）
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# 向量模型路径
VECTOR_MODEL_PATH = "./bge-large-zh-v1.5"

# 医疗数据路径
MEDICAL_DATA_DIR = "./Data"

# 每个 CSV 文件最多读取多少条数据
MAX_PER_FILE = 100

# 持久化缓存文件路径
VECTOR_CACHE_FILE = "./knowledge_base_cache.pkl"

# 创建FastAPI应用
app = FastAPI(
    title="医疗聊天机器人 API",
    description="基于通义千问 + BGE 向量检索的医疗问答系统（支持图片分析、文件上传更新知识库）",
    version="2.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 全局变量（向量模型和知识库）==========
embedding_model = None
embedding_tokenizer = None
knowledge_base = []          # 存储文档片段
knowledge_base_vectors = []  # 存储对应的向量


# ========== 持久化缓存函数 ==========
def save_knowledge_base_to_cache():
    """保存知识库到磁盘缓存"""
    try:
        vectors_list = []
        for vec in knowledge_base_vectors:
            if vec is not None:
                vectors_list.append(vec.tolist())
            else:
                vectors_list.append(None)

        cache_data = {
            "documents": knowledge_base,
            "vectors": vectors_list,
            "document_count": len(knowledge_base)
        }
        with open(VECTOR_CACHE_FILE, 'wb') as f:
            pickle.dump(cache_data, f)
        print(f"[INFO] ✅ 知识库已保存到缓存: {VECTOR_CACHE_FILE}")
        return True
    except Exception as e:
        print(f"[WARN] 保存知识库缓存失败: {e}")
        return False


def load_knowledge_base_from_cache() -> bool:
    """从磁盘缓存加载知识库"""
    global knowledge_base, knowledge_base_vectors

    try:
        cache_path = Path(VECTOR_CACHE_FILE)
        if not cache_path.exists():
            print(f"[INFO] 缓存文件不存在: {VECTOR_CACHE_FILE}")
            return False

        with open(VECTOR_CACHE_FILE, 'rb') as f:
            cache_data = pickle.load(f)

        knowledge_base = cache_data["documents"]

        knowledge_base_vectors = []
        for vec_list in cache_data["vectors"]:
            if vec_list is not None:
                knowledge_base_vectors.append(np.array(vec_list))
            else:
                knowledge_base_vectors.append(None)

        print(f"[INFO] ✅ 从缓存加载知识库成功: {len(knowledge_base)} 条文档")
        return True

    except Exception as e:
        print(f"[WARN] 加载知识库缓存失败: {e}")
        return False


def clear_knowledge_base_cache():
    """清空知识库缓存文件"""
    global knowledge_base, knowledge_base_vectors
    try:
        cache_path = Path(VECTOR_CACHE_FILE)
        if cache_path.exists():
            cache_path.unlink()
            print(f"[INFO] ✅ 已删除缓存文件: {VECTOR_CACHE_FILE}")
        knowledge_base = []
        knowledge_base_vectors = []
    except Exception as e:
        print(f"[WARN] 删除缓存文件失败: {e}")


# ========== 医疗数据加载函数 ==========
def load_medical_csv_data(data_dir: str = "./Data", max_per_file: int = MAX_PER_FILE) -> List[str]:
    """从 Data 文件夹加载医疗 CSV 数据"""
    documents = []

    csv_files = {
        "Andrology.csv": "男科",
        "IM.csv": "心血管科",
        "Obstetrics.csv": "妇产科",
        "Oncology.csv": "肿瘤科",
        "Pediatrics.csv": "儿科",
        "Surgery.csv": "外科"
    }

    print(f"[INFO] 开始加载医疗数据（每个文件最多 {max_per_file} 条）...")

    for csv_file, department in csv_files.items():
        file_path = Path(data_dir) / csv_file

        if not file_path.exists():
            print(f"[WARN] 文件不存在: {file_path}")
            continue

        try:
            df = None
            for enc in ['gb18030', 'gbk', 'utf-8', 'utf-8-sig', 'gb2312']:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    print(f"[INFO] 读取 {csv_file} 成功 (编码: {enc})")
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
                except Exception as e:
                    continue

            if df is None or df.empty:
                print(f"[ERROR] 无法读取 {csv_file}")
                continue

            original_count = len(df)
            if len(df) > max_per_file:
                df = df.head(max_per_file)
                print(f"[INFO]   {csv_file} 原 {original_count} 条，限制为 {max_per_file} 条")
            else:
                print(f"[INFO]   {csv_file} 共 {original_count} 条")

            question_col = None
            answer_col = None

            possible_question_cols = ['ask', 'question', 'title', '问题', 'query', 'Question', 'Ask']
            for col in possible_question_cols:
                if col in df.columns:
                    question_col = col
                    break

            if question_col is None:
                question_col = df.columns[0]
                print(f"[INFO]  使用第一列作为问题列: {question_col}")
            else:
                print(f"[INFO]  问题列: {question_col}")

            possible_answer_cols = ['answer', 'Answer', '答案', 'response', 'content', 'Response']
            for col in possible_answer_cols:
                if col in df.columns:
                    answer_col = col
                    break

            if answer_col is None and len(df.columns) > 1:
                answer_col = df.columns[1]
                print(f"[INFO]  使用第二列作为答案列: {answer_col}")
            elif answer_col:
                print(f"[INFO]  答案列: {answer_col}")
            else:
                print(f"[WARN]  未找到答案列")

            valid_count = 0
            for _, row in df.iterrows():
                try:
                    question = str(row[question_col]) if pd.notna(row[question_col]) else ""
                    question = question.strip()

                    if answer_col and pd.notna(row[answer_col]):
                        answer = str(row[answer_col]).strip()
                    else:
                        answer = ""

                    if not question or len(question) < 5:
                        continue

                    if len(question) > 300:
                        question = question[:300]
                    if len(answer) > 800:
                        answer = answer[:800]

                    if answer:
                        doc = f"""【科室】{department}
【问题】{question}
【回答】{answer}"""
                    else:
                        doc = f"""【科室】{department}
【问题】{question}"""

                    documents.append(doc)
                    valid_count += 1

                except Exception as e:
                    continue

            print(f"[INFO]   从 {csv_file} 加载了 {valid_count} 条有效记录")

        except Exception as e:
            print(f"[ERROR] 处理 {csv_file} 失败: {e}")

    print(f"[INFO] 📚 总共加载 {len(documents)} 条医疗知识")
    return documents


# ========== 向量模型加载与工具函数 ==========

def load_embedding_model():
    """加载 BGE 向量模型"""
    global embedding_model, embedding_tokenizer
    if embedding_model is None:
        print("[INFO] 正在加载向量模型...")
        try:
            embedding_model = AutoModel.from_pretrained(VECTOR_MODEL_PATH)
            embedding_tokenizer = AutoTokenizer.from_pretrained(VECTOR_MODEL_PATH)
            embedding_model.eval()
            print("[INFO] 向量模型加载完成")
        except Exception as e:
            print(f"[WARN] 向量模型加载失败: {e}")
            print("[INFO] RAG 功能将不可用，聊天功能正常")
            embedding_model = None
            embedding_tokenizer = None
    return embedding_model, embedding_tokenizer


@lru_cache(maxsize=128)
def text_to_vector_cached(text: str) -> Optional[tuple]:
    """将文本转换为向量（带缓存）"""
    model, tokenizer = load_embedding_model()
    if model is None:
        return None

    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)

    with torch.no_grad():
        outputs = model(**inputs)
        vector = outputs.last_hidden_state.mean(dim=1)
        vector = torch.nn.functional.normalize(vector, p=2, dim=1)

    return tuple(vector.squeeze().numpy().tolist())


def text_to_vector(text: str) -> Optional[np.ndarray]:
    """将文本转换为向量（封装缓存函数）"""
    result = text_to_vector_cached(text)
    if result is None:
        return None
    return np.array(result)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """计算余弦相似度"""
    return float(np.dot(vec1, vec2))


def search_knowledge_base(query: str, top_k: int = 3, threshold: float = 0.5) -> List[dict]:
    """
    在知识库中搜索相关内容，返回带来源和置信度的结果
    """
    if not knowledge_base or len(knowledge_base_vectors) == 0:
        return []

    query_vec = text_to_vector(query)
    if query_vec is None:
        return []

    similarities = []
    for i, doc_vec in enumerate(knowledge_base_vectors):
        if doc_vec is not None:
            sim = cosine_similarity(query_vec, doc_vec)
            if sim >= threshold:
                # 解析文档内容，提取科室、问题和答案
                content = knowledge_base[i]
                department = ""
                question = ""
                answer = ""

                lines = content.split('\n')
                for line in lines:
                    if line.startswith('【科室】'):
                        department = line.replace('【科室】', '').strip()
                    elif line.startswith('【问题】'):
                        question = line.replace('【问题】', '').strip()
                    elif line.startswith('【回答】'):
                        answer = line.replace('【回答】', '').strip()

                similarities.append({
                    "index": i,
                    "department": department,
                    "question": question,
                    "answer": answer[:300],
                    "score": sim
                })

    similarities.sort(key=lambda x: x["score"], reverse=True)
    return similarities[:top_k]


def init_knowledge_base(documents: List[str]):
    """初始化知识库（文档向量化）"""
    global knowledge_base, knowledge_base_vectors

    if not documents:
        knowledge_base = []
        knowledge_base_vectors = []
        print("[INFO] 知识库已清空")
        return

    knowledge_base = documents
    knowledge_base_vectors = []

    print(f"[INFO] 正在向量化 {len(documents)} 个文档...")
    for idx, doc in enumerate(documents):
        vec = text_to_vector(doc)
        knowledge_base_vectors.append(vec)
        if (idx + 1) % 50 == 0:
            print(f"[INFO] 已向量化 {idx + 1}/{len(documents)} 个文档")

    valid_count = len([v for v in knowledge_base_vectors if v is not None])
    print(f"[INFO] 知识库向量化完成，共 {valid_count}/{len(documents)} 个有效向量")


# ========== 辅助函数 ==========
def extract_text_from_image(image_base64: str) -> str:
    """
    从图片中提取文本信息（使用通义千问多模态能力）
    返回图片描述文本
    """
    try:
        client = _client()
        response = client.chat.completions.create(
            model="qwen-vl-plus",  # 使用通义千问的多模态模型
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请详细描述这张图片中的内容，包括：1. 你看到了什么；2. 如果包含文字，请读出文字内容；3. 如果是医学相关图片（如皮肤症状、检查报告、药品包装等），请重点分析可能反映的医疗信息。"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                    ]
                }
            ],
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ERROR] 图片分析失败: {e}")
        return f"（图片分析失败: {str(e)}）"


# ========== API 接口 ==========

@app.get("/cache_stats")
async def cache_stats():
    """获取向量缓存统计信息"""
    cache_info = text_to_vector_cached.cache_info()
    return {
        "hits": cache_info.hits,
        "misses": cache_info.misses,
        "maxsize": cache_info.maxsize,
        "currsize": cache_info.currsize
    }


@app.post("/clear_cache")
async def clear_cache():
    """清空向量缓存"""
    text_to_vector_cached.cache_clear()
    return {"status": "success", "message": "向量缓存已清空"}


def _client() -> AsyncOpenAI:
    """创建异步OpenAI客户端"""
    return AsyncOpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL,
    )


@app.get("/")
async def root():
    """根路径，检查服务状态"""
    return {
        "status": "ok",
        "message": "医疗聊天机器人 API is running with RAG support",
        "service": "阿里云百炼 - 通义千问 + BGE 向量检索",
        "rag_available": embedding_model is not None,
        "knowledge_base_size": len(knowledge_base),
        "cache_info": {
            "hits": text_to_vector_cached.cache_info().hits,
            "misses": text_to_vector_cached.cache_info().misses,
            "currsize": text_to_vector_cached.cache_info().currsize
        }
    }


@app.get("/health")
async def health():
    """健康检查接口"""
    if not DASHSCOPE_API_KEY:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "API Key 未配置，请设置环境变量 DASHSCOPE_API_KEY",
            }
        )
    return {
        "status": "healthy",
        "api_key_configured": True,
        "base_url": DASHSCOPE_BASE_URL,
        "rag_available": embedding_model is not None,
        "knowledge_base_size": len(knowledge_base),
        "cache_size": text_to_vector_cached.cache_info().currsize
    }


@app.post("/init_knowledge")
async def setup_knowledge(
    documents: List[str] = Body(..., description="文档列表")
):
    """初始化知识库"""
    if embedding_model is None:
        return JSONResponse(
            status_code=503,
            content={"error": "向量模型未加载，RAG 功能不可用"}
        )

    init_knowledge_base(documents)
    save_knowledge_base_to_cache()
    return {
        "status": "success",
        "message": f"已加载 {len(documents)} 个文档",
        "document_count": len(documents),
        "valid_vectors": len([v for v in knowledge_base_vectors if v is not None])
    }


@app.post("/add_documents")
async def add_documents(
    documents: List[str] = Body(..., description="要添加的文档列表")
):
    """向知识库添加新文档"""
    if embedding_model is None:
        return JSONResponse(
            status_code=503,
            content={"error": "向量模型未加载，RAG 功能不可用"}
        )

    added = 0
    for doc in documents:
        if doc and doc not in knowledge_base:
            knowledge_base.append(doc)
            vec = text_to_vector(doc)
            knowledge_base_vectors.append(vec)
            added += 1

    if added > 0:
        save_knowledge_base_to_cache()

    print(f"[INFO] 已添加 {added} 个新文档到知识库")
    return {
        "status": "success",
        "message": f"已添加 {added} 个新文档",
        "total_documents": len(knowledge_base)
    }


@app.post("/clear_knowledge")
async def clear_knowledge():
    """清空知识库"""
    global knowledge_base, knowledge_base_vectors
    knowledge_base = []
    knowledge_base_vectors = []
    clear_knowledge_base_cache()
    return {
        "status": "success",
        "message": "知识库已清空"
    }


@app.get("/knowledge_status")
async def knowledge_status():
    """查看知识库状态"""
    return {
        "initialized": len(knowledge_base) > 0,
        "document_count": len(knowledge_base),
        "rag_available": embedding_model is not None
    }


@app.post("/search")
async def search_documents(
    query: str = Body(..., description="搜索查询"),
    top_k: int = Body(3, description="返回结果数量"),
    threshold: float = Body(0.5, description="相似度阈值")
):
    """向量检索接口 - 返回带置信度的知识来源"""
    if embedding_model is None:
        return JSONResponse(
            status_code=503,
            content={"error": "向量模型未加载，RAG 功能不可用"}
        )

    results = search_knowledge_base(query, top_k, threshold)
    print(f"[SEARCH] 查询: {query[:50]}... 找到 {len(results)} 条结果")
    for r in results:
        print(f"   - {r.get('department', '未知')}: {r['score']:.4f}")

    return {
        "query": query,
        "results": results,
        "cache_info": {
            "hits": text_to_vector_cached.cache_info().hits,
            "misses": text_to_vector_cached.cache_info().misses
        }
    }


# ========== 文件上传接口 ==========

@app.post("/upload_knowledge_file")
async def upload_knowledge_file(
    file: UploadFile = File(..., description="上传CSV文件更新知识库"),
    max_per_file: int = Body(100, description="每个文件最大读取条数")
):
    """
    上传CSV文件来更新知识库
    支持文件名包含科室信息，如 Andrology.csv 会自动识别为男科
    """
    # 检查文件类型
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="只支持CSV文件")

    # 科室映射
    department_map = {
        "Andrology": "男科",
        "IM": "心血管科",
        "Obstetrics": "妇产科",
        "Oncology": "肿瘤科",
        "Pediatrics": "儿科",
        "Surgery": "外科"
    }

    # 从文件名推断科室
    department = "通用"
    for key, dept in department_map.items():
        if key in file.filename:
            department = dept
            break

    try:
        # 读取文件内容
        contents = await file.read()

        # 尝试不同编码读取CSV
        df = None
        for enc in ['gb18030', 'gbk', 'utf-8', 'utf-8-sig', 'gb2312']:
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding=enc)
                print(f"[INFO] 读取 {file.filename} 成功 (编码: {enc})")
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                continue

        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="无法读取CSV文件")

        # 限制数据量
        original_count = len(df)
        if len(df) > max_per_file:
            df = df.head(max_per_file)

        # 识别列名
        question_col = None
        answer_col = None

        possible_question_cols = ['ask', 'question', 'title', '问题', 'query', 'Question', 'Ask', 'q']
        for col in possible_question_cols:
            if col in df.columns:
                question_col = col
                break

        if question_col is None:
            question_col = df.columns[0]

        possible_answer_cols = ['answer', 'Answer', '答案', 'response', 'content', 'Response', 'a']
        for col in possible_answer_cols:
            if col in df.columns:
                answer_col = col
                break

        if answer_col is None and len(df.columns) > 1:
            answer_col = df.columns[1]

        # 处理数据
        new_documents = []
        for _, row in df.iterrows():
            try:
                question = str(row[question_col]) if pd.notna(row[question_col]) else ""
                question = question.strip()

                if answer_col and pd.notna(row[answer_col]):
                    answer = str(row[answer_col]).strip()
                else:
                    answer = ""

                if not question or len(question) < 3:
                    continue

                if len(question) > 300:
                    question = question[:300]
                if len(answer) > 800:
                    answer = answer[:800]

                if answer:
                    doc = f"""【科室】{department}
【问题】{question}
【回答】{answer}"""
                else:
                    doc = f"""【科室】{department}
【问题】{question}"""

                new_documents.append(doc)

            except Exception as e:
                continue

        # 添加到知识库
        added_count = 0
        for doc in new_documents:
            if doc not in knowledge_base:
                knowledge_base.append(doc)
                vec = text_to_vector(doc)
                knowledge_base_vectors.append(vec)
                added_count += 1

        # 保存缓存
        if added_count > 0:
            save_knowledge_base_to_cache()

        print(f"[INFO] 从 {file.filename} 添加了 {added_count} 条新文档到知识库")

        return {
            "status": "success",
            "message": f"成功添加 {added_count} 条新知识",
            "file_name": file.filename,
            "department": department,
            "total_read": len(new_documents),
            "added_count": added_count,
            "total_knowledge_base": len(knowledge_base)
        }

    except Exception as e:
        print(f"[ERROR] 上传文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理文件失败: {str(e)}")


@app.post("/upload_multiple_files")
async def upload_multiple_files(
    files: List[UploadFile] = File(..., description="上传多个CSV文件"),
    max_per_file: int = 100
):
    """
    批量上传多个CSV文件更新知识库
    """
    results = []
    total_added = 0

    for file in files:
        if not file.filename.endswith('.csv'):
            results.append({
                "file_name": file.filename,
                "status": "skipped",
                "message": "不是CSV文件"
            })
            continue

        # 科室映射
        department_map = {
            "Andrology": "男科",
            "IM": "心血管科",
            "Obstetrics": "妇产科",
            "Oncology": "肿瘤科",
            "Pediatrics": "儿科",
            "Surgery": "外科"
        }

        department = "通用"
        for key, dept in department_map.items():
            if key in file.filename:
                department = dept
                break

        try:
            contents = await file.read()

            df = None
            for enc in ['gb18030', 'gbk', 'utf-8', 'utf-8-sig', 'gb2312']:
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding=enc)
                    break
                except:
                    continue

            if df is None or df.empty:
                results.append({
                    "file_name": file.filename,
                    "status": "error",
                    "message": "无法读取文件"
                })
                continue

            if len(df) > max_per_file:
                df = df.head(max_per_file)

            # 识别列名
            question_col = df.columns[0]
            answer_col = df.columns[1] if len(df.columns) > 1 else None

            for col in df.columns:
                if col in ['ask', 'question', 'title', '问题', 'query']:
                    question_col = col
                if col in ['answer', 'Answer', '答案', 'response']:
                    answer_col = col

            new_documents = []
            for _, row in df.iterrows():
                try:
                    question = str(row[question_col]) if pd.notna(row[question_col]) else ""
                    question = question.strip()

                    if answer_col and pd.notna(row[answer_col]):
                        answer = str(row[answer_col]).strip()
                    else:
                        answer = ""

                    if not question or len(question) < 3:
                        continue

                    if len(question) > 300:
                        question = question[:300]
                    if len(answer) > 800:
                        answer = answer[:800]

                    if answer:
                        doc = f"""【科室】{department}
【问题】{question}
【回答】{answer}"""
                    else:
                        doc = f"""【科室】{department}
【问题】{question}"""

                    new_documents.append(doc)
                except:
                    continue

            added_count = 0
            for doc in new_documents:
                if doc not in knowledge_base:
                    knowledge_base.append(doc)
                    vec = text_to_vector(doc)
                    knowledge_base_vectors.append(vec)
                    added_count += 1

            total_added += added_count

            results.append({
                "file_name": file.filename,
                "status": "success",
                "department": department,
                "read_count": len(new_documents),
                "added_count": added_count
            })

        except Exception as e:
            results.append({
                "file_name": file.filename,
                "status": "error",
                "message": str(e)
            })

    if total_added > 0:
        save_knowledge_base_to_cache()

    return {
        "status": "success",
        "total_added": total_added,
        "files_processed": len(results),
        "results": results,
        "total_knowledge_base": len(knowledge_base)
    }


@app.get("/knowledge_base_stats")
async def knowledge_base_stats():
    """获取知识库详细统计信息"""
    # 统计各科室数量
    dept_stats = {}
    for doc in knowledge_base:
        lines = doc.split('\n')
        for line in lines:
            if line.startswith('【科室】'):
                dept = line.replace('【科室】', '').strip()
                dept_stats[dept] = dept_stats.get(dept, 0) + 1
                break

    return {
        "total_documents": len(knowledge_base),
        "valid_vectors": len([v for v in knowledge_base_vectors if v is not None]),
        "department_stats": dept_stats,
        "cache_size": text_to_vector_cached.cache_info().currsize,
        "cache_hits": text_to_vector_cached.cache_info().hits,
        "cache_misses": text_to_vector_cached.cache_info().misses
    }


@app.post("/reload_knowledge")
async def reload_knowledge():
    """重新加载知识库（从缓存）"""
    global knowledge_base, knowledge_base_vectors

    knowledge_base = []
    knowledge_base_vectors = []

    if load_knowledge_base_from_cache():
        # 重新向量化
        for idx, doc in enumerate(knowledge_base):
            vec = text_to_vector(doc)
            knowledge_base_vectors.append(vec)

        return {
            "status": "success",
            "message": f"已重新加载 {len(knowledge_base)} 条文档",
            "document_count": len(knowledge_base)
        }
    else:
        return {
            "status": "error",
            "message": "无法加载缓存"
        }


# ========== 对话导出接口 ==========

@app.post("/export_conversation")
async def export_conversation(request: Request):
    """
    导出对话记录
    支持导出为 TXT 和 JSON 格式
    """
    try:
        # 获取请求体
        body = await request.json()
        conversation = body.get("conversation", [])

        print(f"[EXPORT] 收到导出请求，对话条数: {len(conversation)}")

        if not conversation:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "没有对话内容"}
            )

        # 生成导出数据
        export_data = {
            "export_time": datetime.now().isoformat(),
            "total_messages": len(conversation),
            "conversation": conversation
        }

        # 生成 TXT 格式
        txt_content = "=" * 60 + "\n"
        txt_content += f"对话记录导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        txt_content += f"消息总数: {len(conversation)}\n"
        txt_content += "=" * 60 + "\n\n"

        for i, msg in enumerate(conversation, 1):
            role = "用户" if msg.get("role") == "user" else "AI助手"
            content = msg.get("content", "")
            txt_content += f"[{i}] {role}\n"
            txt_content += f"{content}\n"
            txt_content += "-" * 40 + "\n\n"

        txt_content += "=" * 60 + "\n"
        txt_content += "⚠️ 本对话仅供参考，不能替代专业医疗诊断与建议。\n"

        print(f"[EXPORT] 导出成功，生成 TXT 长度: {len(txt_content)}")

        return {
            "status": "success",
            "txt_content": txt_content,
            "json_content": export_data,
            "message_count": len(conversation)
        }

    except Exception as e:
        print(f"[ERROR] 导出对话失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


# ========== 医疗专用系统提示词 ==========
MEDICAL_SYSTEM_PROMPT = """你是一名专业的医疗问答助手。

【回答规则】
1. 请基于检索到的医疗知识库资料来回答用户问题
2. 回答要专业、准确、易懂
3. 对于严重的医疗问题，请提醒用户及时就医
4. 不能替代专业医生的诊断

【注意事项】
- 你是AI医疗助手，不能替代专业医生的诊断
- 对于紧急情况，建议立即就医
- 用药问题请咨询执业医师或药师"""


@app.post("/chat")
async def chat(
    query: str = Body(..., description="用户输入的问题"),
    image_base64: Optional[str] = Body(None, description="图片的base64编码"),
    sys_prompt: str = Body(MEDICAL_SYSTEM_PROMPT, description="系统提示词"),
    history_len: int = Body(1, description="保留历史对话的轮数"),
    history: List[dict] = Body([], description="历史对话记录"),
    temperature: float = Body(0.7, description="采样温度"),
    top_p: float = Body(0.8, description="核采样参数"),
    max_tokens: int = Body(1024, description="最大输出token数"),
    stream: bool = Body(True, description="是否流式返回"),
    model: str = Body("qwen-plus", description="模型名称"),
    use_rag: bool = Body(True, description="是否启用知识库检索增强"),
    rag_top_k: int = Body(3, description="RAG 检索返回的文档数量"),
    rag_threshold: float = Body(0.5, description="RAG 相似度阈值"),
):
    """
    聊天接口 - 支持 RAG 和多模态图片分析

    如果上传了图片，会先调用多模态模型分析图片内容，
    然后将分析结果与用户问题一起作为查询文本进行 RAG 检索和回答生成
    """

    if not DASHSCOPE_API_KEY:
        return JSONResponse(
            status_code=500,
            content={"error": "未配置 API Key", "message": "请设置环境变量 DASHSCOPE_API_KEY"},
        )

    valid_models = ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-long"]
    if model not in valid_models:
        model = "qwen-plus"

    # ========== 处理图片：提取图片描述 ==========
    image_description = ""
    if image_base64:
        print("[INFO] 正在分析上传的图片...")
        try:
            # 使用同步方式分析图片（因为通义千问多模态API）
            import asyncio
            # 在线程池中运行同步的图片分析
            loop = asyncio.get_event_loop()
            image_description = await loop.run_in_executor(
                None, extract_text_from_image, image_base64
            )
            print(f"[INFO] 图片分析完成，描述长度: {len(image_description)}")

            # 将图片描述添加到查询中
            if image_description:
                query = f"[用户上传了图片]\n图片分析结果：{image_description}\n\n用户问题：{query}"
        except Exception as e:
            print(f"[ERROR] 图片分析失败: {e}")
            query = f"[用户上传了图片但分析失败: {str(e)}]\n\n用户问题：{query}"

    # ========== RAG：知识库检索（用于增强系统提示词）==========
    rag_results = []
    knowledge_context = ""

    if use_rag and embedding_model is not None and knowledge_base:
        # 使用原始问题（不包含图片描述）进行检索，或者使用处理后的查询
        search_query = query.split("用户问题：")[-1] if "用户问题：" in query else query
        rag_results = search_knowledge_base(search_query, top_k=rag_top_k, threshold=rag_threshold)
        print(f"[RAG] 检索到 {len(rag_results)} 条相关内容")
        for r in rag_results:
            print(f"   - 科室: {r.get('department', '未知')}, 相似度: {r['score']:.4f}")

        # 构建知识上下文
        if rag_results:
            knowledge_context = "\n\n【参考资料】\n"
            for i, result in enumerate(rag_results, 1):
                department = result.get('department', '未知')
                question = result.get('question', '')
                answer = result.get('answer', '')
                knowledge_context += f"\n{i}. 【{department}科】相关问题：{question}\n   参考回答：{answer}\n"

    # ========== 构建消息列表 ==========
    messages: List[dict] = []

    # 增强系统提示词
    if use_rag and knowledge_context:
        enhanced_sys_prompt = f"""{sys_prompt}

{knowledge_context}

请基于上述【参考资料】中的内容来回答用户问题。"""
        messages.append({"role": "system", "content": enhanced_sys_prompt})
    else:
        messages.append({"role": "system", "content": sys_prompt})
        if use_rag:
            messages.append({"role": "system", "content": "⚠️ 提示：当前知识库中没有找到与用户问题直接相关的资料，请基于你的医学知识回答。"})

    # 添加历史对话
    if history_len > 0 and history:
        max_history_messages = history_len * 2
        recent_history = history[-max_history_messages:] if len(history) > max_history_messages else history
        messages.extend(recent_history)

    # 添加当前用户问题（支持多模态）
    messages.append({"role": "user", "content": query})

    print(f"[DEBUG] 调用模型: {model}, RAG 启用: {use_rag}, 检索到 {len(rag_results)} 条")
    print(f"[DEBUG] 是否有图片: {image_base64 is not None}, 查询长度: {len(query)}")

    client = _client()

    if not stream:
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=False,
            )
            content = resp.choices[0].message.content
            return JSONResponse(content=content)

        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] 非流式调用失败: {error_msg}")
            if "Invalid API Key" in error_msg or "authentication" in error_msg.lower():
                return JSONResponse(status_code=401, content={"error": "API Key 无效"})
            else:
                return JSONResponse(status_code=502, content={"error": error_msg})

    # ========== 流式输出：只返回 AI 回答 ==========
    async def stream_generator() -> AsyncGenerator[str, None]:
        try:
            stream_response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream_response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content

            # 发送免责声明
            yield "\n\n---\n⚠️ **本系统仅供参考，不能替代专业医疗诊断与建议。**"

        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] 流式调用失败: {error_msg}")
            if "Invalid API Key" in error_msg or "authentication" in error_msg.lower():
                yield f"\n[错误] API Key 无效，请检查配置"
            else:
                yield f"\n[错误] {error_msg}"

    return StreamingResponse(stream_generator(), media_type="text/plain")


@app.get("/models")
async def list_models():
    """获取可用的模型列表"""
    return {
        "models": [
            {"name": "qwen-plus", "description": "通义千问 Plus - 通用对话，性价比高"},
            {"name": "qwen-turbo", "description": "通义千问 Turbo - 快速响应，成本更低"},
            {"name": "qwen-max", "description": "通义千问 Max - 最强能力，复杂任务"},
            {"name": "qwen-long", "description": "通义千问 Long - 长文本处理"},
            {"name": "qwen-vl-plus", "description": "通义千问 VL Plus - 多模态图片分析"}
        ]
    }


# ========== 启动事件（带缓存加载）==========
@app.on_event("startup")
async def startup_event():
    """应用启动时执行 - 优先从缓存加载"""
    print("=" * 60)
    print("🚀 医疗聊天机器人 FastAPI 服务启动中...")
    print("=" * 60)

    load_embedding_model()

    if embedding_model is not None:
        print("✅ 向量模型加载成功，RAG 功能可用")
        print("✅ 缓存机制已启用（最多缓存128个查询）")
        print("✅ 相似度阈值过滤已启用")
        print(f"✅ 每个 CSV 文件限制读取: {MAX_PER_FILE} 条")
        print("✅ 多模态图片分析已启用（qwen-vl-plus）")
        print("✅ 文件上传更新知识库已启用")

        print("\n[INFO] 尝试从缓存加载知识库...")
        if load_knowledge_base_from_cache():
            print(f"✅ 从缓存加载知识库完成: {len(knowledge_base)} 条文档")
            print("   💡 提示: 缓存文件存在，跳过数据加载和向量化过程")
        else:
            print("\n[INFO] 缓存不存在，开始加载医疗数据...")
            medical_docs = load_medical_csv_data(MEDICAL_DATA_DIR, max_per_file=MAX_PER_FILE)

            if medical_docs:
                init_knowledge_base(medical_docs)
                save_knowledge_base_to_cache()
                print(f"\n✅ 已加载 {len(medical_docs)} 条医疗知识库文档")
                print("   包含科室: 男科、心血管科、妇产科、肿瘤科、儿科、外科")
                print("   💾 已保存到缓存，下次启动将直接加载")
            else:
                print("\n[WARN] 未找到医疗数据，使用默认知识库")
                default_docs = [
                    "医疗问答助手：请提供医疗相关问题，我会尽力为您解答。",
                    "常见医疗问题包括：症状咨询、治疗方案、用药指导等。",
                ]
                init_knowledge_base(default_docs)
                print(f"✅ 已加载 {len(default_docs)} 个默认知识库文档")
    else:
        print("⚠️ 向量模型加载失败，RAG 功能将不可用")
        print("   聊天功能正常，请检查模型路径: " + VECTOR_MODEL_PATH)

    print("\n" + "=" * 60)
    print("📊 可用接口:")
    print("   GET  /                      - 服务信息")
    print("   GET  /health                - 健康检查")
    print("   GET  /models                - 模型列表")
    print("   GET  /cache_stats           - 缓存统计")
    print("   POST /clear_cache           - 清空内存缓存")
    print("   GET  /knowledge_status      - 知识库状态")
    print("   GET  /knowledge_base_stats  - 知识库详细统计")
    print("   POST /search                - 向量检索（返回带置信度的知识来源）")
    print("   POST /chat                  - 聊天对话（支持图片上传分析）")
    print("   POST /add_documents         - 添加文档")
    print("   POST /clear_knowledge       - 清空知识库（同时删除缓存）")
    print("   POST /upload_knowledge_file - 上传CSV文件更新知识库")
    print("   POST /upload_multiple_files - 批量上传CSV文件")
    print("   POST /reload_knowledge      - 重新加载知识库")
    print("   POST /export_conversation   - 导出对话记录")
    print("=" * 60)


# ========== 主入口 ==========
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🚀 启动医疗聊天机器人后端服务")
    print("=" * 60)
    print(f"📡 API 地址: http://127.0.0.1:6066")
    print(f"📚 API 文档: http://127.0.0.1:6066/docs")
    print(f"❤️ 健康检查: http://127.0.0.1:6066/health")
    print(f"📖 知识库状态: http://127.0.0.1:6066/knowledge_status")
    print(f"📊 缓存统计: http://127.0.0.1:6066/cache_stats")
    print("=" * 60)
    print("按 Ctrl+C 停止服务")
    print("=" * 60)

    uvicorn.run(app, host="127.0.0.1", port=6066, log_level="info")