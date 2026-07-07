"""
抖音搜索爬虫 — 入口（关键词搜索 + 自动爬取）

用法：
  # 搜索关键词 + 自动爬取完整内容
  conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
    --keywords "智能水杯,恒温杯,Ember温控杯" \
    --pages 5

  # 仅搜索不爬取（先看结果再决定）
  conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
    --keywords "智能水杯" --pages 3 --search-only
"""

import argparse

from .spiders.search import search_and_crawl


def main():
    parser = argparse.ArgumentParser(description="抖音关键词搜索 + 视频爬虫")
    parser.add_argument("--keywords", "-k", required=True,
                        help="搜索关键词（逗号分隔）")
    parser.add_argument("--pages", "-p", type=int, default=5,
                        help="每个关键词翻页数（默认 5，每页 20 条）")
    parser.add_argument("--cookie", "-c", default="",
                        help="抖音 Cookie（优先 .env 中的 DOUYIN_COOKIE）")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="输出目录（默认 res/data/douyin/output/）")
    parser.add_argument("--search-only", action="store_true",
                        help="仅搜索不爬取内容")
    parser.add_argument("--with-comments", action="store_true",
                        help="同时抓取评论（含点赞/回复数/子回复）")
    parser.add_argument("--comment-pages", type=int, default=5,
                        help="评论翻页数（默认5，每页20条）")
    parser.add_argument("--sort", type=int, default=1, choices=[0, 1, 2],
                        help="排序方式: 0=综合 1=最多点赞(默认) 2=最新发布")
    args = parser.parse_args()

    keywords = [kw.strip() for kw in args.keywords.split(",") if kw.strip()]
    if not keywords:
        print("❌ 请提供至少一个搜索关键词")
        return

    search_and_crawl(
        keywords=keywords,
        search_pages=args.pages,
        output_dir=args.output_dir,
        cookie=args.cookie,
        search_only=args.search_only,
        with_comments=args.with_comments,
        comment_pages=args.comment_pages,
        sort_type=args.sort,
    )


if __name__ == "__main__":
    main()
