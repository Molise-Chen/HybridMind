"""
HybridMind — 意图路由模块
基于规则 + 关键词匹配，将用户输入分类为 code / doc / multimodal / unknown。
"""

import re
from enum import Enum, auto

from src.utils.logger import logger


class Intent(Enum):
    """用户意图枚举。"""
    CODE = auto()         # 代码开发
    DOC = auto()          # 文档检索
    MULTIMODAL = auto()   # 多模态解析
    UNKNOWN = auto()      # 无法判断


# ---- 意图关键词规则 ----
CODE_KEYWORDS: list[str] = [
    r"写(一个|个)?(代码|程序|脚本|函数|类|模块)",
    r"(生成|创建|实现|编写|编|开发|构建)(一个|个)?(代码|程序|脚本|函数)",
    r"(debug|调试|修复|修|改|重构)(这个|一下|代码|bug|错误)",
    r"(fibonacci|斐波那契|排序|sort|二分|binary.search|冒泡|快排)",
    r"(算法|数据结构|设计模式)",
]

DOC_KEYWORDS: list[str] = [
    r"(搜索|查找|检索|查询|找|搜|搜索一下|查一下)(关于|一下|一个)?",
    r"(什么是|什么叫|什么叫作|解释一下|解释|讲讲)(.*?)(概念|意思|含义|原理|机制)",
    r"(介绍|说明|概述|总结|摘要)(一下)?",
    r"(闭包|装饰器|生成器|协程|异步|多线程|多进程|元类|上下文管理器)",
    r"(知识点|原理|机制|特性|用法|语法|api|教程|文档)",
    r"(文档|知识库|资料|参考).{0,5}(搜索|检索|查询|里|中)",
]

MULTIMODAL_KEYWORDS: list[str] = [
    r"(看|查看|读取|解析|识别|分析|读)\s*(一下|这个|这张|一幅|一张|图片|照片|图像|pdf|文档|文件|./|\\.)",
    r"(图片|照片|图像|截图|pdf|文件).{0,10}(里|里面|中|上)(有|是|写)(什么|啥|哪些)内容",
    r"(ocr|识别|提取)(文字|文本|内容)",
    r"\.(png|jpg|jpeg|gif|bmp|pdf|md|markdown)\b",
]


class IntentRouter:
    """
    意图路由器。
    
    基于关键词正则匹配，将用户输入分为四类意图：
    - CODE: 代码开发
    - DOC: 文档检索
    - MULTIMODAL: 多模态解析
    - UNKNOWN: 兜底（走通用问答）
    """
    
    def __init__(self, use_llm: bool = False):
        """
        Args:
            use_llm: 是否使用 LLM 进行意图分类（默认用规则）
        """
        self.use_llm = use_llm
        # 预编译正则
        self._code_patterns = [re.compile(p, re.IGNORECASE) for p in CODE_KEYWORDS]
        self._doc_patterns = [re.compile(p, re.IGNORECASE) for p in DOC_KEYWORDS]
        self._multi_patterns = [re.compile(p, re.IGNORECASE) for p in MULTIMODAL_KEYWORDS]
    
    def classify_intent(self, user_input: str) -> Intent:
        """
        分类用户输入意图。
        
        Args:
            user_input: 用户输入文本
        
        Returns:
            Intent 枚举值
        """
        if not user_input or not user_input.strip():
            return Intent.UNKNOWN
        
        # 多模态检测优先（文件扩展名匹配更明确）
        for pattern in self._multi_patterns:
            if pattern.search(user_input):
                logger.info(f"[IntentRouter] 意图 → MULTIMODAL (匹配: {pattern.pattern[:40]})")
                return Intent.MULTIMODAL
        
        # 文档检测（"搜索/查找/什么是" 信号比语言名更强）
        for pattern in self._doc_patterns:
            if pattern.search(user_input):
                logger.info(f"[IntentRouter] 意图 → DOC (匹配: {pattern.pattern[:40]})")
                return Intent.DOC
        
        # 代码检测
        for pattern in self._code_patterns:
            if pattern.search(user_input):
                logger.info(f"[IntentRouter] 意图 → CODE (匹配: {pattern.pattern[:40]})")
                return Intent.CODE
        
        logger.info("[IntentRouter] 意图 → UNKNOWN（无明确规则匹配）")
        return Intent.UNKNOWN
    
    def route(self, user_input: str) -> dict:
        """
        路由入口：分类意图并返回调度指令。
        
        Returns:
            {"intent": Intent, "intent_name": str, "skill": str}
        """
        intent = self.classify_intent(user_input)
        
        intent_map = {
            Intent.CODE: "code",
            Intent.DOC: "doc",
            Intent.MULTIMODAL: "multimodal",
            Intent.UNKNOWN: "unknown",
        }
        
        return {
            "intent": intent,
            "intent_name": intent_map[intent],
            "skill": intent_map[intent],
        }
