"""
HybridMind — CLI 入口模块
支持交互式 REPL 和单次执行两种模式。

用法:
    python -m src.main                  # 交互模式
    python -m src.main --input "..."    # 单次执行
    python -m src.main --add ./doc.pdf  # 添加文档到知识库
    python -m src.main --list           # 列出知识库文档
"""

import argparse
import sys
from pathlib import Path

# 确保 console 支持 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 确保 src 目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import HYBRIDMIND_VERSION, PROJECT_NAME
from src.agent import HybridMindAgent
from src.knowledge_base import HybridKnowledgeBase
from src.utils.logger import setup_logger, logger


def print_banner() -> None:
    """打印启动横幅。"""
    print(f"""
╔══════════════════════════════════════════╗
║  🧠  {PROJECT_NAME} v{HYBRIDMIND_VERSION}                     ║
║  "会思考的多模态知识库 & 自主 Agent 工作台"  ║
╚══════════════════════════════════════════╝
""")
    print("命令: 直接输入任务 | :add <文件> | :list | :help | :exit\n")


def interactive_mode(agent: HybridMindAgent, kb: HybridKnowledgeBase) -> None:
    """交互式 REPL 循环。"""
    print_banner()
    
    while True:
        try:
            user_input = input("🧠 >>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break
        
        if not user_input:
            continue
        
        # 特殊命令
        if user_input.lower() in (":exit", ":q", "exit", "quit"):
            print("👋 再见！")
            break
        
        if user_input.lower() in (":help", ":h", "help"):
            print("""
📖 HybridMind 使用帮助:
  直接输入任务 — 智能路由到对应技能
  :add <文件路径> — 添加文档到知识库
  :list           — 列出知识库中文档
  :search <查询>  — 语义搜索知识库
  :help           — 显示此帮助
  :exit           — 退出
""")
            continue
        
        if user_input.lower() == ":list":
            docs = kb.list_documents()
            if not docs:
                print("📭 知识库为空。使用 :add <文件> 添加文档。")
            else:
                print(f"📚 知识库文档 ({len(docs)} 个):")
                for i, doc in enumerate(docs, 1):
                    print(f"  {i}. {doc['filename']} [{doc['chunks']} 块] — {doc['source']}")
            continue
        
        if user_input.startswith(":add "):
            file_path = user_input[5:].strip().strip('"').strip("'")
            try:
                doc_id = kb.add_document(file_path)
                if doc_id:
                    print(f"✅ 文档已添加 (ID: {doc_id}): {file_path}")
                else:
                    print(f"⚠️ 文件无有效文本内容: {file_path}")
            except Exception as e:
                print(f"❌ 添加失败: {e}")
            continue
        
        if user_input.startswith(":search "):
            query = user_input[8:].strip()
            result = kb.query(query, n_results=5)
            if not result["documents"]:
                print("🔍 未找到匹配结果。")
            else:
                print(f"🔍 搜索 '{query[:40]}...' 的结果:")
                for i, doc in enumerate(result["documents"], 1):
                    source = result["metadatas"][i-1].get("source", "unknown")
                    print(f"\n  [{i}] 来源: {source}")
                    print(f"  {doc[:200]}...")
            continue
        
        # 正常任务处理
        result = agent.process(user_input)
        
        # 输出结果
        intent_label = {"code": "💻", "doc": "📚", "multimodal": "🖼️", "unknown": "🤔"}
        icon = intent_label.get(result["intent"], "🤔")
        
        print(f"\n{icon} [{result['intent'].upper()}] ", end="")
        if result["retries"] > 0:
            print(f"(经 {result['retries']} 次自愈重试)")
        else:
            print()
        
        print(result["result"])
        print()


def single_run(agent: HybridMindAgent, user_input: str) -> None:
    """单次执行模式。"""
    logger.info(f"单次执行 | 输入: {user_input[:80]}...")
    result = agent.process(user_input)
    
    print(f"[{result['intent'].upper()}] ", end="")
    if result["retries"] > 0:
        print(f"(经 {result['retries']} 次自愈重试)")
    else:
        print()
    print(result["result"])
    
    if not result["success"]:
        sys.exit(1)


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description=f"{PROJECT_NAME} v{HYBRIDMIND_VERSION} — 多模态知识库 & 自主 Agent 工作台",
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="单次执行模式，直接处理输入文本",
    )
    parser.add_argument(
        "--add",
        type=str,
        help="添加文档到知识库（支持 txt/md/pdf）",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出知识库中所有文档",
    )
    parser.add_argument(
        "--search", "-s",
        type=str,
        help="语义搜索知识库",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"{PROJECT_NAME} v{HYBRIDMIND_VERSION}",
    )
    
    args = parser.parse_args()
    
    # 初始化
    setup_logger(log_dir=PROJECT_ROOT / "logs")
    kb = HybridKnowledgeBase()
    agent = HybridMindAgent(kb=kb)
    
    # --add 模式
    if args.add:
        try:
            doc_id = kb.add_document(args.add)
            if doc_id:
                print(f"✅ 文档已添加 (ID: {doc_id}): {args.add}")
            else:
                print(f"⚠️ 文件无有效文本内容: {args.add}")
        except Exception as e:
            print(f"❌ 添加失败: {e}")
            sys.exit(1)
        return
    
    # --list 模式
    if args.list:
        docs = kb.list_documents()
        if not docs:
            print("📭 知识库为空。")
        else:
            print(f"📚 知识库文档 ({len(docs)} 个):")
            for i, doc in enumerate(docs, 1):
                print(f"  {i}. {doc['filename']} [{doc['chunks']} 块]")
        return
    
    # --search 模式
    if args.search:
        result = kb.query(args.search, n_results=5)
        if not result["documents"]:
            print("🔍 未找到匹配结果。")
        else:
            print(f"🔍 搜索 '{args.search[:40]}' 的结果:")
            for i, doc in enumerate(result["documents"], 1):
                source = result["metadatas"][i-1].get("source", "unknown")
                print(f"\n  [{i}] 来源: {source}")
                print(f"  {doc[:200]}...")
        return
    
    # 单次执行模式
    if args.input:
        single_run(agent, args.input)
        return
    
    # 默认：交互模式
    interactive_mode(agent, kb)


if __name__ == "__main__":
    main()
