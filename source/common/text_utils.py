"""文本处理工具"""

import re


def clean_text(text: str) -> str:
    """清理文本：去掉控制字符、零宽字符、多余空白、HTML 实体"""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    text = text.replace('​', '').replace('‎', '').replace('‏', '')
    text = re.sub(r'&#?\w+;', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_number(text: str) -> int:
    """从字符串中提取第一个数字，支持千位分隔符"""
    m = re.search(r'(\d[\d,]*\d|\d)', str(text).replace(',', '').replace('，', ''))
    return int(m.group(1).replace(',', '')) if m else 0


def make_content_preview(text: str, max_len: int = 200) -> str:
    """截取正文开头"""
    cleaned = clean_text(text)
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len] + "…"
