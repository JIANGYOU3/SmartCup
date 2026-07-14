"""抖音爬虫 — 输出管道"""

import csv
import json
from pathlib import Path
from typing import Iterator

from .items import DouyinVideo
from .config import config


class CsvPipeline:
    """CSV 输出管道"""

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._writer = None

    def open(self):
        self._file = open(self.output_path, "w", encoding=config.OUTPUT_ENCODING, newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=DouyinVideo.get_fieldnames())
        self._writer.writeheader()
        self._file.flush()

    def write(self, video: DouyinVideo):
        self._writer.writerow(video.to_dict())
        self._file.flush()

    def close(self):
        if self._file:
            self._file.close()


class JsonPipeline:
    """JSON 输出管道"""

    def __init__(self, output_path: Path):
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._items = []

    def write(self, video: DouyinVideo):
        self._items.append(video.to_dict())

    def close(self):
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(self._items, f, ensure_ascii=False, indent=2)
