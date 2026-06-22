"""
HybridMind — 文件工具模块
支持文本、图片 (Pillow + OCR)、PDF、Markdown 的读取与解析。
"""

from pathlib import Path
from typing import Optional

from src.utils.logger import logger


def read_text_file(path: str | Path) -> str:
    """读取纯文本文件，自动检测 UTF-8 / GBK 编码。"""
    path = Path(path)
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"无法解码文件: {path}")


def read_markdown(path: str | Path) -> str:
    """读取 Markdown 文件（等同于 read_text_file）。"""
    return read_text_file(path)


def read_image(path: str | Path) -> dict:
    """
    读取图片文件，返回结构化信息。
    返回格式: {"path": str, "format": str, "size": (w, h), "mode": str, "ocr_text": str | None}
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {path}")
    
    try:
        from PIL import Image
    except ImportError:
        raise ImportError("Pillow 未安装，请运行: pip install pillow")
    
    img = Image.open(path)
    info = {
        "path": str(path),
        "format": img.format or path.suffix.upper().lstrip("."),
        "size": img.size,          # (width, height)
        "mode": img.mode,          # RGB / RGBA / L ...
        "ocr_text": None,
    }
    
    # 尝试 OCR
    try:
        import pytesseract
        ocr_text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        info["ocr_text"] = ocr_text.strip() if ocr_text.strip() else None
    except ImportError:
        logger.debug("pytesseract 未安装，跳过 OCR")
    except Exception as e:
        logger.warning(f"OCR 失败: {e}")
    
    return info


def read_pdf(path: str | Path) -> dict:
    """
    读取 PDF 文件，提取文本内容。
    返回格式: {"path": str, "pages": int, "text": str}
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF 不存在: {path}")
    
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise ImportError("PyPDF2 未安装，请运行: pip install pypdf2")
    
    reader = PdfReader(str(path))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)
    
    return {
        "path": str(path),
        "pages": len(reader.pages),
        "text": "\n\n".join(pages_text),
    }


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    将长文本切分为有重叠的块，用于 embedding。
    
    Args:
        text: 输入文本
        chunk_size: 每块最大字符数
        overlap: 块之间重叠字符数
    
    Returns:
        文本块列表
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


# ══════════════════════════════════════════════════════
#  GlobalFileFinder — 全盘文件搜索
# ══════════════════════════════════════════════════════

import os
import time
import re
import string
from typing import Optional


class GlobalFileFinder:
    """
    全盘文件查找器。
    
    三层搜索策略：
    1. 当前工作目录 + 项目 data/ 目录
    2. 用户常见目录（桌面、文档、下载）
    3. 全盘递归搜索（所有盘符，限时）
    
    支持缓存和模糊匹配。
    """
    
    # 搜索结果缓存 {filename_lower: full_path}
    _cache: dict[str, str] = {}
    
    # 用户文件夹黑名单（跳过系统目录）
    SKIP_DIRS: set = {
        "Windows", "Program Files", "Program Files (x86)", "ProgramData",
        "$Recycle.Bin", "System Volume Information", "node_modules",
        "__pycache__", ".git", ".reasonix", "venv", ".venv",
        "AppData", "Microsoft", "MSBuild", "WindowsApps",
    }
    
    # 用户常见目录
    COMMON_ROOTS: list[str] = []
    
    @classmethod
    def _init_common_roots(cls) -> None:
        """初始化常见搜索根目录。"""
        if cls.COMMON_ROOTS:
            return
        home = os.path.expanduser("~")
        candidates = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "Documents"),
            os.path.join(home, "Downloads"),
            os.path.join(home, "OneDrive"),
            os.path.join(home, "Pictures"),
            os.path.join(home, "Desktop", "考研"),
            os.path.join(home, "Desktop", "学习"),
            os.path.join(home, "Documents", "考研"),
            "D:\\",
        ]
        for c in candidates:
            if os.path.isdir(c):
                cls.COMMON_ROOTS.append(c)
    
    @classmethod
    def _clean_filename(cls, raw_input: str) -> str:
        """
        从用户输入中提取纯文件名。
        去掉"读取"、"查看"、"解析"等动词前缀和路径符号。
        """
        # 去掉常见的动词前缀
        cleaned = re.sub(
            r'^(读取|查看|解析|打开|看|读|识别|分析|搜|搜索|找)\s*',
            '',
            raw_input.strip(),
        )
        # 去掉引号和 ./ 等
        cleaned = cleaned.strip('"\'`').lstrip('./')
        # 去掉路径部分，只保留文件名
        if '/' in cleaned or '\\' in cleaned:
            cleaned = cleaned.replace('/', '\\').split('\\')[-1]
        return cleaned.strip()
    
    @classmethod
    def find(
        cls,
        filename: str,
        timeout: float = 15.0,
        use_cache: bool = True,
    ) -> Optional[Path]:
        """
        三层搜索查找文件。
        
        Args:
            filename: 用户输入的文件名（可以包含"读取"等前缀）
            timeout: 总搜索超时秒数
            use_cache: 是否使用缓存
        
        Returns:
            文件的绝对 Path，未找到返回 None
        """
        cleaned = cls._clean_filename(filename)
        cleaned_lower = cleaned.lower().strip()
        
        # 如果已经是完整路径且存在，直接返回
        if os.path.exists(filename):
            return Path(filename).resolve()
        if os.path.exists(cleaned):
            return Path(cleaned).resolve()
        
        # 检查缓存
        if use_cache and cleaned_lower in cls._cache:
            cached = cls._cache[cleaned_lower]
            if os.path.exists(cached):
                logger.info(f"[FileFinder] 缓存命中: {cached}")
                return Path(cached)
            else:
                del cls._cache[cleaned_lower]
        
        start_time = time.time()
        logger.info(f"[FileFinder] 搜索: '{cleaned}'")
        
        # ---- 第一层：CWD + data/ ----
        layer1_dirs = [
            Path.cwd(),
            Path.cwd() / "data",
        ]
        for d in layer1_dirs:
            result = cls._search_dir(d, cleaned_lower, start_time, timeout)
            if result:
                return result
        
        # ---- 第二层：用户常见目录 ----
        cls._init_common_roots()
        for d in cls.COMMON_ROOTS:
            if time.time() - start_time > timeout:
                break
            result = cls._search_dir(Path(d), cleaned_lower, start_time, timeout, depth=3)
            if result:
                return result
        
        # ---- 第三层：全盘递归搜索 ----
        drives = cls._get_available_drives()
        for drive in drives:
            if time.time() - start_time > timeout:
                logger.warning(f"[FileFinder] 搜索超时 ({timeout}s)")
                break
            try:
                result = cls._search_dir(
                    Path(drive), cleaned_lower, start_time, timeout, depth=5
                )
                if result:
                    return result
            except PermissionError:
                continue
        
        logger.warning(f"[FileFinder] 未找到: '{cleaned}'")
        return None
    
    @classmethod
    def _search_dir(
        cls,
        root: Path,
        target: str,
        start_time: float,
        timeout: float,
        depth: int = 5,
    ) -> Optional[Path]:
        """在指定目录中递归搜索文件。"""
        if time.time() - start_time > timeout:
            return None
        if depth <= 0:
            return None
        
        try:
            for entry in root.iterdir():
                if time.time() - start_time > timeout:
                    return None
                
                try:
                    if entry.is_dir():
                        # 跳过系统目录
                        if entry.name in cls.SKIP_DIRS:
                            continue
                        if depth > 1:
                            result = cls._search_dir(
                                entry, target, start_time, timeout, depth - 1
                            )
                            if result:
                                return result
                    elif entry.is_file():
                        name_lower = entry.name.lower()
                        # 精确匹配或子串匹配
                        if target == name_lower or target in name_lower:
                            full_path = entry.resolve()
                            cls._cache[target] = str(full_path)
                            logger.info(f"[FileFinder] 找到: {full_path}")
                            return full_path
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass
        
        return None
    
    @staticmethod
    def _get_available_drives() -> list[str]:
        """获取所有可用盘符。"""
        drives = []
        for letter in string.ascii_uppercase:
            path = f"{letter}:\\"
            if os.path.exists(path):
                drives.append(path)
        # Windows 用户常用盘优先
        priority = ["D:\\", "E:\\", "F:\\"]
        for p in priority:
            if p in drives:
                drives.remove(p)
                drives.insert(0, p)
        return drives
    
    @classmethod
    def clear_cache(cls) -> None:
        """清空搜索缓存。"""
        cls._cache.clear()
        logger.info("[FileFinder] 缓存已清空")
