"""抖音爬虫配置"""

import os

from source.common.paths import get_project_root, get_data_dir, load_env

load_env()


class DouyinCrawlerConfig:
    """抖音爬虫配置"""

    # 项目路径
    PROJECT_ROOT = get_project_root()
    DATA_RAW = get_data_dir("douyin") / "raw"
    DATA_OUTPUT = get_data_dir("douyin") / "output"

    # 请求配置
    REQUEST_DELAY = 3.0                 # 请求间隔（秒），抖音反爬严格
    REQUEST_TIMEOUT = 30                # 请求超时（秒）
    MAX_RETRIES = 3                     # 重试次数

    # 并发配置（抖音反爬严格，建议低并发）
    MAX_WORKERS = 2

    # User-Agent
    USER_AGENT = os.getenv(
        "DOUYIN_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    # Cookie（必需，用于 API 签名 + 身份验证）
    COOKIE = os.getenv("DOUYIN_COOKIE", "")

    # 输出编码
    OUTPUT_ENCODING = "utf-8-sig"

    # 评论每页条数
    COMMENT_PAGE_SIZE = 50


config = DouyinCrawlerConfig()
