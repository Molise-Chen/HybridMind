"""
HybridMind — 文档检索技能模块
负责从本地知识库中语义检索并回答问题。
"""

from src.knowledge_base import HybridKnowledgeBase
from src.utils.logger import logger


class DocSkill:
    """
    文档检索技能。
    
    当意图路由判定为 "doc" 时激活。
    与 HybridKnowledgeBase 协作，实现文档检索、摘要和问答。
    """
    
    SKILL_NAME = "doc"
    
    def __init__(self, kb: HybridKnowledgeBase | None = None):
        """
        Args:
            kb: 知识库实例（可选，惰性初始化）
        """
        self._kb = kb
    
    @property
    def kb(self) -> HybridKnowledgeBase:
        if self._kb is None:
            self._kb = HybridKnowledgeBase()
        return self._kb
    
    def search_docs(self, query: str, top_k: int = 5) -> list[dict]:
        """
        语义搜索知识库中的文档。
        
        Returns:
            结果列表 [{"content": str, "source": str, "relevance": float}, ...]
        """
        logger.info(f"[DocSkill] 搜索文档 | 查询: {query[:60]}...")
        result = self.kb.query(query, n_results=top_k)
        
        docs = []
        for i, doc in enumerate(result["documents"]):
            docs.append({
                "content": doc,
                "source": result["metadatas"][i].get("source", "unknown") if result["metadatas"] else "unknown",
                "relevance": 1.0 - result["distances"][i] if result["distances"] else 1.0,
            })
        return docs
    
    def answer_from_docs(self, question: str) -> str:
        """
        从知识库中检索相关文档并构建答案。
        """
        docs = self.search_docs(question, top_k=3)
        if not docs:
            return "未找到与问题相关的文档。知识库可能为空，请先使用 --add 命令添加文档。"
        
        # 拼接检索到的文档内容
        context = "\n\n---\n\n".join(
            f"[来源: {d['source']}]\n{d['content'][:500]}" for d in docs
        )
        
        # 构建回答（当前为模板化，未来接入 LLM）
        answer = (
            f"📚 从知识库中检索到 {len(docs)} 条相关内容:\n\n"
            f"{context}\n\n"
            f"💡 提示: 以上为语义检索结果，可接入 LLM 进行深度总结。"
        )
        return answer
    
    def summarize_doc(self, file_path: str) -> str:
        """
        对单个文档进行摘要。
        
        Args:
            file_path: 文档路径
        
        Returns:
            摘要文本
        """
        from src.utils.file_utils import read_text_file, read_pdf
        
        path = str(file_path)
        if path.lower().endswith(".pdf"):
            result = read_pdf(path)
            text = result["text"]
        else:
            text = read_text_file(path)
        
        # 简单摘要：取前 300 字 + 统计信息
        preview = text[:300].replace("\n", " ")
        char_count = len(text)
        word_count = len(text.split())
        
        summary = (
            f"📄 文档摘要: {file_path}\n"
            f"   - 字符数: {char_count}\n"
            f"   - 词数 (估): {word_count}\n"
            f"   - 预览: {preview}..."
        )
        return summary
