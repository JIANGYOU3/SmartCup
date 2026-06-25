"""数据模型"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ZhihuPost:
    """知乎帖子"""
    url: str                                    # 链接
    title: str                                  # 标题
    content: str = ""                           # 正文
    author: str = ""                            # 作者
    upvotes: int = 0                            # 点赞数
    comments: int = 0                           # 评论数
    publish_time: str = ""                      # 发布时间
    images: list[str] = field(default_factory=list)   # 图片链接列表
    tags: list[str] = field(default_factory=list)      # 话题标签
    extra: dict = field(default_factory=dict)          # 额外字段

    def to_dict(self) -> dict:
        return {
            "链接": self.url,
            "标题": self.title,
            "正文": self.content,
            "作者": self.author,
            "点赞数": self.upvotes,
            "评论数": self.comments,
            "发布时间": self.publish_time,
            "图片": " | ".join(self.images),
            "标签": ", ".join(self.tags),
        }
