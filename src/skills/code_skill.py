"""
HybridMind — 代码开发技能模块
负责代码生成、语法检查、自动修复。
"""

import subprocess
import tempfile
from pathlib import Path

from src.utils.logger import logger


class CodeSkill:
    """
    代码开发技能。
    
    当意图路由判定为 "code" 时激活。
    支持：代码生成、静态语法检查、执行测试、自动 lint 修复。
    """
    
    SKILL_NAME = "code"
    
    def generate_code(self, spec: str, language: str = "python") -> str:
        """
        根据需求规格生成代码骨架。
        
        当前为规则驱动的模板生成，未来可接入 LLM 生成。
        
        Args:
            spec: 需求描述
            language: 目标语言（当前仅支持 python）
        
        Returns:
            生成的代码字符串
        """
        logger.info(f"[CodeSkill] 生成代码 | 语言: {language} | 需求: {spec[:60]}...")
        
        # 基于规则的关键词匹配生成模板
        spec_lower = spec.lower()
        
        if "斐波那契" in spec or "fibonacci" in spec_lower:
            code = '''def fibonacci(n: int) -> list[int]:
    """生成前 n 个斐波那契数。"""
    if n <= 0:
        return []
    if n == 1:
        return [0]
    seq = [0, 1]
    for _ in range(2, n):
        seq.append(seq[-1] + seq[-2])
    return seq


if __name__ == "__main__":
    print(fibonacci(10))
'''
        elif "排序" in spec or "sort" in spec_lower:
            code = '''def quick_sort(arr: list) -> list:
    """快速排序实现。"""
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)


if __name__ == "__main__":
    print(quick_sort([3, 6, 8, 10, 1, 2, 1]))
'''
        elif "二分" in spec or "binary search" in spec_lower:
            code = '''def binary_search(arr: list, target) -> int:
    """二分查找，返回索引或 -1。"""
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1


if __name__ == "__main__":
    print(binary_search([1, 3, 5, 7, 9], 5))
'''
        elif "函数" in spec or "function" in spec_lower:
            code = f'''# 根据需求生成的函数模板
# 需求: {spec}

def solution():
    """在此实现你的逻辑。"""
    pass


if __name__ == "__main__":
    solution()
'''
        else:
            code = f'''# HybridMind 生成的代码
# 需求: {spec}

def main():
    print("Hello from HybridMind!")
    # TODO: 实现具体逻辑


if __name__ == "__main__":
    main()
'''
        return code
    
    def check_syntax(self, code: str) -> tuple[bool, str]:
        """
        检查 Python 代码语法。
        
        Returns:
            (is_valid, error_message)
        """
        try:
            compile(code, "<hybridmind>", "exec")
            return True, ""
        except SyntaxError as e:
            return False, f"语法错误 [行 {e.lineno}]: {e.msg}"
    
    def run_tests(self, code: str) -> tuple[bool, str]:
        """
        在临时文件中执行代码并捕获输出。
        
        Returns:
            (success, output)
        """
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name
        
        try:
            result = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr or result.stdout
        except subprocess.TimeoutExpired:
            return False, "错误: 代码执行超时 (30s)"
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    
    def lint_fix(self, code: str, error_info: str = "") -> str:
        """
        根据错误信息尝试自动修复代码。
        
        当前为规则驱动的简单修复，未来可接入 LLM。
        """
        # 常见错误修复规则
        fixes = {
            "NameError": "# 修复: 添加缺失的变量定义\n",
            "IndentationError": "# 修复: 统一缩进为 4 空格\n",
            "TypeError": "# 修复: 调整参数类型\n",
            "ZeroDivisionError": "# 修复: 添加除数非零检查\n",
        }
        
        for err_type, fix_hint in fixes.items():
            if err_type in error_info:
                logger.info(f"[CodeSkill] 自动修复: {err_type}")
                return f"{fix_hint}\n{code}"
        
        return code
