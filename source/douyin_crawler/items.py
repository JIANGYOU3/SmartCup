"""抖音数据模型"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DouyinVideo:
    """抖音视频"""

    url: str = ""
    aweme_id: str = ""
    video_type: str = ""              # 短视频 / 图文 / 直播
    desc: str = ""                     # 视频描述/标题
    content: str = ""                  # 视频文案（完整描述）
    author: str = ""                   # 作者昵称
    play_count: int = 0                # 播放数
    digg_count: int = 0                # 点赞数
    comment_count: int = 0             # 评论数
    share_count: int = 0               # 分享数
    publish_time: str = ""             # 发布时间
    duration: int = 0                  # 视频时长（秒）
    tags: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转为中文列名的字典，对齐知乎 13 字段格式"""
        return {
            "关键词": "",
            "视频类型": self.video_type,
            "播放数": self.play_count,
            "评论数": self.comment_count,
            "视频标题": self.desc,
            "视频文案": self.content,
            "作者昵称": self.author,
            "发布时间": self.publish_time,
            "点赞数": self.digg_count,
            "分享数": self.share_count,
            "视频时长": self.duration,
            "视频链接": self.url,
        }

    # 输出字段名（与 to_dict 保持一致）
    FIELDNAMES = [
        "关键词", "视频类型", "播放数", "评论数", "视频标题",
        "视频文案", "作者昵称", "发布时间", "点赞数", "分享数",
        "视频时长", "视频链接",
    ]
