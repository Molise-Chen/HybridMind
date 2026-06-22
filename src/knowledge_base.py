"""
HybridMind — RAG 知识库模块
基于 ChromaDB + sentence-transformers 的本地向量知识库。
支持文档添加、语义检索、文档列表。
"""

import uuid
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION, EMBEDDING_MODEL
from src.utils.logger import logger
from src.utils.file_utils import read_text_file, read_pdf, read_markdown, chunk_text


class HybridKnowledgeBase:
    """
    本地向量知识库。
    
    使用 ChromaDB 作为向量存储，sentence-transformers 作为 embedding 引擎。
    支持 txt / md / pdf 文件的自动解析、分块、向量化和检索。
    """
    
    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        collection_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        self.persist_dir = Path(persist_dir or CHROMA_PERSIST_DIR)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name or CHROMA_COLLECTION
        self.embedding_model = embedding_model or EMBEDDING_MODEL
        self._offline_mode = False
        
        # 初始化 embedding 函数
        self.embedding_fn = self._init_embedding()
        
        try:
            # 初始化 ChromaDB 客户端（持久化模式）
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
            )
            logger.info(
                f"知识库已初始化 | 持久化目录: {self.persist_dir} | "
                f"集合: {self.collection_name} | 文档数: {self.collection.count()}"
            )
        except Exception as e:
            logger.warning(f"ChromaDB 初始化失败 ({e})，降级为离线文本模式")
            self._offline_mode = True
            self.client = None
            self.collection = None
            self._text_store: dict[str, dict] = {}  # {doc_id: {text, metadata}}
    
    def _init_embedding(self):
        """初始化 embedding 函数，带离线 fallback。"""
        import os
        
        # 关闭 SSL 验证以解决企业网络代理问题（可选）
        if os.getenv("HYBRIDMIND_NO_SSL_VERIFY"):
            os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"
            os.environ["CURL_CA_BUNDLE"] = ""
        
        try:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            # 优先尝试本地缓存，失败则从网络下载
            return SentenceTransformerEmbeddingFunction(model_name=self.embedding_model)
        except Exception as e:
            logger.warning(f"sentence-transformers 加载失败 ({e})，使用 ChromaDB 内置默认 embedding")
            # 使用 ChromaDB 内置的最小 embedding 函数
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            return DefaultEmbeddingFunction()
    
    def add_document(
        self,
        file_path: str | Path,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        解析文件并添加到知识库。
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 根据后缀解析文件
        suffix = file_path.suffix.lower()
        if suffix in (".txt", ".log", ".py", ".json", ".yaml", ".yml"):
            text = read_text_file(file_path)
        elif suffix == ".md":
            text = read_markdown(file_path)
        elif suffix == ".pdf":
            result = read_pdf(file_path)
            text = result["text"]
        else:
            text = read_text_file(file_path)
        
        if not text.strip():
            logger.warning(f"文件无有效文本内容: {file_path}")
            return ""
        
        # 分块
        chunks = chunk_text(text)
        if not chunks:
            return ""
        
        doc_id = str(uuid.uuid4())[:8]
        
        # 离线文本模式
        if self._offline_mode:
            self._text_store[doc_id] = {
                "text": "\n".join(chunks),
                "source": str(file_path),
                "filename": file_path.name,
            }
            logger.info(f"文档已添加(离线模式) | 文件: {file_path.name} | ID: {doc_id}")
            return doc_id
        
        # ChromaDB 模式
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "source": str(file_path),
                "filename": file_path.name,
                "chunk_index": i,
                "total_chunks": len(chunks),
                **(metadata or {}),
            }
            for i in range(len(chunks))
        ]
        
        try:
            self.collection.add(ids=ids, documents=chunks, metadatas=metadatas)
            logger.info(f"文档已添加 | 文件: {file_path.name} | 分块数: {len(chunks)} | ID: {doc_id}")
        except Exception as e:
            logger.warning(f"ChromaDB add 失败 ({e})，降级为离线模式")
            self._offline_mode = True
            self._text_store[doc_id] = {
                "text": "\n".join(chunks),
                "source": str(file_path),
                "filename": file_path.name,
            }
        
        return doc_id
    
    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> dict:
        """语义检索知识库。离线模式下使用关键词匹配。"""
        # 离线文本模式
        if self._offline_mode:
            results = []
            for doc_id, doc in self._text_store.items():
                text = doc["text"]
                # 简单关键词匹配评分
                score = sum(1 for word in query_text if word in text)
                if score > 0:
                    results.append({
                        "document": text[:500],
                        "metadata": {"source": doc["source"], "filename": doc["filename"]},
                        "distance": 1.0 / (1 + score),
                    })
            results.sort(key=lambda x: x["distance"])
            results = results[:n_results]
            return {
                "documents": [r["document"] for r in results],
                "metadatas": [r["metadata"] for r in results],
                "distances": [r["distance"] for r in results],
            }
        
        if self.collection.count() == 0:
            logger.warning("知识库为空，请先添加文档")
            return {"documents": [], "metadatas": [], "distances": []}
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=min(n_results, self.collection.count()),
                where=where,
            )
            logger.info(f"检索完成 | 查询: '{query_text[:50]}...' | 结果数: {len(results['documents'][0])}")
            return {
                "documents": results["documents"][0],
                "metadatas": results["metadatas"][0],
                "distances": results["distances"][0],
            }
        except Exception as e:
            logger.warning(f"ChromaDB query 失败 ({e})，降级为离线模式")
            self._offline_mode = True
            return self.query(query_text, n_results, where)
    
    def list_documents(self) -> list[dict]:
        """列出知识库中所有文档。"""
        if self._offline_mode:
            return [
                {"source": d["source"], "filename": d["filename"], "chunks": 1}
                for d in self._text_store.values()
            ]
        
        if self.collection.count() == 0:
            return []
        
        all_data = self.collection.get()
        sources: dict[str, dict] = {}
        for meta in all_data.get("metadatas", []):
            src = meta.get("source", "unknown")
            if src not in sources:
                sources[src] = {"source": src, "filename": meta.get("filename", ""), "chunks": 0}
            sources[src]["chunks"] += 1
        
        return list(sources.values())
    
    def delete_document(self, source: str) -> int:
        """按 source 路径删除文档的所有分块。"""
        if self._offline_mode:
            to_delete = [k for k, v in self._text_store.items() if v["source"] == source]
            for k in to_delete:
                del self._text_store[k]
            return len(to_delete)
        
        before = self.collection.count()
        self.collection.delete(where={"source": source})
        after = self.collection.count()
        deleted = before - after
        logger.info(f"文档已删除 | source: {source} | 移除分块: {deleted}")
        return deleted
