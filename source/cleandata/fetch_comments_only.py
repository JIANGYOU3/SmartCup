"""
补评论脚本 — 读取已有爬取结果，仅拉取评论，输出完整 CSV。

用法：
  conda run -n SmartCup python -u source/cleandata/fetch_comments_only.py
  conda run -n SmartCup python -u source/cleandata/fetch_comments_only.py \
    --input res/data/douyin/output/爬取结果_全量.csv \
    --output res/data/douyin/output/爬取结果_全量_含评论.csv \
    --workers 2
"""

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from source.douyin_crawler.spiders.douyin import DouyinScraper
from source.douyin_crawler.items import DouyinVideo
from source.common.paths import get_project_root

from tqdm import tqdm


def extract_aweme_id(url: str) -> str:
    """从视频链接提取 aweme_id"""
    m = re.search(r'/video/(\d+)', url)
    return m.group(1) if m else ""


def main():
    parser = argparse.ArgumentParser(description="补拉抖音视频评论")
    parser.add_argument("--input", "-i",
                        default="res/data/douyin/output/爬取结果_全量.csv")
    parser.add_argument("--output", "-o",
                        default="res/data/douyin/output/爬取结果_全量_含评论.csv")
    parser.add_argument("--comment-pages", type=int, default=5,
                        help="评论翻页数（默认5，每页50条）")
    parser.add_argument("--cookie", default="",
                        help="抖音 Cookie（优先 .env）")
    args = parser.parse_args()

    project_root = get_project_root()
    input_path = project_root / args.input
    output_path = project_root / args.output

    # 读取已有数据
    with open(input_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"📂 读取: {len(rows)} 条视频")

    # 初始化爬虫
    scraper = DouyinScraper(args.cookie)

    # 输出列：基础列 + 评论展开列
    out_fieldnames = DouyinVideo.get_fieldnames(20)
    # 保留原始"关键词"列
    if "关键词" not in out_fieldnames:
        out_fieldnames.insert(0, "关键词")

    success = 0
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fieldnames, extrasaction='ignore')
        writer.writeheader()

        for row in tqdm(rows, desc="拉取评论", unit="条"):
            url = row.get("视频链接", "")
            aweme_id = extract_aweme_id(url)
            if not aweme_id:
                continue

            try:
                comments = scraper.fetch_comments(aweme_id, max_pages=args.comment_pages)
            except Exception as e:
                print(f"  ⚠️ 评论拉取失败 {aweme_id}: {e}")
                comments = []

            # 构建输出行（保留基础字段 + 追加评论）
            out_row = {}
            for key in DouyinVideo.BASE_FIELDNAMES:
                out_row[key] = row.get(key, "")

            # 展开评论
            max_comments = 20
            for i, c in enumerate(comments[:max_comments]):
                idx = i + 1
                out_row[f"评论{idx}"] = c.text
                out_row[f"评论{idx}点赞"] = c.digg_count
                out_row[f"评论{idx}回复数"] = c.reply_total
                out_row[f"评论{idx}用户"] = c.user
                out_row[f"评论{idx}时间"] = c.create_time
                out_row[f"评论{idx}属地"] = c.ip_label
                if c.sub_replies:
                    for j, sr in enumerate(c.sub_replies[:3]):
                        sj = j + 1
                        out_row[f"评论{idx}子回复{sj}"] = sr.get("text", "")
                        out_row[f"评论{idx}子回复{sj}用户"] = sr.get("user", "")
                        out_row[f"评论{idx}子回复{sj}点赞"] = sr.get("digg", 0)

            if comments:
                import json
                out_row["评论JSON"] = json.dumps(
                    [c.to_dict() for c in comments], ensure_ascii=False
                )

            writer.writerow(out_row)
            f.flush()
            success += 1

    print(f"\n✅ 完成: {success}/{len(rows)} 条")
    print(f"📂 输出: {output_path}")


if __name__ == "__main__":
    main()
