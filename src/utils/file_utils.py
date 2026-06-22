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
