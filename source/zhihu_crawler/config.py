"""爬虫配置"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


class CrawlerConfig:
    """知乎爬虫配置"""

    # 项目路径
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    DATA_RAW = PROJECT_ROOT / "res" / "data" / "zhihu" / "raw"
    DATA_OUTPUT = PROJECT_ROOT / "res" / "data" / "zhihu" / "output"

    # 请求配置
    REQUEST_DELAY = 2.0                # 请求间隔（秒）
    REQUEST_TIMEOUT = 30               # 请求超时（秒）
    MAX_RETRIES = 3                    # 重试次数

    # 并发配置
    MAX_WORKERS = 4                    # 并发数

    # User-Agent
    USER_AGENT = os.getenv(
        "CRAWLER_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )

    # Cookie（从环境变量加载，可选）
    COOKIE = os.getenv("ZHIHU_COOKIE", "")

    # 输出编码
    OUTPUT_ENCODING = "utf-8-sig"


config = CrawlerConfig()
