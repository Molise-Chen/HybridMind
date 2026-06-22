"""
HybridMind — 全局配置模块
=======================
定义项目版本、路径常量及运行时参数。
所有路径可通过环境变量覆盖，默认使用相对路径。
"""

import os
from pathlib import Path

# ---- 版本信息 ----
HYBRIDMIND_VERSION = "0.1.0"
PROJECT_NAME = "HybridMind"
PROJECT_DESCRIPTION = "会思考的多模态知识库 & 自主 Agent 工作台"

# ---- 路径常量 ----
# 项目根目录（src/config.py 的上两级）
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# 数据存储目录
DATA_DIR: Path = Path(
    os.getenv("HYBRIDMIND_DATA_DIR", PROJECT_ROOT / "data")
)

# ChromaDB 向量库持久化路径
CHROMA_PERSIST_DIR: Path = Path(
    os.getenv("HYBRIDMIND_CHROMA_DIR", DATA_DIR / "chroma_db")
)

# 日志目录
LOG_DIR: Path = Path(
    os.getenv("HYBRIDMIND_LOG_DIR", PROJECT_ROOT / "logs")
)

# Skills 目录（动态技能热加载）
SKILLS_DIR: Path = Path(
    os.getenv("HYBRIDMIND_SKILLS_DIR", Path(__file__).resolve().parent / "skills")
)

# ---- 运行时参数 ----
LOG_LEVEL: str = os.getenv("HYBRIDMIND_LOG_LEVEL", "INFO")

# Embedding 模型名称（sentence-transformers）
EMBEDDING_MODEL: str = os.getenv(
    "HYBRIDMIND_EMBEDDING_MODEL", "all-MiniLM-L6-v2"
)

# ChromaDB 集合名称
CHROMA_COLLECTION: str = os.getenv(
    "HYBRIDMIND_CHROMA_COLLECTION", "hybridmind_docs"
)

# LLM 配置（可插拔后端）
LLM_BACKEND: str = os.getenv("HYBRIDMIND_LLM_BACKEND", "openai")  # openai | ollama
LLM_MODEL: str = os.getenv("HYBRIDMIND_LLM_MODEL", "gpt-4o-mini")
LLM_API_KEY: str = os.getenv("HYBRIDMIND_LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
LLM_BASE_URL: str = os.getenv("HYBRIDMIND_LLM_BASE_URL", "https://api.openai.com/v1")

# 自愈闭环重试次数
MAX_RETRY: int = int(os.getenv("HYBRIDMIND_MAX_RETRY", "3"))

# ---- 初始化 ----
def ensure_dirs() -> None:
    """确保必要的目录存在。"""
    for d in (DATA_DIR, CHROMA_PERSIST_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


# 模块加载时自动创建目录
ensure_dirs()
