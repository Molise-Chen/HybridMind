"""
HybridMind — 日志工具模块
提供彩色控制台输出 + 文件日志轮转。
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False


def setup_logger(
    name: str = "HybridMind",
    level: str = "INFO",
    log_dir: Path | None = None,
) -> logging.Logger:
    """
    初始化日志器。
    
    Args:
        name: 日志器名称
        level: 日志等级 (DEBUG/INFO/WARNING/ERROR)
        log_dir: 日志文件目录（可选）
    
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # ---- 控制台 Handler（彩色） ----
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    
    if HAS_COLORLOG:
        fmt = colorlog.ColoredFormatter(
            "%(log_color)s[%(levelname)-7s] %(asctime)s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
    else:
        fmt = logging.Formatter(
            "[%(levelname)-7s] %(asctime)s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    console.setFormatter(fmt)
    logger.addHandler(console)
    
    # ---- 文件 Handler（轮转） ----
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "hybridmind.log",
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "[%(levelname)-7s] %(asctime)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)
    
    return logger


# 默认全局 logger
logger = setup_logger()
