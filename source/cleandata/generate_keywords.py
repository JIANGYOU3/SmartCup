"""
从 AI 标签数据生成分类关键词表

用法:
  conda run -n SmartCup python source/cleandata/generate_keywords.py
  conda run -n SmartCup python source/cleandata/generate_keywords.py --top 200
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from source.common.paths import get_project_root, load_env
from source.common.excel_style import csv_to_excel

load_env()

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

DATA_DIR = get_project_root() / "res" / "data" / "douyin" / "output"
LABELED_CSV = DATA_DIR / "标签结果.csv"
KEYWORD_OUTPUT = DATA_DIR / "关键词表.csv"

# ── 已知品牌 ──
KNOWN_BRANDS = [
    "华为", "小米", "米家", "哈尔斯", "苏泊尔", "富光", "希诺", "物生物",
    "膳魔师", "Thermos", "象印", "Zojirushi", "虎牌", "Tiger",
    "Stanley", "YETI", "Ember", "麦开", "Moikit", "OHOM",
    "Nextmug", "Cauldryn", "HidrateSpark", "LARQ", "趣家",
    "智象", "乐童仔", "搜米", "乐基因", "Nalgene", "CamelBak",
    "S'well", "Contigo", "Owala", "Hydro Flask", "Klean Kanteen",
    "Brumate", "Yeti", "Tiger", "象印", "孔雀", "Peacock",
    "三好", "臻米", "摩飞", "Morphy Richards", "北鼎", "Buydeem",
    "格来德", "东菱", "小熊", "九阳", "美的", "格力",
]

# ── 功能特征词 ──
FUNCTION_FEATURES = [
    "温度显示", "测温", "温控", "恒温", "保温", "加热", "制冷",
    "提醒", "喝水提醒", "定时", "智能", "APP", "蓝牙", "WiFi",
    "杀菌", "紫外线", "UV", "消毒", "指纹", "指纹解锁",
    "触屏", "LED", "显示屏", "太阳能", "充电", "无线充",
    "便携", "折叠", "大容量", "茶水分离", "过滤",
    "发电", "自发电", "搅拌", "自动搅拌", "磁吸", "磁力",
]

# ── 场景词 ──
SCENE_WORDS = [
    "办公", "办公室", "车载", "旅行", "户外", "露营", "运动",
    "健身", "学生", "儿童", "婴儿", "母婴", "送礼物", "礼品",
    "商务", "出差", "居家", "家用", "厨房", "泡茶", "咖啡",
    "中药", "熬药", "炖煮", "宿舍", "学校", "开车", "自驾",
]

# ── 人群词 ──
CROWD_WORDS = [
    "学生", "儿童", "孩子", "宝宝", "婴儿", "宝妈", "上班族",
    "老人", "养生", "程序员", "商务人士", "户外爱好者",
    "健身达人", "咖啡爱好者", "茶友", "学生党", "打工族",
]

# ── 评价词 ──
REVIEW_WORDS = [
    "测评", "评测", "推荐", "对比", "横评", "开箱", "体验",
    "性价比", "好用", "实用", "便宜", "贵", "值得买", "避坑",
    "智商税", "踩雷", "好物", "神器", "黑科技", "天花板",
    "第一名", "最好", "最便宜", "必买", "后悔没早买",
]


def extract_keywords_from_field(text: str) -> list[str]:
    """从逗号分隔的字段提取关键词"""
    if not text:
        return []
    words = []
    # 可能是逗号、分号、或顿号分隔
    for part in re.split(r'[,，;；、\s]+', text):
        part = part.strip().strip('"\'').strip()
        if len(part) >= 2 and len(part) <= 20:
            words.append(part)
    return words


def classify_keyword(kw: str) -> str:
    """根据规则分类关键词"""
    kw_lower = kw.lower()

    # 品牌词
    for brand in KNOWN_BRANDS:
        if brand.lower() in kw_lower:
            return "品牌词"

    # 功能词
    for feat in FUNCTION_FEATURES:
        if feat in kw:
            return "功能词"

    # 场景词
    for scene in SCENE_WORDS:
        if scene in kw:
            return "场景词"

    # 人群词
    for crowd in CROWD_WORDS:
        if crowd in kw:
            return "人群词"

    # 评价词
    for review in REVIEW_WORDS:
        if review in kw:
            return "评价词"

    # 核心词（含"杯"但非品牌）
    if "杯" in kw or "水杯" in kw or "保温" in kw or "智能" in kw:
        return "核心词"

    # 长尾词
    if len(kw) >= 4:
        return "长尾词"

    return "其他"


def generate_category_summary(keywords_by_cat: dict, top_n: int = 30) -> str:
    """生成每个类别的摘要，供 AI 进一步优化"""
    lines = []
    for cat, words in keywords_by_cat.items():
        top_words = [w for w, _ in words.most_common(top_n)]
        lines.append(f"## {cat}\n" + "\n".join(f"- {w}" for w in top_words))
    return "\n\n".join(lines)


def ai_refine_keywords(keywords_by_cat: dict) -> dict:
    """用 DeepSeek 优化关键词分类，去重补漏"""
    if not API_KEY:
        return None

    summary = generate_category_summary(keywords_by_cat, 40)

    prompt = f"""你是智能水杯/保温杯市场分析专家。以下是从 766 条抖音视频标签中提取的关键词，已按规则初步分类。

请做以下优化：
1. 去掉不相关或太宽泛的词（如"不相关""其他"）
2. 补充缺失的重要品牌/功能/场景词
3. 对每个分类，选出最有搜索价值的 TOP 15 关键词
4. 添加一个"推荐搜索组合"类别，给出 10 个高效搜索词组（如"智能水杯 测评""恒温杯 推荐"等）

{summary}

返回 JSON:
{{
  "核心词": ["词1", "词2", ...],
  "品牌词": [...],
  "功能词": [...],
  "场景词": [...],
  "评价词": [...],
  "人群词": [...],
  "痛点词": [...],
  "长尾词": [...],
  "推荐搜索组合": ["组合1", "组合2", ...]
}}"""

    import requests
    try:
        resp = requests.post(API_URL, json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "你是市场分析关键词专家。返回严格JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
            "response_format": {"type": "json_object"},
        }, headers={"Authorization": f"Bearer {API_KEY}"}, timeout=60)

        if resp.status_code == 200:
            data = resp.json()
            return json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"  ⚠️ AI 优化失败: {e}")

    return None


def main():
    parser = argparse.ArgumentParser(description="生成分类关键词表")
    parser.add_argument("--top", type=int, default=200, help="每个类别保留的关键词数")
    parser.add_argument("--no-ai", action="store_true", help="跳过 AI 优化")
    args = parser.parse_args()

    print("=" * 60)
    print("📊 关键词提取 & 分类")
    print("=" * 60)

    # 1. 读取标签数据
    print(f"\n📂 读取: {LABELED_CSV}")
    with open(LABELED_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"   {len(rows)} 条视频")

    # 2. 提取关键词
    kw_counter = Counter()
    label_counter = Counter()
    pain_counter = Counter()

    for row in rows:
        # 从 AI 关键词字段
        for kw in extract_keywords_from_field(row.get("关键词", "")):
            kw_counter[kw] += 1

        # 从内容标签字段
        for lb in extract_keywords_from_field(row.get("内容标签", "")):
            label_counter[lb] += 1

        # 从需求痛点字段
        for pain in extract_keywords_from_field(row.get("需求痛点", "")):
            pain_counter[pain] += 1

    # 3. 合并所有来源，去重
    all_keywords = Counter()
    for kw, cnt in kw_counter.items():
        all_keywords[kw] += cnt * 3  # AI 关键词权重更高
    for kw, cnt in label_counter.items():
        all_keywords[kw] += cnt * 2
    for kw, cnt in pain_counter.items():
        all_keywords[kw] += cnt

    print(f"\n📊 原始关键词: {len(kw_counter)} 个 (AI标签)")
    print(f"   内容标签: {len(label_counter)} 个")
    print(f"   需求痛点: {len(pain_counter)} 个")
    print(f"   合并去重: {len(all_keywords)} 个")

    # 4. 分类
    keywords_by_cat = defaultdict(Counter)
    for kw, cnt in all_keywords.items():
        if cnt < 2:  # 过滤仅出现1次的
            continue
        cat = classify_keyword(kw)
        keywords_by_cat[cat][kw] = cnt

    # 5. AI 优化（可选）
    if not args.no_ai and API_KEY:
        print(f"\n🤖 AI 优化分类...")
        refined = ai_refine_keywords(keywords_by_cat)
        if refined:
            print("   ✅ AI 优化完成")
            # 使用 AI 结果
            final_keywords = refined
        else:
            final_keywords = {cat: [w for w, _ in words.most_common(args.top)]
                              for cat, words in keywords_by_cat.items()}
    else:
        final_keywords = {cat: [w for w, _ in words.most_common(args.top)]
                          for cat, words in keywords_by_cat.items()}

    # 6. 输出 CSV
    print(f"\n📊 生成关键词表...")

    # 确定所有类别
    all_cats = ["核心词", "品牌词", "功能词", "场景词", "评价词", "人群词", "痛点词", "长尾词", "推荐搜索组合"]

    max_len = max((len(v) for v in final_keywords.values() if isinstance(v, list)), default=0)

    with open(KEYWORD_OUTPUT, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(all_cats)

        for i in range(max_len):
            row = []
            for cat in all_cats:
                items = final_keywords.get(cat, [])
                if isinstance(items, list) and i < len(items):
                    row.append(items[i])
                else:
                    row.append("")
            writer.writerow(row)

    print(f"   📂 {KEYWORD_OUTPUT}")

    # 7. Excel
    try:
        excel_path = csv_to_excel(
            KEYWORD_OUTPUT,
            sheet_title="关键词分类表",
            column_widths={cat: 30 for cat in all_cats},
        )
        print(f"   📂 {excel_path}")
    except Exception as e:
        print(f"   ⚠️ Excel: {e}")

    # 8. 打印摘要
    print(f"\n{'='*60}")
    print("📋 关键词分类摘要")
    print(f"{'='*60}")

    for cat in all_cats:
        items = final_keywords.get(cat, [])
        if isinstance(items, list) and items:
            print(f"\n🏷️ {cat} ({len(items)} 个):")
            print(f"   {', '.join(items[:15])}")
        elif isinstance(items, str):
            print(f"\n🏷️ {cat}: {items[:100]}")

    print(f"\n{'='*60}")
    print("✅ 关键词表生成完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
