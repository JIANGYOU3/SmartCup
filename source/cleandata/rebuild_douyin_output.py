"""
重建抖音标签输出文件 — 修复评论列顺序 bug（无需重新调用 AI API）

原理：
  - 从已有的 标签结果.csv 的 AI原始JSON 列中提取 AI 标签
  - 从 爬取结果_清洗后.csv 读取原始数据（评论列顺序正确）
  - 用修复后的 build_output() 重建列顺序正确的输出

用法：
  conda run -n SmartCup python source/cleandata/rebuild_douyin_output.py
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from source.cleandata.douyin_labeler import build_output
from source.common.excel_style import csv_to_excel

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "res/data/douyin/output"

RAW_CSV = DATA_DIR / "爬取结果_清洗后.csv"       # 原始数据（评论列顺序正确）
OLD_LABELED = DATA_DIR / "标签结果.csv"           # 旧标签结果（列顺序有bug，但AI标签正确）
NEW_LABELED = DATA_DIR / "标签结果.csv"           # 覆盖写入

# 预定义正确的列顺序（与修复后的 douyin_labeler.py 保持一致）
COMMENT_FIELDS = ["", "点赞", "回复数", "用户", "时间", "属地",
                  "子回复1", "子回复1用户", "子回复1点赞",
                  "子回复2", "子回复2用户", "子回复2点赞",
                  "子回复3", "子回复3用户", "子回复3点赞"]

CORRECT_FIELDNAMES = [
    "视频标题", "视频文案", "作者昵称", "作者粉丝量",
    "点赞数", "评论数", "收藏数", "分享数", "发布时间", "视频链接",
    "内容标签", "相关性等级", "相关性理由", "话题类别", "用户情绪",
    "需求痛点", "数据价值等级", "数据价值理由", "关键词", "一句话总结",
    "AI原始JSON",
]
for i in range(1, 21):
    for sfx in COMMENT_FIELDS:
        CORRECT_FIELDNAMES.append(f"评论{i}{sfx}")
    if i == 1:
        CORRECT_FIELDNAMES.append("评论JSON")


def main():
    print("=" * 60)
    print("🔧 重建抖音标签输出（修复评论列顺序）")
    print("=" * 60)

    # ── 1. 读取原始数据 ──
    print(f"\n📂 读取原始数据: {RAW_CSV.name}")
    with open(RAW_CSV, encoding="utf-8-sig") as f:
        raw_rows = list(csv.DictReader(f))
    print(f"   {len(raw_rows)} 条")

    # 构建 URL → raw_row 映射
    raw_by_url = {}
    for r in raw_rows:
        url = r.get("视频链接", "").strip()
        if url:
            raw_by_url[url] = r

    # ── 2. 从旧标签结果提取 AI 标签 ──
    print(f"\n📂 读取旧标签: {OLD_LABELED.name}")
    with open(OLD_LABELED, encoding="utf-8-sig") as f:
        old_rows = list(csv.DictReader(f))
    print(f"   {len(old_rows)} 条")

    if len(old_rows) != len(raw_rows):
        print(f"   ⚠️ 行数不一致: 标签({len(old_rows)}) vs 原始({len(raw_rows)})")
        print(f"   将用视频链接匹配重建...")

    # 提取每行的 AI 标签（从 AI原始JSON 列）
    paired = []  # (raw_row, labels_dict)
    skipped = 0
    parse_errors = 0

    for old_row in old_rows:
        url = old_row.get("视频链接", "").strip()
        ai_json_raw = old_row.get("AI原始JSON", "{}").strip()

        try:
            labels = json.loads(ai_json_raw) if ai_json_raw else {}
        except json.JSONDecodeError:
            labels = {}
            parse_errors += 1

        # 获取对应的原始数据
        raw_row = raw_by_url.get(url)
        if raw_row is None:
            # 降级：用旧行数据本身
            raw_row = old_row
            skipped += 1

        paired.append((raw_row, labels))

    if parse_errors:
        print(f"   ⚠️ {parse_errors} 条 AI原始JSON 解析失败（将用空标签）")
    if skipped:
        print(f"   ⚠️ {skipped} 条在原始数据中未找到对应URL")
    print(f"   ✅ {len(paired)} 条匹配成功")

    # ── 3. 用修复后的 build_output 重建 ──
    print(f"\n🔧 用修复后的 build_output() 重建...")
    raw_list, labels_list = zip(*paired) if paired else ([], [])
    output_rows = build_output(list(raw_list), list(labels_list))
    print(f"   ✅ {len(output_rows)} 条")

    # ── 4. 验证列顺序 ──
    errors = []
    # 检查评论7位置
    for idx, fn in enumerate(CORRECT_FIELDNAMES):
        if fn.startswith("评论7") and "评论" in fn:
            # 确保评论7在评论6之后、评论8之前
            break

    c7_first = next((i for i, fn in enumerate(CORRECT_FIELDNAMES) if fn == "评论7"), -1)
    c6_last = max((i for i, fn in enumerate(CORRECT_FIELDNAMES) if fn.startswith("评论6")), default=-1)
    c8_first = next((i for i, fn in enumerate(CORRECT_FIELDNAMES) if fn == "评论8"), -1)

    if not (c6_last < c7_first < c8_first):
        errors.append(f"评论7位置异常: c6@{c6_last}, c7@{c7_first}, c8@{c8_first}")
    else:
        print(f"   ✅ 评论7位置正确: 评论6@{c6_last} < 评论7@{c7_first} < 评论8@{c8_first}")

    # ── 5. 检查数据完整性 ──
    # 确保输出行数与输入一致，核心字段不丢失
    for i, (out_row, (raw_row, labels)) in enumerate(zip(output_rows, paired)):
        # 核心字段
        for k in ["视频标题", "视频链接", "点赞数", "评论数"]:
            if k not in out_row:
                errors.append(f"行{i} 缺失核心字段: {k}")

    # 检查 AI 标签字段
    has_content_labels = sum(1 for r in output_rows if r.get("内容标签", "").strip())
    if has_content_labels == 0:
        errors.append("所有行内容标签为空！")
    else:
        print(f"   ✅ {has_content_labels}/{len(output_rows)} 行有内容标签")

    if errors:
        print(f"\n❌ {len(errors)} 个错误:")
        for e in errors:
            print(f"   - {e}")
        print("\n⚠️ 中止写入，保留原文件不变")
        return 1

    # ── 6. 写 CSV ──
    print(f"\n💾 写入: {NEW_LABELED.name}")
    with open(NEW_LABELED, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CORRECT_FIELDNAMES, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"   ✅ {len(output_rows)} 条, {len(CORRECT_FIELDNAMES)} 列")

    # ── 7. 写 Excel ──
    try:
        excel_path = csv_to_excel(
            NEW_LABELED,
            sheet_title="抖音标签结果",
            column_widths={
                "视频标题": 50, "视频文案": 60, "作者昵称": 14,
                "作者粉丝量": 12, "点赞数": 10, "评论数": 10,
                "收藏数": 10, "分享数": 10,
                "内容标签": 30, "相关性等级": 10, "话题类别": 10,
                "用户情绪": 10, "需求痛点": 40, "数据价值等级": 12,
                "关键词": 30, "一句话总结": 30,
            },
            link_columns={"视频链接"},
            number_columns={"点赞数", "评论数", "收藏数", "分享数", "作者粉丝量"},
        )
        print(f"📂 Excel: {excel_path}")
    except Exception as e:
        print(f"⚠️ Excel 失败: {e}")

    print(f"\n{'=' * 60}")
    print("✅ 重建完成")
    print(f"{'=' * 60}")
    print(f"\n💡 接下来运行 clean_douyin_v2.py 重新生成 标签结果_最终.csv:")
    print(f"   conda run -n SmartCup python source/cleandata/clean_douyin_v2.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
