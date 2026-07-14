"""CSV 工具 —— 多行记录解析"""

import csv
from pathlib import Path


def _find_link_column(header: list[str], default_index: int) -> int:
    """Find a link column in both crawler and search-result CSV schemas."""
    normalized = [h.strip().replace("﻿", "") for h in header]
    # Prefer explicit link column names.  Older browser exports use "内容".
    for candidate in ("链接", "url", "URL", "视频链接", "问答链接", "内容"):
        if candidate in normalized:
            return normalized.index(candidate)
    return default_index


def parse_multiline_csv(csv_path: Path, link_col_index: int = 1) -> list[dict]:
    """
    解析包含跨行记录的 CSV 文件。

    检测规则：当指定列以 "http" 开头时认为是新记录，否则追加到上一条记录的最后一个字段。

    返回 list[dict]，每条记录以表头为 key。
    """
    records = []

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        header = [h.strip().replace("﻿", "") for h in header]

        current = None
        for row in reader:
            has_link = len(row) > link_col_index and row[link_col_index].strip().startswith("http")
            if has_link:
                if current is not None:
                    records.append(_row_to_dict(header, current))
                current = row
            else:
                if current is not None and row:
                    current[-1] = current[-1] + "\n" + (row[0] if row else "")

        if current is not None:
            records.append(_row_to_dict(header, current))

    return records


def _row_to_dict(header: list[str], parts: list[str]) -> dict:
    return {header[i]: parts[i].strip() if i < len(parts) else "" for i in range(len(header))}


def extract_links_from_csv(csv_path: Path, link_col_index: int = 1) -> list[str]:
    """
    从 CSV 提取所有链接（兼容跨行记录）。
    适用于只需链接列表的场景（如爬虫入口）。
    """
    links = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)

        col = _find_link_column(header, link_col_index)

        current = None
        for row in reader:
            has_link = len(row) > col and row[col].strip().startswith("http")
            if has_link:
                if current is not None:
                    links.append(current[col].strip() if len(current) > col else "")
                current = row

        if current is not None:
            links.append(current[col].strip() if len(current) > col else "")

    return [l for l in links if l]
