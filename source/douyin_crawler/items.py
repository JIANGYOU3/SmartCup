"""抖音数据模型"""

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DouyinComment:
    """抖音评论"""

    cid: str = ""                     # 评论 ID
    user: str = ""                    # 评论者昵称
    text: str = ""                    # 评论内容
    digg_count: int = 0               # 评论点赞数
    reply_total: int = 0              # 回复总数
    create_time: str = ""             # 评论时间
    ip_label: str = ""                # IP 属地
    sub_replies: list[dict] = field(default_factory=list)  # 子回复 [{user, text, digg_count}]

    def to_dict(self) -> dict:
        return {
            "cid": self.cid,
            "user": self.user,
            "text": self.text,
            "digg_count": self.digg_count,
            "reply_total": self.reply_total,
            "create_time": self.create_time,
            "ip_label": self.ip_label,
            "sub_replies": self.sub_replies,
        }


@dataclass
class DouyinVideo:
    """抖音视频"""

    url: str = ""
    aweme_id: str = ""
    video_type: str = ""              # 短视频 / 图文 / 直播
    desc: str = ""                     # 视频描述/标题
    content: str = ""                  # 视频文案（完整描述）
    author: str = ""                   # 作者昵称
    author_follower_count: int = 0     # 🆕 作者粉丝量
    play_count: int = 0                # 播放数
    digg_count: int = 0                # 点赞数
    comment_count: int = 0             # 评论数
    collect_count: int = 0             # 🆕 收藏数
    share_count: int = 0               # 分享数
    publish_time: str = ""             # 发布时间
    duration: int = 0                  # 视频时长（秒）
    tags: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    comments: list[DouyinComment] = field(default_factory=list)  # 🆕 结构化评论
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转为中文列名的字典"""
        result = {
            "关键词": "",
            "视频类型": self.video_type,
            "播放数": self.play_count,
            "评论数": self.comment_count,
            "视频标题": self.desc,
            "视频文案": self.content,
            "作者昵称": self.author,
            "作者粉丝量": self.author_follower_count,
            "发布时间": self.publish_time,
            "点赞数": self.digg_count,
            "收藏数": self.collect_count,
            "分享数": self.share_count,
            "视频时长": self.duration,
            "视频链接": self.url,
        }

        # 🆕 展开评论到多列：评论1, 评论1点赞, 评论1回复数, 评论1用户, 评论1时间, ...
        # 以及子回复
        max_comments = 20  # 最多展开前20条评论
        for i, c in enumerate(self.comments[:max_comments]):
            idx = i + 1
            result[f"评论{idx}"] = c.text
            result[f"评论{idx}点赞"] = c.digg_count
            result[f"评论{idx}回复数"] = c.reply_total
            result[f"评论{idx}用户"] = c.user
            result[f"评论{idx}时间"] = c.create_time
            result[f"评论{idx}属地"] = c.ip_label
            # 子回复（前3条）
            if c.sub_replies:
                for j, sr in enumerate(c.sub_replies[:3]):
                    sj = j + 1
                    result[f"评论{idx}子回复{sj}"] = sr.get("text", "")
                    result[f"评论{idx}子回复{sj}用户"] = sr.get("user", "")
                    result[f"评论{idx}子回复{sj}点赞"] = sr.get("digg", 0)

        # 完整评论 JSON（备用）
        if self.comments:
            result["评论JSON"] = json.dumps(
                [c.to_dict() for c in self.comments],
                ensure_ascii=False
            )

        return result

    # 基础输出字段名
    BASE_FIELDNAMES = [
        "关键词", "视频类型", "播放数", "评论数", "视频标题",
        "视频文案", "作者昵称", "作者粉丝量", "发布时间", "点赞数", "收藏数",
        "分享数", "视频时长", "视频链接",
    ]

    # 🆕 评论展开列
    @classmethod
    def get_fieldnames(cls, comment_count: int = 20) -> list[str]:
        """动态生成输出列名"""
        fields = list(cls.BASE_FIELDNAMES)
        for i in range(1, comment_count + 1):
            fields.extend([
                f"评论{i}", f"评论{i}点赞", f"评论{i}回复数",
                f"评论{i}用户", f"评论{i}时间", f"评论{i}属地",
                f"评论{i}子回复1", f"评论{i}子回复1用户", f"评论{i}子回复1点赞",
                f"评论{i}子回复2", f"评论{i}子回复2用户", f"评论{i}子回复2点赞",
                f"评论{i}子回复3", f"评论{i}子回复3用户", f"评论{i}子回复3点赞",
            ])
        fields.append("评论JSON")
        return fields
