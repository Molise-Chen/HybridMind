"""
HybridMind — Agent 调度核心 + 自愈闭环
整合 Router、Skills、KnowledgeBase，实现完整的意图 → 执行 → 验证 → 修复流程。
"""

from pathlib import Path
from typing import Optional

from src.config import MAX_RETRY, LLM_BACKEND, LLM_MODEL, LLM_API_KEY, LLM_BASE_URL, FILE_SEARCH_TIMEOUT
from src.router import IntentRouter, Intent
from src.knowledge_base import HybridKnowledgeBase
from src.skills.code_skill import CodeSkill
from src.skills.doc_skill import DocSkill
from src.skills.multimodal_skill import MultimodalSkill
from src.utils.logger import logger
from src.utils.file_utils import GlobalFileFinder


class HybridMindAgent:
    """
    HybridMind 自主 Agent 核心。
    
    工作流:
    1. IntentRouter 分类用户意图
    2. 调度对应 Skill 执行
    3. self_verify 验证结果
    4. 如果失败 → auto_repair 自动修复 → 重试（最多 MAX_RETRY 次）
    """
    
    def __init__(
        self,
        kb: Optional[HybridKnowledgeBase] = None,
        router: Optional[IntentRouter] = None,
    ):
        self.kb = kb or HybridKnowledgeBase()
        self.router = router or IntentRouter()
        self.code_skill = CodeSkill()
        self.doc_skill = DocSkill(kb=self.kb)
        self.multimodal_skill = MultimodalSkill()
        
        self.retry_count = 0
        
        logger.info("HybridMindAgent initialized")
    
    def process(self, user_input: str) -> dict:
        """
        主处理入口。
        
        Args:
            user_input: 用户输入文本
        
        Returns:
            {
                "intent": str,
                "result": str,
                "success": bool,
                "retries": int,
                "error": str | None,
            }
        """
        self.retry_count = 0
        
        # Step 1: 意图路由
        route_info = self.router.route(user_input)
        intent = route_info["intent"]
        intent_name = route_info["intent_name"]
        
        # Step 2: 调度执行
        result = self._dispatch(intent, user_input)
        
        # Step 3: 自愈闭环（失败重试）
        while not self.self_verify(result) and self.retry_count < MAX_RETRY:
            self.retry_count += 1
            logger.warning(f"[AutoRepair] Retry {self.retry_count}/{MAX_RETRY}...")
            result = self.auto_repair(result, intent, user_input)
        
        success = self.self_verify(result)
        
        return {
            "intent": intent_name,
            "result": result.get("output", ""),
            "success": success,
            "retries": self.retry_count,
            "error": result.get("error"),
        }
    
    def _dispatch(self, intent: Intent, user_input: str) -> dict:
        """根据意图分发到对应 Skill。"""
        try:
            if intent == Intent.CODE:
                code = self.code_skill.generate_code(user_input)
                valid, err = self.code_skill.check_syntax(code)
                if not valid:
                    return {"output": code, "error": err, "code": code}
                run_ok, run_out = self.code_skill.run_tests(code)
                output = f"```python\n{code}```\n\n{'[OK] 执行成功:' if run_ok else '[FAIL] 执行失败:'}\n{run_out}"
                return {"output": output, "error": None if run_ok else run_out, "code": code}
            
            elif intent == Intent.DOC:
                answer = self.doc_skill.answer_from_docs(user_input)
                return {"output": answer, "error": None}
            
            elif intent == Intent.MULTIMODAL:
                # 尝试从输入中提取文件路径
                file_path = self._extract_file_path(user_input)
                if file_path:
                    # 如果本地路径不存在，启动全盘搜索
                    resolved = str(file_path)
                    if not Path(resolved).exists():
                        logger.info(f"本地未找到 {resolved}，启动全盘搜索...")
                        found = GlobalFileFinder.find(
                            user_input,
                            timeout=FILE_SEARCH_TIMEOUT,
                        )
                        if found:
                            resolved = str(found)
                            logger.info(f"全盘搜索找到: {resolved}")
                        else:
                            return {
                                "output": (
                                    f"❌ 文件未找到: {file_path}\n"
                                    f"已搜索范围：当前目录 → 桌面/文档/下载 → 全盘\n"
                                    f"请确认文件名是否正确，或提供完整路径。"
                                ),
                                "error": "FileNotFoundError",
                            }
                    desc = self.multimodal_skill.describe_content(resolved)
                    return {"output": desc, "error": None}
                else:
                    return {"output": "请指定要解析的文件路径。例如: 解析 ./docs/demo.pdf", "error": None}
            
            else:  # UNKNOWN
                return {
                    "output": (
                        f"[?] 未能明确识别你的意图。我可以帮你:\n"
                        f"  [CODE] 写代码 — 例如 '帮我写一个排序函数'\n"
                        f"  [DOC] 查文档 — 例如 '搜索闭包的知识'\n"
                        f"  [FILE] 解析文件 — 例如 '读取 ./docs/report.pdf'"
                    ),
                    "error": None,
                }
        
        except Exception as e:
            logger.error(f"调度执行异常: {e}")
            return {"output": f"执行异常: {e}", "error": str(e)}
    
    def self_verify(self, result: dict) -> bool:
        """
        自我验证：检查结果是否有效。
        
        验证规则:
        - output 不为空
        - 无致命 error
        - 结果长度合理
        """
        if not result:
            return False
        output = result.get("output", "")
        error = result.get("error")
        
        # 有致命错误
        if error and "IndentationError" not in error and "SyntaxError" not in error:
            return False
        
        # 输出为空
        if not output or not output.strip():
            return False
        
        # 输出太短（可能是占位符）
        if len(output.strip()) < 5:
            return False
        
        return True
    
    def auto_repair(self, result: dict, intent: Intent, user_input: str) -> dict:
        """
        自动修复：根据错误类型尝试修复。
        """
        error_info = result.get("error", "")
        
        if intent == Intent.CODE and "code" in result:
            # 尝试用 CodeSkill.lint_fix 修复
            fixed_code = self.code_skill.lint_fix(result["code"], error_info)
            valid, err = self.code_skill.check_syntax(fixed_code)
            if not valid:
                return {"output": fixed_code, "error": err, "code": fixed_code}
            run_ok, run_out = self.code_skill.run_tests(fixed_code)
            return {
                "output": f"```python\n{fixed_code}```\n\n[AutoRepair] 修复后:\n{'[OK] 成功:' if run_ok else '[FAIL] 仍然失败:'}\n{run_out}",
                "error": None if run_ok else run_out,
                "code": fixed_code,
            }
        
        # 其他意图的修复策略：重新执行一次（幂等重试）
        return self._dispatch(intent, user_input)
    
    @staticmethod
    def _extract_file_path(user_input: str) -> Optional[str]:
        """从用户输入中提取文件路径。"""
        import re
        # 匹配常见路径模式
        patterns = [
            r'(?:文件|路径|path)[:：\s]*["\']?([^\s"\']+\.\w{2,5})["\']?',
            r'["\']?(\S+\.(?:png|jpg|jpeg|gif|bmp|pdf|md|txt|markdown))["\']?',
            r'(?:解析|读取|查看)[:：\s]*["\']?([^\s"\']+)["\']?',
        ]
        for pattern in patterns:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
