"""
抖音爬虫 — HTML SSR + API 双策略方案

策略 A（优先）：解析 HTML <script id="RENDER_DATA"> SSR JSON，首屏数据无需签名
策略 B（补充）：通过 sign/Request 调用 API 获取视频详情 + 评论翻页

输出 12 字段：关键词、视频类型、播放数、评论数、视频标题、视频文案、
            作者昵称、发布时间、点赞数、分享数、视频时长、视频链接
"""

import re
import time
import json
import random
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

from ..config import config
from ..items import DouyinVideo
from ..sign import Request


class DouyinScraper:
    """抖音爬虫：HTML SSR 解析 + API 补充"""

    def __init__(self, cookie: str = None):
        self.cookie = cookie or config.COOKIE
        if not self.cookie:
            raise ValueError("未设置抖音 Cookie！请在 .env 中设置 DOUYIN_COOKIE=...")

        # 标准 requests session（用于 HTML 页面下载）
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Cookie": self.cookie,
            "Referer": "https://www.douyin.com/",
        })
        self.session.timeout = config.REQUEST_TIMEOUT

        # 签名请求器（用于 API 调用）
        self.api = Request(cookie=self.cookie)

        self._request_count = 0

    # ── 工具 ────────────────────────────────────

    @staticmethod
    def extract_aweme_id(url: str) -> Optional[str]:
        """从链接提取 aweme_id"""
        m = re.search(r'/video/(\d+)', url)
        if m:
            return m.group(1)
        m = re.search(r'aweme_id=(\d+)', url)
        if m:
            return m.group(1)
        return None

    def _delay(self):
        time.sleep(config.REQUEST_DELAY + random.uniform(0, 1.0))
        self._request_count += 1

    # ── 策略 A：RENDER_DATA SSR 解析 ─────────────

    def _scrape_via_render_data(self, aweme_id: str) -> Optional[dict]:
        """从 HTML 页面解析 RENDER_DATA SSR JSON"""
        url = f"https://www.douyin.com/video/{aweme_id}"
        try:
            resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            self._delay()
            if resp.status_code != 200:
                return None

            # 提取 <script id="RENDER_DATA" type="application/json">...</script>
            match = re.search(
                r'<script id="RENDER_DATA" type="application/json">(.*?)</script>',
                resp.text, re.DOTALL
            )
            if not match:
                return None

            raw = match.group(1)
            decoded = unquote(raw)
            data = json.loads(decoded)
            return data
        except Exception:
            return None

    def _parse_render_data(self, data: dict, aweme_id: str) -> dict:
        """从 RENDER_DATA JSON 中提取视频字段"""
        result = {}

        # RENDER_DATA 数据结构：app.initialState 或直接嵌套
        # 常见路径尝试
        for path in [
            ["app", "initialState", "videoDetail"],
            ["40", "post"],
            ["app", "videoDetail"],
        ]:
            node = data
            try:
                for key in path:
                    node = node[key]
                break
            except (KeyError, TypeError):
                node = None
                continue

        if node is None:
            return result

        # 提取字段（兼容多种结构变体）
        if isinstance(node, dict):
            result["desc"] = node.get("desc", "")
            result["author"] = (
                node.get("author", {}).get("nickname", "")
                if isinstance(node.get("author"), dict) else ""
            )
            # 互动数据优先从 statistics 子对象提取
            stats = node.get("statistics", {}) or {}
            result["digg_count"] = stats.get("digg_count", 0) or node.get("digg_count", 0) or 0
            result["comment_count"] = stats.get("comment_count", 0) or node.get("comment_count", 0) or 0
            result["share_count"] = stats.get("share_count", 0) or node.get("share_count", 0) or 0
            result["play_count"] = stats.get("play_count", 0) or node.get("play_count", 0) or 0
            result["duration"] = node.get("duration", 0) or 0
            result["create_time"] = node.get("create_time", 0) or 0

            if result.get("create_time"):
                from datetime import datetime
                result["publish_time"] = datetime.fromtimestamp(result["create_time"]).strftime("%Y-%m-%d %H:%M:%S")

            # 标签
            tags = []
            if isinstance(node.get("text_extra"), list):
                for te in node["text_extra"]:
                    if te.get("hashtag_name"):
                        tags.append(te["hashtag_name"])
            result["tags"] = tags

        return result

    # ── 策略 B：API 调用 ──────────────────────────

    def _scrape_via_api(self, aweme_id: str) -> Optional[dict]:
        """通过 API 获取视频详情"""
        try:
            resp, status = self.api.getJSON(
                '/aweme/v1/web/aweme/detail/',
                {'aweme_id': aweme_id}
            )
            self._delay()
            if status == 200 and resp:
                aweme_detail = resp.get("aweme_detail", {})
                return self._parse_api_detail(aweme_detail)
        except Exception:
            pass
        return None

    def _parse_api_detail(self, detail: dict) -> dict:
        """解析 API 返回的视频详情"""
        result = {}
        if not detail:
            return result

        result["desc"] = detail.get("desc", "")
        result["author"] = (
            detail.get("author", {}).get("nickname", "")
            if isinstance(detail.get("author"), dict) else ""
        )
        result["duration"] = detail.get("duration", 0) or 0

        # 互动数据优先从 statistics 子对象提取
        stats = detail.get("statistics", {}) or {}
        result["digg_count"] = stats.get("digg_count", 0) or detail.get("digg_count", 0) or 0
        result["comment_count"] = stats.get("comment_count", 0) or detail.get("comment_count", 0) or 0
        result["share_count"] = stats.get("share_count", 0) or detail.get("share_count", 0) or 0
        result["play_count"] = stats.get("play_count", 0) or 0

        create_time = detail.get("create_time", 0) or 0
        if create_time:
            from datetime import datetime
            result["publish_time"] = datetime.fromtimestamp(create_time).strftime("%Y-%m-%d %H:%M:%S")

        return result

    # ── 评论获取 ──────────────────────────────────

    def fetch_comments(self, aweme_id: str, max_pages: int = 10) -> list[str]:
        """获取视频评论（纯文本列表）"""
        comments = []
        cursor = 0

        for page in range(max_pages):
            try:
                resp, status = self.api.getJSON(
                    '/aweme/v1/web/comment/list/',
                    {
                        'aweme_id': aweme_id,
                        'cursor': cursor,
                        'count': config.COMMENT_PAGE_SIZE,
                    }
                )
                self._delay()

                if status != 200 or not resp:
                    break

                comment_list = resp.get("comments") or []
                if not comment_list:
                    break

                for c in comment_list:
                    text = c.get("text", "").strip()
                    if text:
                        comments.append(text)

                cursor = resp.get("cursor", 0)
                has_more = resp.get("has_more", 0)
                if not has_more:
                    break

            except Exception:
                break

        return comments

    # ── 主入口 ────────────────────────────────────

    def scrape(self, url: str, keyword: str = "") -> Optional[DouyinVideo]:
        """爬取单个视频的完整数据"""
        aweme_id = self.extract_aweme_id(url)
        if not aweme_id:
            return None

        # 合并双策略数据
        result = {}

        # 策略 A：RENDER_DATA
        render_data = self._scrape_via_render_data(aweme_id)
        if render_data:
            result = self._parse_render_data(render_data, aweme_id)

        # 策略 B：API（补充策略 A 缺失的字段）
        api_data = self._scrape_via_api(aweme_id)
        if api_data:
            for k, v in api_data.items():
                if v and not result.get(k):
                    result[k] = v

        if not result:
            return None

        # 判断视频类型
        video_type = "短视频"
        if result.get("duration", 0) == 0 and result.get("desc"):
            # 可能是图文（没有时长但有描述）
            images = result.get("images", []) or render_data.get("images", []) if render_data else []
            if images:
                video_type = "图文"

        return DouyinVideo(
            url=url,
            aweme_id=aweme_id,
            video_type=video_type,
            desc=result.get("desc", ""),
            content=result.get("desc", ""),  # 抖音视频描述即内容
            author=result.get("author", ""),
            play_count=result.get("play_count", 0),
            digg_count=result.get("digg_count", 0),
            comment_count=result.get("comment_count", 0),
            share_count=result.get("share_count", 0),
            publish_time=result.get("publish_time", ""),
            duration=result.get("duration", 0),
            tags=result.get("tags", []),
        )

    def scrape_with_comments(self, url: str, keyword: str = "", max_comment_pages: int = 5) -> Optional[DouyinVideo]:
        """爬取视频 + 评论"""
        video = self.scrape(url, keyword)
        if video and video.comment_count > 0:
            comments = self.fetch_comments(video.aweme_id, max_comment_pages)
            if comments:
                video.extra["comments"] = comments
        return video
