"""
抖音爬虫 — 主入口（基于已有链接列表）

用法：
  conda run -n SmartCup python -u -m source.douyin_crawler.main

  # 指定输入输出
  conda run -n SmartCup python -u -m source.douyin_crawler.main \
    --input res/data/douyin/raw/链接列表.csv \
    --output res/data/douyin/output/爬取结果.csv
"""

import argparse
from pathlib import Path

from source.common.paths import get_project_root
from source.common.excel_style import csv_to_excel
from source.common.csv_utils import extract_links_from_csv
from .spiders.douyin import DouyinScraper
from .items import DouyinVideo


def main():
    parser = argparse.ArgumentParser(description="抖音视频批量爬虫（基于链接列表）")
    parser.add_argument("--input", "-i", default="res/data/douyin/raw/链接列表.csv")
    parser.add_argument("--output", "-o", default="res/data/douyin/output/爬取结果.csv")
    parser.add_argument("--cookie", "-c", default="", help="抖音 Cookie（优先 .env）")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    project_root = get_project_root()
    input_path = project_root / args.input
    output_path = project_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    use_resume = not args.no_resume

    print("=" * 60, flush=True)
    print("抖音视频爬虫", flush=True)
    print("=" * 60, flush=True)
    print(f"  输入: {input_path}", flush=True)
    print(f"  输出: {output_path}", flush=True)
    print(f"  断点续爬: {'开启' if use_resume else '关闭'}", flush=True)
    print(flush=True)

    # 加载链接
    links = extract_links_from_csv(input_path, link_col_index=0)
    print(f"📂 共 {len(links)} 条链接\n")

    # 断点续爬：读取已处理的 URL
    processed_urls = set()
    import csv
    if use_resume and output_path.exists():
        with open(output_path, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                processed_urls.add(row.get("视频链接", ""))

    scraper = DouyinScraper(args.cookie)

    from tqdm import tqdm

    with open(output_path, "a" if use_resume else "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=DouyinVideo.FIELDNAMES)
        if not use_resume or not processed_urls:
            writer.writeheader()

        success = 0
        skipped = 0
        for url in tqdm(links, desc="爬取视频", unit="个"):
            if url in processed_urls:
                skipped += 1
                continue

            video = scraper.scrape(url)
            if video:
                writer.writerow(video.to_dict())
                f.flush()
                success += 1

    print(f"\n✅ 完成: {success} 条新增, {skipped} 条跳过")

    # 转 Excel
    if output_path.exists():
        print(f"\n📊 正在生成 Excel...")
        try:
            excel_path = csv_to_excel(
                output_path,
                sheet_title="抖音爬取结果",
                column_widths={
                    "关键词": 20, "视频类型": 10, "播放数": 12, "评论数": 10,
                    "视频标题": 45, "视频文案": 55, "作者昵称": 14,
                    "发布时间": 16, "点赞数": 10, "分享数": 10,
                    "视频时长": 10, "视频链接": 35,
                },
                link_columns={"视频链接"},
                number_columns={"播放数", "评论数", "点赞数", "分享数", "视频时长"},
            )
            print(f"✅ Excel 已保存: {excel_path}")
        except Exception as e:
            print(f"⚠️ Excel 生成失败: {e}")


if __name__ == "__main__":
    main()
