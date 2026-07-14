"""清洗爬取结果 — 删除污染数据"""
import csv
from pathlib import Path
from source.common.pollution import NSFW_KEYWORDS
from source.common.excel_style import csv_to_excel

INPUT = "res/data/zhihu/output/爬取结果.csv"
OUTPUT = "res/data/zhihu/output/爬取结果_清洗后.csv"

NSFW = NSFW_KEYWORDS

with open(INPUT, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    fieldnames = reader.fieldnames or []

total = len(rows)
kept = []
removed_reasons = {}

for r in rows:
    content = r.get("回答内容", "").strip()
    title = r.get("问题标题", "").strip()
    post_type = r.get("帖子类型", "")
    full_text = f"{title} {content}"

    # 1. 视频 — 删除
    if post_type == "视频":
        removed_reasons["视频无内容"] = removed_reasons.get("视频无内容", 0) + 1
        continue

    # 2. 空内容 — 删除
    if not content and not title:
        removed_reasons["空内容"] = removed_reasons.get("空内容", 0) + 1
        continue

    # 3. NSFW — 删除
    hit = None
    for kw in NSFW:
        if kw in full_text:
            hit = kw; break
    if hit:
        removed_reasons[f"NSFW-{hit}"] = removed_reasons.get(f"NSFW-{hit}", 0) + 1
        continue

    # 4. 太短（<20字）且无赞无评 — 删除
    if len(content) < 20 and int(r.get("赞同数", 0) or 0) == 0 and int(r.get("评论数", 0) or 0) == 0:
        removed_reasons["短内容无互动"] = removed_reasons.get("短内容无互动", 0) + 1
        continue

    kept.append(r)

# 写入
with open(OUTPUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(kept)

print(f"原始: {total} 条")
print(f"保留: {len(kept)} 条")
print(f"删除: {total - len(kept)} 条")
for reason, cnt in sorted(removed_reasons.items(), key=lambda x: -x[1]):
    print(f"  ❌ {reason}: {cnt}")
print(f"\n✅ 清洗后: {OUTPUT}")

# 转 Excel
excel_path = csv_to_excel(
    Path(OUTPUT),
    sheet_title="清洗后数据",
    column_widths={
        "关键词": 25, "帖子类型": 10, "问题被浏览次数": 14, "问题回答个数": 14,
        "问题评论个数": 14, "问题标题": 40, "问题内容": 50, "答主昵称": 14,
        "回答时间": 16, "赞同数": 10, "评论数": 10, "回答内容": 55, "问答链接": 35,
    },
    link_columns={"问答链接"},
    number_columns={"赞同数", "评论数", "问题被浏览次数", "问题回答个数", "问题评论个数"},
)
print(f"✅ Excel: {excel_path}")
