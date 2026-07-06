"""知乎爬虫 — 主入口..."""

import sys
import argparse
from pathlib import Path

from source.common.paths import get_project_root, get_output_dir
from source.common.excel_style import csv_to_excel
from .spiders.zhihu import run_batch_scrape


def main():
    parser = argparse.ArgumentParser(description="知乎内容批量爬虫")
    parser.add_argument("--input", "-i", default="res/data/zhihu/raw/标题筛选版1.0.csv")
    parser.add_argument("--output", "-o", default="res/data/zhihu/output/爬取结果.csv")
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()

    project_root = get_project_root()
    input_path = project_root / args.input
    output_path = project_root / args.output
    use_resume = not args.no_resume

    print("=" * 60, flush=True)
    print("知乎内容批量爬虫", flush=True)
    print("=" * 60, flush=True)
    print(f"  输入: {input_path}", flush=True)
    print(f"  输出: {output_path}", flush=True)
    print(f"  断点续爬: {'开启' if use_resume else '关闭'}", flush=True)
    print(flush=True)

    run_batch_scrape(
        input_csv=input_path,
        output_csv=output_path,
        resume=use_resume,
    )

    # ── 自动转 Excel ──
    if output_path.exists():
        print(f"\n📊 正在生成 Excel...", flush=True)
        try:
            excel_path = csv_to_excel(
                output_path,
                sheet_title="爬取结果",
                column_widths={
                    "关键词": 25, "帖子类型": 10, "问题被浏览次数": 14, "问题回答个数": 14,
                    "问题评论个数": 14, "问题标题": 40, "问题内容": 50, "答主昵称": 14,
                    "回答时间": 16, "赞同数": 10, "评论数": 10, "回答内容": 55, "问答链接": 35,
                },
                link_columns={"问答链接"},
                number_columns={"赞同数", "评论数", "问题被浏览次数", "问题回答个数", "问题评论个数"},
            )
            print(f"✅ Excel 已保存: {excel_path}", flush=True)
        except Exception as e:
            print(f"⚠️ Excel 生成失败: {e}", flush=True)


if __name__ == "__main__":
    main()
