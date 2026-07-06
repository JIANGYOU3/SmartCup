"""工具函数"""

import time
import hashlib
import random
from typing import Any

# 从公共模块 re-export，保持向后兼容
from source.common.text_utils import clean_text, extract_number  # noqa: F401


def random_delay(base: float = 1.0, jitter: float = 0.5):
    """随机延迟"""
    time.sleep(base + random.uniform(0, jitter))


def url_hash(url: str) -> str:
    """URL 的短哈希"""
    return hashlib.md5(url.encode()).hexdigest()[:10]


def retry(times: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < times - 1:
                        time.sleep(delay * (2 ** attempt))
            raise last_error
        return wrapper
    return decorator
