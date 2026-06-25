"""
知乎关键词搜索 + 自动爬取 — 主入口

用法：
  # 搜索关键词并自动爬取完整内容
  conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
    --keywords "智能水杯,恒温杯,Ember温控杯" \
    --pages 5

  # 仅搜索不爬取
  conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
    --keywords "智能水杯" \
    --pages 3 \
    --search-only
"""

import argparse
from pathlib import Path

from .spiders.search import search_and_crawl


def main():
    parser = argparse.ArgumentParser(description="知乎关键词搜索 + 自动爬取")
    parser.add_argument(
        "--keywords", "-k", required=True,
        help="搜索关键词，多个用逗号分隔。例如: '智能水杯,恒温杯,Ember'"
    )
    parser.add_argument(
        "--pages", "-p", type=int, default=5,
        help="每个关键词最多翻几页（每页20条，默认5页=100条/关键词）"
    )
    parser.add_argument(
        "--output-dir", "-o", default=None,
        help="输出目录（默认 res/data/zhihu/output/）"
    )
    parser.add_argument(
        "--search-only", action="store_true",
        help="仅搜索不爬取（只收集链接，不获取完整内容）"
    )
    args = parser.parse_args()

    # 解析关键词
    keywords = [kw.strip() for kw in args.keywords.split(",") if kw.strip()]
    if not keywords:
        print("❌ 请提供至少一个关键词")
        return

    output_dir = Path(args.output_dir) if args.output_dir else None

    search_and_crawl(
        keywords=keywords,
        search_pages=args.pages,
        output_dir=output_dir,
        auto_crawl=not args.search_only,
    )


if __name__ == "__main__":
    main()
