"""爬虫中间件"""

import time
import random
from .config import config


class RequestMiddleware:
    """请求中间件：处理请求头、Cookie、延迟等"""

    DEFAULT_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "User-Agent": config.USER_AGENT,
    }

    @classmethod
    def get_headers(cls, referer: str = "") -> dict:
        headers = cls.DEFAULT_HEADERS.copy()
        if referer:
            headers["Referer"] = referer
        if config.COOKIE:
            headers["Cookie"] = config.COOKIE
        return headers

    @classmethod
    def delay(cls):
        """请求间隔"""
        time.sleep(config.REQUEST_DELAY + random.uniform(0, 1.0))
