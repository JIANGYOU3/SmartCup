"""工具函数"""

import re
import time
import hashlib
import random
from typing import Any


def clean_text(text: str) -> str:
    """清理文本"""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = text.replace('​', '').replace('‎', '').replace('‏', '')
    text = re.sub(r'&#?\w+;', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_number(text: str) -> int:
    """从字符串中提取数字"""
    m = re.search(r'(\d[\d,]*\d|\d)', str(text).replace(',', '').replace('，', ''))
    return int(m.group(1).replace(',', '')) if m else 0


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
