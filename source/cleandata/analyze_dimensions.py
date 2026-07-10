"""
关键词维度分析 — 标签结果 × 关键词分类 × 互动数据

用法：
  conda run -n SmartCup python source/cleandata/analyze_dimensions.py
"""

import csv
import re
import json
from pathlib import Path
from collections import defaultdict, Counter

PROJECT = Path(__file__).resolve().parent.parent.parent
DATA = PROJECT / "res/data/douyin/output"

# ── 读取关键词分类表 ──
def load_keyword_categories():
    """读取关键词表，返回 {关键词: 类别}"""
    kw2cat = {}
    with open(DATA / "关键词表.csv", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        categories = [h for h in header if h.strip()]
        for row in reader:
            for i, cell in enumerate(row):
                kw = cell.strip()
                if kw and i < len(categories):
                    kw2cat[kw] = categories[i]
    return kw2cat

# ── 读取搜索结果（关键词→aweme_id 映射）──
def load_search_map():
    """返回 {aweme_id: keyword}"""
    id2kw = {}
    for csv_file in sorted(DATA.glob("搜索结果_*.csv")):
        try:
            with open(csv_file, encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    aid = row.get("aweme_id", "").strip()
                    kw = row.get("keyword", "").strip()
                    if aid and kw:
                        id2kw[aid] = kw
        except Exception:
            pass
    return id2kw

def extract_aweme_id(url: str) -> str:
    m = re.search(r'/video/(\d+)', url)
    return m.group(1) if m else ""

# ── 主分析 ──
def main():
    kw2cat = load_keyword_categories()
    id2kw = load_search_map()
    print(f"关键词分类: {len(set(kw2cat.values()))} 类, {len(kw2cat)} 个关键词")
    print(f"搜索映射: {len(id2kw)} 条记录")

    # 读取标签结果
    rows = []
    with open(DATA / "标签结果.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    print(f"标签结果: {len(rows)} 条\n")

    # 统计维度
    # 按类别
    cat_stats = defaultdict(lambda: {
        "videos": 0, "likes": 0, "comments": 0, "collects": 0, "shares": 0,
        "标签": Counter(), "情绪": Counter(), "话题": Counter(), "相关性": Counter(),
        "高价值": 0, "中价值": 0, "低价值": 0,
        "正面": 0, "负面": 0, "中性": 0, "混合": 0,
    })

    unmatched = 0
    for r in rows:
        url = r.get("视频链接", "")
        aid = extract_aweme_id(url)
        kw = id2kw.get(aid, "")
        cat = kw2cat.get(kw, "未分类")

        try:
            likes = int(r.get("点赞数", 0) or 0)
            comments = int(r.get("评论数", 0) or 0)
            collects = int(r.get("收藏数", 0) or 0)
            shares = int(r.get("分享数", 0) or 0)
        except ValueError:
            likes = comments = collects = shares = 0

        if not kw:
            unmatched += 1

        s = cat_stats[cat]
        s["videos"] += 1
        s["likes"] += likes
        s["comments"] += comments
        s["collects"] += collects
        s["shares"] += shares

        # AI 标签
        labels_raw = r.get("内容标签", "")
        if labels_raw:
            for label in str(labels_raw).replace("，", ",").split(","):
                label = label.strip().strip("[]'\" ")
                if label:
                    s["标签"][label] += 1

        emotion = r.get("用户情绪", "").strip()
        if emotion:
            s["情绪"][emotion] += 1
            if "正面" in emotion: s["正面"] += 1
            elif "负面" in emotion: s["负面"] += 1
            elif "混合" in emotion: s["混合"] += 1
            elif "中性" in emotion: s["中性"] += 1

        topic = r.get("话题类别", "").strip()
        if topic:
            s["话题"][topic] += 1

        relevance = r.get("相关性等级", "").strip()
        if relevance:
            s["相关性"][relevance] += 1

        value = r.get("数据价值等级", "").strip()
        if "高" in value: s["高价值"] += 1
        elif "中" in value: s["中价值"] += 1
        else: s["低价值"] += 1

    # ── 输出报告 ──
    print("=" * 70)
    print("  📊 关键词维度分析报告")
    print("=" * 70)
    print(f"  匹配成功: {len(rows) - unmatched}, 未匹配: {unmatched}")
    print()

    # 按视频数排序
    sorted_cats = sorted(cat_stats.items(), key=lambda x: x[1]["videos"], reverse=True)

    for cat, s in sorted_cats:
        print(f"┌─ {cat} ({s['videos']} 条视频) ─────────────────────┐")
        print(f"│ 互动: 👍{s['likes']:,}  💬{s['comments']:,}  ⭐{s['collects']:,}  🔄{s['shares']:,}")

        # Top 标签
        top_labels = s["标签"].most_common(5)
        label_str = "  ".join([f"{l}({c})" for l, c in top_labels])
        print(f"│ Top标签: {label_str}")

        # 情绪
        emo_str = f"正面:{s['正面']}  负面:{s['负面']}  中性:{s['中性']}  混合:{s['混合']}"
        print(f"│ 情绪: {emo_str}")

        # 价值
        print(f"│ 价值: 高:{s['高价值']}  中:{s['中价值']}  低:{s['低价值']}")

        # Top 话题
        top_topics = s["话题"].most_common(3)
        topic_str = "  ".join([f"{t}({c})" for t, c in top_topics])
        print(f"│ 话题: {topic_str}")
        print(f"└{'─'*55}┘")
        print()

    # ── 保存详细报告 CSV ──
    report_path = DATA / "维度分析报告.csv"
    with open(report_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["类别", "视频数", "点赞数", "评论数", "收藏数", "分享数",
                         "正面", "负面", "中性", "混合",
                         "高价值", "中价值", "低价值",
                         "Top标签", "Top话题"])
        for cat, s in sorted_cats:
            writer.writerow([
                cat, s["videos"], s["likes"], s["comments"], s["collects"], s["shares"],
                s["正面"], s["负面"], s["中性"], s["混合"],
                s["高价值"], s["中价值"], s["低价值"],
                "; ".join([f"{l}({c})" for l, c in s["标签"].most_common(5)]),
                "; ".join([f"{t}({c})" for t, c in s["话题"].most_common(5)]),
            ])
    print(f"📂 详细报告: {report_path}")

    # ── 高价值内容清单 ──
    high_value_path = DATA / "高价值内容.csv"
    high_rows = [r for r in rows if "高" in r.get("数据价值等级", "")]
    if high_rows:
        with open(high_value_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=high_rows[0].keys(), extrasaction='ignore')
            writer.writeheader()
            writer.writerows(high_rows)
        print(f"📂 高价值内容 ({len(high_rows)} 条): {high_value_path}")


if __name__ == "__main__":
    main()
