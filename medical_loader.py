"""
医疗数据加载器 - 专门读取 Data 文件夹中的 CSV 文件
"""

import pandas as pd
from pathlib import Path
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_medical_data(data_dir: str = "./Data") -> List[str]:
    """
    加载所有医疗 CSV 文件，返回文档列表
    """
    documents = []

    # 科室映射
    csv_files = {
        "Andrology.csv": "男科",
        "IM.csv": "心血管科",
        "Obstetrics.csv": "妇产科",
        "Oncology.csv": "肿瘤科",
        "Pediatrics.csv": "儿科",
        "Surgery.csv": "外科"
    }

    for csv_file, department in csv_files.items():
        file_path = Path(data_dir) / csv_file

        if not file_path.exists():
            logger.warning(f"文件不存在: {file_path}")
            continue

        try:
            # 尝试多种编码读取
            df = None
            for enc in ['gb18030', 'gbk', 'utf-8', 'utf-8-sig']:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    logger.info(f"✅ 读取 {csv_file} 成功 (编码: {enc})")
                    break
                except:
                    continue

            if df is None:
                logger.error(f"无法读取 {csv_file}")
                continue

            # 找出问题和答案列
            question_col = None
            answer_col = None

            # 查找问题列
            for col in df.columns:
                if str(col).lower() in ['ask', 'question', 'title']:
                    question_col = col
                    break
            if question_col is None:
                question_col = df.columns[0]  # 默认第一列

            # 查找答案列
            for col in df.columns:
                if str(col).lower() in ['answer', 'Answer']:
                    answer_col = col
                    break
            if answer_col is None and len(df.columns) > 1:
                answer_col = df.columns[1]  # 默认第二列

            # 构建文档
            for _, row in df.iterrows():
                question = str(row[question_col]) if pd.notna(row[question_col]) else ""
                answer = str(row[answer_col]) if answer_col and pd.notna(row[answer_col]) else ""

                if question and len(question) > 3:
                    doc = f"【科室】{department}\n【问题】{question[:500]}\n【回答】{answer[:1500]}"
                    documents.append(doc)

            logger.info(f"   从 {csv_file} 加载了 {len(df)} 条")

        except Exception as e:
            logger.error(f"处理 {csv_file} 失败: {e}")

    logger.info(f"📚 总共加载 {len(documents)} 条医疗知识")
    return documents


if __name__ == "__main__":
    # 测试加载
    docs = load_medical_data()
    print(f"\n共加载 {len(docs)} 条知识")
    if docs:
        print("\n示例:")
        print(docs[0][:300])