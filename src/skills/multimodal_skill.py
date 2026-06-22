"""
HybridMind — 多模态解析技能模块
负责图片、PDF、Markdown 等富媒体文件的解析与内容提取。
"""

from pathlib import Path

from src.utils.file_utils import read_image, read_pdf, read_markdown
from src.utils.logger import logger


class MultimodalSkill:
    """
    多模态解析技能。
    
    当意图路由判定为 "multimodal" 时激活。
    支持图片 OCR、PDF 文本提取、Markdown 渲染。
    """
    
    SKILL_NAME = "multimodal"
    
    def parse_image(self, path: str | Path) -> dict:
        """
        解析图片文件，提取元数据和 OCR 文本。
        
        Returns:
            {"path": str, "format": str, "size": (w,h), "ocr_text": str|None}
        """
        logger.info(f"[MultimodalSkill] 解析图片: {path}")
        return read_image(path)
    
    def parse_pdf(self, path: str | Path) -> dict:
        """
        解析 PDF 文件，提取全部文本内容。
        
        Returns:
            {"path": str, "pages": int, "text": str}
        """
        logger.info(f"[MultimodalSkill] 解析 PDF: {path}")
        return read_pdf(path)
    
    def describe_content(self, path: str | Path) -> str:
        """
        根据文件类型自动选择解析策略，返回人类可读的内容描述。
        
        支持: png / jpg / jpeg / gif / bmp / pdf / md / txt
        """
        path = Path(path)
        if not path.exists():
            return f"❌ 文件不存在: {path}"
        
        suffix = path.suffix.lower()
        
        if suffix in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
            info = self.parse_image(path)
            ocr_info = f"\n   - OCR 文本: {info['ocr_text'][:200]}..." if info["ocr_text"] else "\n   - OCR: 未检测到文字"
            return (
                f"🖼️ 图片内容描述:\n"
                f"   - 文件: {info['path']}\n"
                f"   - 格式: {info['format']}\n"
                f"   - 尺寸: {info['size'][0]}×{info['size'][1]}px\n"
                f"   - 色彩模式: {info['mode']}"
                f"{ocr_info}"
            )
        
        elif suffix == ".pdf":
            info = self.parse_pdf(path)
            preview = info["text"][:300].replace("\n", " ")
            return (
                f"📕 PDF 内容描述:\n"
                f"   - 文件: {info['path']}\n"
                f"   - 页数: {info['pages']}\n"
                f"   - 内容预览: {preview}..."
            )
        
        elif suffix in (".md", ".markdown"):
            text = read_markdown(path)
            preview = text[:300].replace("\n", " ")
            return (
                f"📝 Markdown 内容描述:\n"
                f"   - 文件: {path}\n"
                f"   - 字符数: {len(text)}\n"
                f"   - 预览: {preview}..."
            )
        
        else:
            try:
                text = path.read_text(encoding="utf-8")
                preview = text[:300]
                return (
                    f"📄 文本文件内容描述:\n"
                    f"   - 文件: {path}\n"
                    f"   - 字符数: {len(text)}\n"
                    f"   - 预览: {preview}..."
                )
            except Exception:
                return f"⚠️ 不支持的文件类型: {suffix}"
