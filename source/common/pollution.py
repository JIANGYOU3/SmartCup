"""数据污染检测 —— 在 AI 调用前过滤明显无关/不当内容"""

import re
from typing import Optional

# 成人 / NSFW 内容关键词
NSFW_KEYWORDS = [
    "飞机杯", "成人用品", "TENGA", "自慰", "充气娃娃",
    "振动棒", "按摩棒",
]

# 与杯子不相关的 "杯"（体育奖杯等）
IRRELEVANT_CUP_KEYWORDS = [
    "世界杯", "欧洲杯", "亚洲杯", "美洲杯", "非洲杯",
    "冠军杯", "联赛杯", "足协杯", "联盟杯", "欧冠",
    "NBA", "CBA",
    "奖杯", "金杯", "银杯", "铜杯", "大力神杯",
    "德劳内杯", "圣杯",
]


def is_polluted(title: str = "", content: str = "", *, min_title_len: int = 3, min_content_len: int = 5) -> Optional[str]:
    """
    检测文本是否属于污染数据。
    返回 None 表示干净，返回字符串表示污染原因（可用于日志）。
    """
    full_text = f"{title} {content}"

    # 1. 空内容
    if len(title.strip()) < min_title_len and len(content.strip()) < min_content_len:
        return "空内容"

    # 2. NSFW
    for kw in NSFW_KEYWORDS:
        if kw in full_text:
            return f"NSFW-{kw}"

    # 3. 无关"杯"
    for kw in IRRELEVANT_CUP_KEYWORDS:
        if kw in full_text:
            return f"不相关-{kw}"

    # 4. 纯 URL / 乱码
    if re.match(r'^https?://', content.strip()) and len(content.strip()) < 50:
        return "纯链接"

    return None
