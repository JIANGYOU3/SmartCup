~"""数据处理管道"""

import csv
import json
from pathlib import Path
from typing import Iterator

from .items import ZhihuPost
from .config import config


class CsvPipeline:
    """CSV 输出管道"""

    def __init__(self, output_path: Path = None):
        self.output_path = output_path or config.DATA_OUTPUT / "crawled_posts.csv"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._writer = None

    def open(self):
        """打开文件准备写入"""
        self._file = open(self.output_path, "w", encoding=config.OUTPUT_ENCODING, newline="")
        fieldnames = ["链接", "标题", "正文", "作者", "点赞数", "评论数", "发布时间", "图片", "标签"]
        self._writer = csv.DictWriter(self._file, fieldnames=fieldnames)
        self._writer.writeheader()

    def process_item(self, item: ZhihuPost):
        """写入单条记录"""
        if self._writer:
            self._writer.writerow(item.to_dict())

    def close(self):
        """关闭文件"""
        if self._file:
            self._file.close()


class JsonPipeline:
    """JSON 输出管道"""

    def __init__(self, output_path: Path = None):
        self.output_path = output_path or config.DATA_OUTPUT / "crawled_posts.json"
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._items = []

    def process_item(self, item: ZhihuPost):
        self._items.append(item.to_dict())

    def close(self):
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(self._items, f, ensure_ascii=False, indent=2)
