"""
抖音数据深度清洗 v2 — 过滤无关视频 + 深度清洗评论

用法：
  conda run -n SmartCup python source/cleandata/clean_douyin_v2.py
  conda run -n SmartCup python source/cleandata/clean_douyin_v2.py --dry-run
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from source.common.excel_style import csv_to_excel

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "res/data/douyin/output"
DEFAULT_INPUT = DATA_DIR / "标签结果_清洗后.csv"
DEFAULT_OUTPUT = DATA_DIR / "标签结果_最终.csv"

# ══════════════════════════════════════════════════════════
#  杯具相关标签（至少命中一个才保留）
# ══════════════════════════════════════════════════════════
CUP_RELATED_LABELS = {
    # 核心产品
    "智能水杯/温控杯", "普通保温杯/水杯", "保温杯推荐/导购",
    "电热水杯/加热杯", "茶水分离杯", "儿童保温杯",
    "便携恒温杯", "55度杯", "指纹水杯", "恒温杯",

    # 品牌
    "米家/小米水杯", "华为/鸿蒙水杯", "哈尔斯", "膳魔师/Thermos",
    "富光", "象印/Zojirushi", "苏泊尔", "虎牌/Tiger",
    "乐童仔指纹锁保温杯", "小白熊恒温杯", "Stanley", "YETI",
    "物生物", "希诺", "摩飞",

    # 其他杯具相关
    "品牌对比/横评", "其他杯具相关", "创意/趣味杯具",
    "智能家居相关", "母婴好物", "开箱", "测评",
}

# ══════════════════════════════════════════════════════════
#  增强评论清洗
# ══════════════════════════════════════════════════════════
USELESS_PATTERNS = [
    re.compile(r'^[哈哈嗝嘿呵嘻嗬呵诶咦呜噗嗷嗯哦唉哎切啧哼啊]+$'),  # 纯语气词
    re.compile(r'^[\U0001F000-\U0001FFFF☀-➿⭐❤\U0001F300-\U0001F6FF\U0001F900-\U0001F9FF]+$'),  # 纯emoji
    re.compile(r'^@\S+\s*$'),                        # 仅 @某人
    re.compile(r'^[,.，。！？!?…~～、\s]+$'),           # 纯标点
    re.compile(r'^[0-9\s\.]+$'),                     # 纯数字/空格
    re.compile(r'^[👍❤️🔥😂😭😍💕🤣😅🙏💪🎉😊🥰💔😁✨️🌟💗💖💞👏😡🤩🥺🎊🎂🍀✅💯💢💤🎵🎶💬➡️⬆️⬇️↗️↙️]+$'),  # 纯表情符号
    re.compile(r'^http[s]?://\S+$'),                 # 纯链接
    re.compile(r'^[a-zA-Z\s]{1,5}$'),                # 1-5个纯英文字母
    re.compile(r'^(.)\1{4,}$'),                      # 同一字符重复5次+（如"。。。。。""啊啊啊啊啊"）
    re.compile(r'^[?？]{2,}$'),                       # 纯问号
    re.compile(r'^[.。]{2,}$'),                       # 纯句号
]

# 部分清洗：去掉 @提及、多余空白，但保留正文
AT_CLEAN = re.compile(r'@\S+\s*')
WHITESPACE_CLEAN = re.compile(r'\s+')
TRAILING_SYMBOLS = re.compile(r'^[，,。！？!?…~～、\s]+|[，,。！？!?…~～、\s]+$')


def is_useless_comment(text: str) -> bool:
    """判断评论是否完全无效"""
    if not text or not text.strip():
        return True
    t = text.strip()
    if len(t) < 2:
        return True
    # 去 @后为空
    cleaned = AT_CLEAN.sub('', t).strip()
    if not cleaned or len(cleaned) < 2:
        return True
    # 匹配无效模式
    for pat in USELESS_PATTERNS:
        if pat.match(t) or pat.match(cleaned):
            return True
    # 全是重复字符（去空白后）
    chars = set(cleaned.replace(' ', ''))
    if len(chars) <= 1 and len(cleaned) >= 3:
        return True
    return False


def clean_comment_text(text: str) -> str:
    """清洗单条评论，保留有价值内容"""
    t = text.strip()
    # 去 @提及
    t = AT_CLEAN.sub('', t).strip()
    # 去首尾标点
    t = TRAILING_SYMBOLS.sub('', t).strip()
    # 合并空白
    t = WHITESPACE_CLEAN.sub(' ', t).strip()
    return t


# 杯具相关关键词（模糊匹配，仅保留杯具专属词，避免 "测评""开箱" 泛匹配）
CUP_KEYWORDS = [
    "智能水杯", "温控杯", "保温杯", "恒温杯", "电热水杯", "加热杯",
    "烧水杯", "茶水分离", "55度杯", "指纹水杯", "指纹杯",
    "儿童水杯", "儿童保温杯", "便携恒温", "降温杯", "车载杯",
    "焖烧杯", "磁吸杯", "茶仓杯", "星芒杯",
    # 品牌
    "米家", "小米水杯", "华为", "鸿蒙", "哈尔斯", "膳魔师", "Thermos",
    "富光", "象印", "Zojirushi", "苏泊尔", "虎牌", "Tiger",
    "Stanley", "YETI", "物生物", "希诺", "摩飞", "趣家",
    "乐童仔", "小白熊", "bololo", "HidrateSpark",
    # 杯具专属
    "水杯", "保温杯", "杯具", "杯测评", "杯推荐", "杯对比", "杯横评",
    "杯子", "喝水", "恒温壶", "温度显示",
]


def video_has_cup_label(labels_raw: str) -> bool:
    """检查视频标签是否与杯具相关（模糊匹配）"""
    if not labels_raw:
        return False
    for label in labels_raw.replace('，', ',').split(','):
        label = label.strip().strip('[]\'\" ')
        if not label:
            continue
        # 精确匹配
        if label in CUP_RELATED_LABELS:
            return True
        # 模糊匹配
        for kw in CUP_KEYWORDS:
            if kw in label:
                return True
    return False


def main():
    parser = argparse.ArgumentParser(description="抖音数据深度清洗 v2")
    parser.add_argument("--input", "-i", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", "-o", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # ── 读取 ──
    with open(args.input, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    print(f"📂 读取: {len(rows)} 条")
    stats = Counter()
    stats["输入"] = len(rows)

    kept = []
    comments_before = 0
    comments_after = 0
    comment_removed = 0

    for r in rows:
        # ── 1. 过滤无关视频 ──
        raw_labels = r.get("内容标签", "")
        # AI 判定为"不相关"的一律删除（即使碰巧有关键词匹配）
        if "不相关" in raw_labels:
            stats["过滤-AI判定不相关"] += 1
            continue
        if not video_has_cup_label(raw_labels):
            stats["过滤-无关视频"] += 1
            continue

        # ── 2. 深度清洗评论 ──
        for i in range(1, 21):
            text_key = f"评论{i}"
            text = r.get(text_key, "").strip()
            if text:
                comments_before += 1
                if is_useless_comment(text):
                    # 清除该评论及所有关联列
                    for suffix in [f"评论{i}", f"评论{i}点赞", f"评论{i}回复数",
                                   f"评论{i}用户", f"评论{i}时间", f"评论{i}属地",
                                   f"评论{i}子回复1", f"评论{i}子回复1用户", f"评论{i}子回复1点赞",
                                   f"评论{i}子回复2", f"评论{i}子回复2用户", f"评论{i}子回复2点赞",
                                   f"评论{i}子回复3", f"评论{i}子回复3用户", f"评论{i}子回复3点赞"]:
                        if suffix in r:
                            r[suffix] = ""
                    comment_removed += 1
                else:
                    # 清洗评论文本
                    r[text_key] = clean_comment_text(text)
                    comments_after += 1

                # 同样清洗子回复
                for j in range(1, 4):
                    sr_key = f"评论{i}子回复{j}"
                    sr_text = r.get(sr_key, "").strip()
                    if sr_text:
                        if is_useless_comment(sr_text):
                            r[sr_key] = ""
                            r[f"评论{i}子回复{j}用户"] = ""
                            r[f"评论{i}子回复{j}点赞"] = ""
                        else:
                            r[sr_key] = clean_comment_text(sr_text)

        kept.append(r)

    stats["保留"] = len(kept)
    stats["移除"] = stats["输入"] - stats["保留"]

    # ── 报告 ──
    print(f"\n{'='*55}")
    print(f"  🧹 深度清洗报告")
    print(f"{'='*55}")
    print(f"  视频: {stats['输入']:,} → {stats['保留']:,} (移除 {stats['移除']:,}, {stats['移除']/max(stats['输入'],1)*100:.1f}%)")
    print(f"  其中过滤无关视频: {stats.get('过滤-无关视频', 0):,} 条")
    print(f"  评论: {comments_before:,} → {comments_after:,} 条有效 (移除 {comment_removed:,} 条无效)")
    if comments_before > 0:
        print(f"  评论有效率: {comments_after/max(comments_before,1)*100:.1f}%")
    print(f"{'='*55}")

    if args.dry_run:
        print("\n⚠️ Dry-run 模式，未写入文件")
        return

    # ── 输出 ──
    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(kept)

    print(f"\n📂 输出: {args.output}")

    # Excel
    try:
        excel_path = csv_to_excel(
            Path(args.output),
            sheet_title="抖音标签结果(最终)",
            column_widths={"视频标题": 45, "视频文案": 55, "视频链接": 35,
                          "作者昵称": 14, "需求痛点": 40, "一句话总结": 40},
            link_columns={"视频链接"},
        )
        print(f"📂 Excel: {excel_path}")
    except Exception as e:
        print(f"⚠️ Excel 失败: {e}")


if __name__ == "__main__":
    main()
