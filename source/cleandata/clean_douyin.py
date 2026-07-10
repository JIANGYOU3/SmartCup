"""
抖音数据深度清洗 — 去空/去NSFW/去无关/去低质

用法：
  conda run -n SmartCup python source/cleandata/clean_douyin.py
  conda run -n SmartCup python source/cleandata/clean_douyin.py --input 标签结果.csv --dry-run
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from source.common.pollution import is_polluted
from source.common.excel_style import csv_to_excel

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "res/data/douyin/output"
DEFAULT_INPUT = DATA_DIR / "标签结果.csv"
DEFAULT_OUTPUT = DATA_DIR / "标签结果_清洗后.csv"

# 低质内容判断阈值
MIN_CONTENT_LEN = 15          # 标题+文案最少字数
MIN_ENGAGEMENT = 2            # 点赞+收藏 最少互动数


def extract_aweme_id(url: str) -> str:
    m = re.search(r'/video/(\d+)', url)
    return m.group(1) if m else ""


def clean(rows: list[dict], dry_run: bool = False) -> tuple[list[dict], Counter]:
    """清洗数据，返回 (干净数据, 统计)"""
    stats = Counter()
    stats["total"] = len(rows)
    seen_ids = set()
    seen_urls = set()
    cleaned = []

    for r in rows:
        url = r.get("视频链接", "").strip()
        title = r.get("视频标题", "").strip()
        desc = r.get("视频文案", "").strip()
        full_text = f"{title} {desc}"

        # ── 1. 去重（按 aweme_id 和 URL） ──
        aid = extract_aweme_id(url)
        if aid and aid in seen_ids:
            stats["重复ID"] += 1
            continue
        if url and url in seen_urls:
            stats["重复URL"] += 1
            continue
        if aid:
            seen_ids.add(aid)
        if url:
            seen_urls.add(url)

        # ── 2. 污染检测 ──
        reason = is_polluted(title, desc, min_title_len=3, min_content_len=5)
        if reason:
            stats[f"污染-{reason}"] += 1
            continue

        # ── 3. 视频类型过滤（直播跳过） ──
        vtype = r.get("视频类型", "").strip()
        if vtype == "直播":
            stats["过滤-直播"] += 1
            continue

        # ── 4. 低质：空内容 ──
        if len(full_text.strip()) < MIN_CONTENT_LEN:
            stats["低质-内容过短"] += 1
            continue

        # ── 5. 低质：标题全是标签/无实义 ──
        title_no_tags = re.sub(r'#\S+', '', title).strip()
        desc_no_tags = re.sub(r'#\S+', '', desc).strip()
        if len(title_no_tags) < 3 and len(desc_no_tags) < 3:
            stats["低质-纯标签"] += 1
            continue

        # ── 6. 低质：零互动 ──
        try:
            likes = int(r.get("点赞数", 0) or 0)
            collects = int(r.get("收藏数", 0) or 0)
        except ValueError:
            likes = collects = 0
        if likes + collects < MIN_ENGAGEMENT:
            stats["低质-零互动"] += 1
            continue

        # ── 文本规范化 ──
        r["视频标题"] = title
        r["视频文案"] = desc

        cleaned.append(r)

    stats["保留"] = len(cleaned)
    stats["移除"] = stats["total"] - stats["保留"]
    return cleaned, stats


def main():
    parser = argparse.ArgumentParser(description="抖音数据深度清洗")
    parser.add_argument("--input", "-i", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", "-o", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dry-run", action="store_true", help="仅检查不输出")
    args = parser.parse_args()

    # 读取
    with open(args.input, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"📂 读取: {len(rows)} 条")

    # 清洗
    cleaned, stats = clean(rows, dry_run=args.dry_run)

    # 报告
    print(f"\n{'='*50}")
    print(f"  🧹 数据清洗报告")
    print(f"{'='*50}")
    print(f"  清洗前: {stats['total']:,} 条")
    print(f"  清洗后: {stats['保留']:,} 条")
    print(f"  移除:   {stats['移除']:,} 条 ({stats['移除']/max(stats['total'],1)*100:.1f}%)")
    print(f"{'='*50}")
    print(f"  明细:")
    for reason in sorted(stats.keys()):
        if reason not in ("total", "保留", "移除") and stats[reason] > 0:
            print(f"    - {reason}: {stats[reason]}")
    print(f"{'='*50}")

    if args.dry_run:
        print("\n⚠️ Dry-run 模式，未写入文件")
        return

    # 输出
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(cleaned)

    print(f"\n📂 清洗后: {args.output}")

    # Excel
    try:
        excel_path = csv_to_excel(
            Path(args.output),
            sheet_title="抖音标签结果(清洗后)",
            column_widths={"视频标题": 45, "视频文案": 55, "视频链接": 35,
                          "作者昵称": 14, "需求痛点": 40, "一句话总结": 40},
            link_columns={"视频链接"},
        )
        print(f"📂 Excel: {excel_path}")
    except Exception as e:
        print(f"⚠️ Excel 生成失败: {e}")


if __name__ == "__main__":
    main()
