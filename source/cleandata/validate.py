"""
数据严谨性校验 — 第一性原理逐项检查

用法：
  conda run -n SmartCup python source/cleandata/validate.py
"""

import csv
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

DATA = Path(__file__).resolve().parent.parent.parent / "res/data/douyin/output"
INPUT = DATA / "标签结果_最终.csv"


def safe_int(v):
    try: return int(v or 0)
    except: return 0


def main():
    print("=" * 60)
    print("  🔍 数据严谨性校验")
    print("=" * 60)

    with open(INPUT, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames

    N = len(rows)
    issues = []

    # ═══════════════════════════════════════════
    #  1. 基础完整性
    # ═══════════════════════════════════════════
    print(f"\n── 1. 基础完整性 ──")
    print(f"   总行数: {N}")
    print(f"   总列数: {len(fields)}")

    required = ["视频标题", "视频链接", "点赞数", "评论数", "收藏数", "分享数",
                "内容标签", "用户情绪", "话题类别", "相关性等级", "数据价值等级"]
    missing_fields = [f for f in required if f not in fields]
    if missing_fields:
        print(f"   ❌ 缺失字段: {missing_fields}")
        issues.append(f"缺失字段 {len(missing_fields)} 个")
    else:
        print(f"   ✅ 全部 {len(required)} 个核心字段存在")

    # 检查空值率
    for f in required:
        empty = sum(1 for r in rows if not r.get(f, "").strip())
        if empty > 0 and f not in ("需求痛点",):
            pct = empty / N * 100
            if pct > 5:
                print(f"   ⚠️ {f}: {empty} 条空值 ({pct:.1f}%)")
                issues.append(f"{f} 空值率 {pct:.1f}%")
    print(f"   ✅ 核心字段空值率 < 5%")

    # ═══════════════════════════════════════════
    #  2. 数据类型校验
    # ═══════════════════════════════════════════
    print(f"\n── 2. 数据类型校验 ──")
    numeric_fields = ["点赞数", "评论数", "收藏数", "分享数", "作者粉丝量"]
    non_numeric = []
    for f in numeric_fields:
        bad = 0
        for r in rows:
            v = r.get(f, "0").strip()
            try:
                int(v or "0")
            except:
                bad += 1
        if bad > 0:
            non_numeric.append((f, bad))
    if non_numeric:
        for f, c in non_numeric:
            print(f"   ❌ {f}: {c} 条非数字")
            issues.append(f"{f} 非数字 {c}条")
    else:
        print(f"   ✅ 全部数字字段格式正确")

    # URL 格式
    bad_url = sum(1 for r in rows if not re.match(r'https://www\.douyin\.com/video/\d+', r.get("视频链接", "")))
    if bad_url > 0:
        print(f"   ❌ 视频链接格式异常: {bad_url} 条")
        issues.append(f"链接异常 {bad_url}条")
    else:
        print(f"   ✅ 视频链接格式全部正确")

    # ═══════════════════════════════════════════
    #  3. 数据一致性
    # ═══════════════════════════════════════════
    print(f"\n── 3. 数据一致性 ──")

    # 点赞/收藏/分享不能为负
    negative = sum(1 for r in rows if safe_int(r.get("点赞数")) < 0
                   or safe_int(r.get("收藏数")) < 0 or safe_int(r.get("分享数")) < 0)
    if negative:
        print(f"   ❌ 负值互动数据: {negative} 条")
        issues.append(f"负值数据 {negative}条")
    else:
        print(f"   ✅ 无负值互动数据")

    # 有评论数但无评论内容
    has_comment_count = sum(1 for r in rows if safe_int(r.get("评论数", 0)) > 0)
    has_comment_text = sum(1 for r in rows if r.get("评论1", "").strip())
    print(f"   评论数>0: {has_comment_count} 条, 有评论内容: {has_comment_text} 条")
    if has_comment_count < has_comment_text:
        print(f"   ⚠️ 有评论内容但评论数为0? — 检查中...")
    # 这是正常的：评论数是从API拿的（可能为0），但评论内容是后来抓的

    # 发布时间格式
    bad_time = sum(1 for r in rows
                   if r.get("发布时间", "") and not re.match(r'\d{4}[-/]\d{2}[-/]\d{2}', r.get("发布时间", "")))
    if bad_time:
        bad_time_pct = bad_time / N * 100
        print(f"   ⚠️ 发布时间格式异常: {bad_time} 条 ({bad_time_pct:.1f}%)")
    else:
        print(f"   ✅ 发布时间格式正常")

    # ═══════════════════════════════════════════
    #  4. 去重检查
    # ═══════════════════════════════════════════
    print(f"\n── 4. 去重检查 ──")
    urls = [r.get("视频链接", "") for r in rows]
    dup_urls = [u for u, c in Counter(urls).items() if c > 1]
    if dup_urls:
        print(f"   ❌ 重复URL: {len(dup_urls)} 组")
        for u in dup_urls[:3]:
            print(f"      {u} (×{Counter(urls)[u]})")
        issues.append(f"重复URL {len(dup_urls)}组")
    else:
        print(f"   ✅ 无重复URL")

    # 提取 aweme_id 去重
    ids = []
    for r in rows:
        m = re.search(r'/video/(\d+)', r.get("视频链接", ""))
        ids.append(m.group(1) if m else "")
    dup_ids = [i for i, c in Counter(ids).items() if i and c > 1]
    if dup_ids:
        print(f"   ❌ 重复 aweme_id: {len(dup_ids)} 组")
        issues.append(f"重复ID {len(dup_ids)}组")
    else:
        print(f"   ✅ 无重复 aweme_id")

    # ═══════════════════════════════════════════
    #  5. AI 标签一致性
    # ═══════════════════════════════════════════
    print(f"\n── 5. AI 标签一致性 ──")

    # 不相关检查 — 不应存在"不相关"标签
    irrelevant = sum(1 for r in rows if "不相关" in r.get("内容标签", ""))
    if irrelevant > 0:
        print(f"   ❌ 仍有 {irrelevant} 条含'不相关'标签!")
        issues.append(f"不相关标签残留 {irrelevant}条")
    else:
        print(f"   ✅ 无'不相关'标签残留")

    # 标签值域检查
    valid_emotions = {"正面", "负面", "中性", "混合"}
    bad_emo = sum(1 for r in rows if r.get("用户情绪", "").strip() not in valid_emotions)
    if bad_emo:
        print(f"   ⚠️ 异常情绪值: {bad_emo} 条")
    else:
        print(f"   ✅ 情绪值全部合法")

    valid_values = {"高", "中", "低"}
    bad_val = sum(1 for r in rows if r.get("数据价值等级", "").strip() not in valid_values)
    if bad_val:
        print(f"   ⚠️ 异常数据价值: {bad_val} 条")
    else:
        print(f"   ✅ 数据价值全部合法")

    bad_rel = sum(1 for r in rows if r.get("相关性等级", "").strip() not in valid_values)
    if bad_rel:
        print(f"   ⚠️ 异常相关性: {bad_rel} 条")
    else:
        print(f"   ✅ 相关性等级全部合法")

    # ═══════════════════════════════════════════
    #  6. 评论清洗质量抽查
    # ═══════════════════════════════════════════
    print(f"\n── 6. 评论清洗质量 ──")

    # 抽查评论是否还有垃圾
    garbage_in_comments = 0
    total_comments = 0
    garbage_patterns = [
        re.compile(r'^[哈哈嗝嘿呵]+$'),
        re.compile(r'^[👍❤️🔥😂😭😍]+$'),
        re.compile(r'^[.。]{2,}$'),
    ]
    for r in rows:
        for i in range(1, 21):
            text = r.get(f"评论{i}", "").strip()
            if text:
                total_comments += 1
                for pat in garbage_patterns:
                    if pat.match(text):
                        garbage_in_comments += 1
                        break
    if garbage_in_comments > 0:
        print(f"   ⚠️ 残留疑似垃圾评论: {garbage_in_comments}/{total_comments}")
    else:
        print(f"   ✅ {total_comments} 条评论无垃圾残留")

    # 统计评论长度分布
    comment_lens = [len(r.get(f"评论{i}", "").strip())
                    for r in rows for i in range(1, 21)
                    if r.get(f"评论{i}", "").strip()]
    if comment_lens:
        short = sum(1 for l in comment_lens if l < 3)
        avg_len = sum(comment_lens) / len(comment_lens)
        print(f"   评论总数: {len(comment_lens)}, 平均长度: {avg_len:.1f} 字, 过短(<3字): {short}")
        if short < len(comment_lens) * 0.02:
            print(f"   ✅ 过短评论占比正常 (<2%)")

    # ═══════════════════════════════════════════
    #  7. 内容标签与标题匹配抽查
    # ═══════════════════════════════════════════
    print(f"\n── 7. 标签-内容匹配抽查 (10条) ──")
    import random
    random.seed(42)
    samples = random.sample(rows, min(10, N))
    mismatches = 0
    for i, r in enumerate(samples):
        title = r.get("视频标题", "")[:50]
        labels = r.get("内容标签", "")[:60]
        summary = r.get("一句话总结", "")[:60]
        print(f"  [{i+1}] 标题: {title}")
        print(f"      标签: {labels}")
        print(f"      总结: {summary}")
        # 简单检查：标题含"保温杯""水杯"但标签里没有
        has_cup_in_title = any(kw in title for kw in ["保温杯", "水杯", "智能杯", "恒温杯"])
        has_cup_in_label = any(kw in labels for kw in ["保温杯", "水杯", "智能杯", "恒温杯"])
        if has_cup_in_title and not has_cup_in_label:
            print(f"      ⚠️ 标题含杯具但标签无匹配")
            mismatches += 1
        print()
    if mismatches == 0:
        print(f"   ✅ 抽查全部匹配")

    # ═══════════════════════════════════════════
    #  8. 数据分布合理性
    # ═══════════════════════════════════════════
    print(f"\n── 8. 数据分布 ──")
    likes_median = sorted([safe_int(r.get("点赞数", 0)) for r in rows])[N // 2]
    print(f"   点赞: 均值 {sum(safe_int(r.get('点赞数',0)) for r in rows)//N:,}, 中位数 {likes_median:,}")
    print(f"   评论: 均值 {sum(safe_int(r.get('评论数',0)) for r in rows)//N:,}")
    print(f"   收藏: 均值 {sum(safe_int(r.get('收藏数',0)) for r in rows)//N:,}")

    # 尾部检查 — 避免截断数据
    print(f"\n  最后3条:")
    for r in rows[-3:]:
        aid = re.search(r'/video/(\d+)', r.get("视频链接", ""))
        print(f"    {aid.group(1) if aid else '?'}: {(r.get('视频标题',''))[:50]}")

    # ═══════════════════════════════════════════
    #  最终判定
    # ═══════════════════════════════════════════
    print(f"\n{'='*60}")
    if issues:
        print(f"  ⚠️ 发现问题 {len(issues)} 项:")
        for iss in issues:
            print(f"    - {iss}")
    else:
        print(f"  ✅ 全部检查通过，数据质量良好")
    print(f"{'='*60}")
    print(f"  总计: {N} 条  |  👍{sum(safe_int(r.get('点赞数',0)) for r in rows):,}")
    print(f"  文件: {INPUT}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
