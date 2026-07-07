"""
抖音数据清洗 + DeepSeek AI 多维标签分类

流程：
  1. 合并多轮爬取 CSV
  2. 清洗无效评论（哈哈哈/纯表情/@无内容/短评论）
  3. DeepSeek API 批量打标签（内容标签/相关性/话题/情绪/痛点/数据价值）
  4. 输出结构化 CSV + Excel

用法：
  conda run -n SmartCup python -u source/cleandata/douyin_labeler.py
  conda run -n SmartCup python -u source/cleandata/douyin_labeler.py --workers 8 --resume
  conda run -n SmartCup python -u source/cleandata/douyin_labeler.py --dry-run
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

import requests
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from source.common.paths import get_project_root, load_env
from source.common.excel_style import csv_to_excel

load_env()

# ── 配置 ──────────────────────────────────────────

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"
DEFAULT_WORKERS = 6
SAVE_INTERVAL = 20

# ── 输入输出 ───────────────────────────────────────

DATA_DIR = get_project_root() / "res" / "data" / "douyin"
OUTPUT_DIR = DATA_DIR / "output"

# 自动查找所有爬取结果 CSV
def find_crawl_csvs():
    """找到所有爬取结果 CSV"""
    csvs = sorted(OUTPUT_DIR.glob("爬取结果_*.csv"))
    return csvs

MERGED_CSV = OUTPUT_DIR / "爬取结果_合并.csv"
CLEANED_CSV = OUTPUT_DIR / "爬取结果_清洗后.csv"
LABELED_CSV = OUTPUT_DIR / "标签结果.csv"
PROGRESS_FILE = OUTPUT_DIR / "douyin_labeler_progress.json"


# ── 评论清洗 ───────────────────────────────────────

# 无效评论模式
USELESS_PATTERNS = [
    re.compile(r'^[哈哈嗝嘿呵嘻嗬]+$'),           # 纯哈类
    re.compile(r'^[\U0001F000-\U0001FFFF\U0001F300-\U0001F6FF\U0001F900-\U0001F9FF]+$'),  # 纯emoji
    re.compile(r'^@\S+\s*$'),                     # 仅 @某人
    re.compile(r'^[,.，。！？!?…~～\s]+$'),         # 纯标点
    re.compile(r'^[0-9\s]+$'),                    # 纯数字
    re.compile(r'^[👍❤️🔥😂😭😍💕🤣😅🙏💪🎉😊🥰💔😁✨️🌟]+$'),  # 纯表情符号
]

def is_useless_comment(text: str) -> bool:
    """判断评论是否无效"""
    if not text or not text.strip():
        return True
    t = text.strip()
    if len(t) < 2:
        return True
    for pat in USELESS_PATTERNS:
        if pat.match(t):
            return True
    # 全是重复字符
    if len(set(t)) <= 2 and len(t) > 1:
        return True
    return False


def clean_comment(text: str) -> str:
    """清洗单条评论"""
    t = text.strip()
    # 去除纯 @提及
    t = re.sub(r'@\S+\s*', '', t).strip()
    # 去除过多空白
    t = re.sub(r'\s+', ' ', t).strip()
    return t


# ── 数据处理 ───────────────────────────────────────

def merge_crawls():
    """合并所有爬取 CSV"""
    csvs = find_crawl_csvs()
    if not csvs:
        print("❌ 未找到爬取结果 CSV")
        return None

    seen_urls = set()
    all_rows = []

    for csv_path in csvs:
        try:
            with open(csv_path, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get("视频链接", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_rows.append(row)
        except Exception as e:
            print(f"  ⚠️ 读取 {csv_path.name} 失败: {e}")

    # 写合并文件
    if all_rows:
        fieldnames = list(all_rows[0].keys())
        with open(MERGED_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_rows)

    print(f"📂 合并: {len(csvs)} 个文件 → {len(all_rows)} 条（去重）")
    return all_rows


def clean_data(rows):
    """清洗数据：去无效评论、补充字段"""
    cleaned = []
    removed_comments = 0
    total_comments = 0

    for row in rows:
        # 清洗每条评论
        for i in range(1, 21):  # 评论1~20
            text_key = f"评论{i}"
            text = row.get(text_key, "").strip()
            if text:
                total_comments += 1
                if is_useless_comment(text):
                    # 清除这条评论及关联字段
                    for suffix in [f"评论{i}", f"评论{i}点赞", f"评论{i}回复数",
                                   f"评论{i}用户", f"评论{i}时间", f"评论{i}属地",
                                   f"评论{i}子回复1", f"评论{i}子回复1用户", f"评论{i}子回复1点赞",
                                   f"评论{i}子回复2", f"评论{i}子回复2用户", f"评论{i}子回复2点赞",
                                   f"评论{i}子回复3", f"评论{i}子回复3用户", f"评论{i}子回复3点赞"]:
                        if suffix in row:
                            row[suffix] = ""
                    removed_comments += 1
                else:
                    row[text_key] = clean_comment(text)

        # 补充内容文本（合并标题+文案，供 AI 分析用）
        title = row.get("视频标题", "")
        desc = row.get("视频文案", "")
        row["完整文本"] = f"{title}\n{desc}".strip()

        cleaned.append(row)

    print(f"🧹 清洗: 移除 {removed_comments}/{total_comments} 条无效评论 ({removed_comments/total_comments*100:.1f}%)" if total_comments else "🧹 清洗完成")

    # 写清洗后文件
    if cleaned:
        fieldnames = list(cleaned[0].keys())
        with open(CLEANED_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(cleaned)

    return cleaned


# ── AI 标签分类 ────────────────────────────────────

SYSTEM_PROMPT = """你是智能水杯/保温杯市场分析专家。你需要分析抖音视频数据，提取以下维度的标签。

## 输出要求
返回严格 JSON 格式（不要 markdown 代码块）:
{
  "内容标签": ["标签1", "标签2"],
  "内容相关性": {"等级": "高/中/低", "理由": "一句话说明"},
  "话题类别": "测评/开箱/教程/对比/广告/娱乐/资讯/其他",
  "用户情绪": "正面/负面/中性/混合",
  "需求痛点": ["用户提到的具体需求或痛点"],
  "数据价值": {"等级": "高/中/低", "理由": "基于互动量和内容质量的一句话评价"},
  "关键词": ["提取3-5个关键词"],
  "一句话总结": "20字内概括"
}

## 维度说明

### 内容标签（可多选）
- 智能水杯/温控杯：智能控温、恒温、调温功能
- 电热水杯/加热杯：便携/车载电热水杯、55度杯
- Ember温控杯：Ember品牌温控马克杯
- 其他国际智能品牌：OHOM/Nextmug/Cauldryn/HidrateSpark/LARQ
- 麦开/Moikit
- 米家/小米水杯：小米、米家生态
- 华为/鸿蒙水杯：华为智选、鸿蒙智联
- 哈尔斯
- 苏泊尔
- 富光
- 希诺
- 物生物
- 膳魔师/Thermos
- 象印/Zojirushi
- 虎牌/Tiger
- Stanley
- YETI
- 品牌对比/横评
- 保温杯推荐/导购
- 普通保温杯/水杯
- 其他杯具相关
- 创意/趣味杯具：DIY、搞怪、创意设计
- 智能家居相关：非水杯但相关智能家居
- 不相关

### 话题类别
- 测评：评测、体验分享
- 开箱：开箱展示
- 教程：使用教程、DIY教程
- 对比：品牌/产品对比
- 广告：品牌营销、带货
- 娱乐：搞笑、剧情、音乐
- 资讯：新闻、行业动态
- 其他

### 用户情绪
- 正面：评论区整体积极、认可、想买
- 负面：吐槽、不满、质疑
- 中性：客观讨论
- 混合：正负面都有

### 需求痛点
从评论和内容中提取用户真实需求或痛点，如"想要温度显示""保温效果不好""价格太贵"

### 数据价值
- 高：内容深度好、互动高、评论有洞察
- 中：有一定价值
- 低：内容浅、互动少、无实质信息
"""


def build_user_prompt(row: dict) -> str:
    """构建发送给 AI 的用户提示"""
    title = row.get("视频标题", "")[:200]
    desc = row.get("视频文案", "")[:300]
    author = row.get("作者昵称", "")
    followers = row.get("作者粉丝量", "0")
    likes = row.get("点赞数", "0")
    comments_cnt = row.get("评论数", "0")
    collects = row.get("收藏数", "0")
    shares = row.get("分享数", "0")

    # 收集有效评论
    valid_comments = []
    for i in range(1, 21):
        text = row.get(f"评论{i}", "").strip()
        if text and not is_useless_comment(text):
            like = row.get(f"评论{i}点赞", "0")
            reply = row.get(f"评论{i}回复数", "0")
            valid_comments.append(f"  [{i}] 👍{like} 💬{reply} {text[:120]}")

    comments_text = "\n".join(valid_comments[:10]) if valid_comments else "（无有效评论）"

    prompt = f"""## 视频信息
标题: {title}
文案: {desc}
作者: {author} | 粉丝: {followers}
数据: 👍{likes} 💬{comments_cnt} ⭐{collects} 🔄{shares}

## 评论（前10条有效评论）
{comments_text}

请分析以上数据，返回 JSON。"""
    return prompt


class DeepSeekLabeler:
    """DeepSeek API 客户端"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or API_KEY
        if not self.api_key:
            raise ValueError("未设置 DEEPSEEK_API_KEY")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def label_one(self, row: dict, retries: int = 3) -> dict:
        """对单条视频打标签"""
        user_prompt = build_user_prompt(row)

        for attempt in range(retries):
            try:
                resp = self.session.post(API_URL, json={
                    "model": MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1024,
                    "response_format": {"type": "json_object"},
                }, timeout=60)

                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return json.loads(content)
                elif resp.status_code == 429:
                    time.sleep(2 ** attempt)
                else:
                    time.sleep(1)
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return {"error": str(e), "内容标签": ["API失败"]}

        return {"内容标签": ["API重试耗尽"]}


def load_progress():
    """加载已有进度"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_progress(results: dict):
    """保存进度"""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(results, f, ensure_ascii=False)


def label_all(rows: list[dict], workers: int = 6, resume: bool = True):
    """批量 AI 打标签"""
    labeler = DeepSeekLabeler()
    progress = load_progress() if resume else {}
    results = {}  # url -> label_result

    # 加载已有
    if progress:
        results.update(progress)
        print(f"📌 断点续跑: 已处理 {len(results)} 条")

    # 需要处理的
    pending = [(i, row) for i, row in enumerate(rows)
               if row.get("视频链接", "") not in results]

    if not pending:
        print("✅ 全部已处理")
        return [results.get(r.get("视频链接", ""), {}) for r in rows]

    print(f"🎯 待处理: {len(pending)} 条, {workers} 并发\n")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for idx, row in pending:
            fut = executor.submit(labeler.label_one, row)
            futures[fut] = (idx, row)

        completed = len(results)
        with tqdm(total=len(pending), desc="AI 打标签", unit="条") as pbar:
            for fut in as_completed(futures):
                idx, row = futures[fut]
                try:
                    result = fut.result()
                except Exception as e:
                    result = {"error": str(e), "内容标签": ["异常"]}

                url = row.get("视频链接", "")
                results[url] = result
                completed += 1

                # 每 N 条保存
                if completed % SAVE_INTERVAL == 0:
                    save_progress(results)

                pbar.update(1)

    # 最终保存
    save_progress(results)

    # 按原始顺序输出
    ordered = [results.get(r.get("视频链接", ""), {}) for r in rows]
    return ordered


def build_output(rows, label_results):
    """合并原始数据 + AI 标签，输出最终 CSV"""
    output_rows = []
    for row, labels in zip(rows, label_results):
        if not labels:
            labels = {}

        new_row = {}

        # 核心字段
        for k in ["视频标题", "视频文案", "作者昵称", "作者粉丝量", "点赞数",
                   "评论数", "收藏数", "分享数", "发布时间", "视频链接"]:
            new_row[k] = row.get(k, "")

        # AI 标签字段
        content_labels = labels.get("内容标签", [])
        new_row["内容标签"] = ", ".join(content_labels) if isinstance(content_labels, list) else str(content_labels)

        relevance = labels.get("内容相关性", {})
        if isinstance(relevance, dict):
            new_row["相关性等级"] = relevance.get("等级", "")
            new_row["相关性理由"] = relevance.get("理由", "")
        else:
            new_row["相关性等级"] = ""
            new_row["相关性理由"] = ""

        new_row["话题类别"] = labels.get("话题类别", "")
        new_row["用户情绪"] = labels.get("用户情绪", "")

        pain_points = labels.get("需求痛点", [])
        new_row["需求痛点"] = "; ".join(pain_points) if isinstance(pain_points, list) else str(pain_points)

        data_value = labels.get("数据价值", {})
        if isinstance(data_value, dict):
            new_row["数据价值等级"] = data_value.get("等级", "")
            new_row["数据价值理由"] = data_value.get("理由", "")
        else:
            new_row["数据价值等级"] = ""
            new_row["数据价值理由"] = ""

        keywords = labels.get("关键词", [])
        new_row["关键词"] = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)

        new_row["一句话总结"] = labels.get("一句话总结", "")
        new_row["AI原始JSON"] = json.dumps(labels, ensure_ascii=False)

        # 保留前5条清洗后的评论
        for i in range(1, 6):
            for sfx in [f"评论{i}", f"评论{i}点赞", f"评论{i}回复数", f"评论{i}用户"]:
                new_row[sfx] = row.get(sfx, "")

        output_rows.append(new_row)

    return output_rows


def print_summary(output_rows):
    """打印汇总统计"""
    print(f"\n{'='*60}")
    print("📊 标签分布统计")
    print(f"{'='*60}")

    # 内容标签
    label_counter = Counter()
    topic_counter = Counter()
    sentiment_counter = Counter()
    relevance_counter = Counter()
    value_counter = Counter()

    for r in output_rows:
        for lb in r.get("内容标签", "").split(", "):
            if lb.strip():
                label_counter[lb.strip()] += 1
        topic_counter[r.get("话题类别", "未知")] += 1
        sentiment_counter[r.get("用户情绪", "未知")] += 1
        relevance_counter[r.get("相关性等级", "未知")] += 1
        value_counter[r.get("数据价值等级", "未知")] += 1

    print(f"\n🏷️ 内容标签 Top 15:")
    for label, count in label_counter.most_common(15):
        print(f"  {label}: {count}")

    print(f"\n📂 话题类别:")
    for t, c in topic_counter.most_common():
        print(f"  {t}: {c}")

    print(f"\n😊 用户情绪:")
    for s, c in sentiment_counter.most_common():
        print(f"  {s}: {c}")

    print(f"\n🎯 相关性:")
    for r, c in relevance_counter.most_common():
        print(f"  {r}: {c}")

    print(f"\n💎 数据价值:")
    for v, c in value_counter.most_common():
        print(f"  {v}: {c}")


# ── 主流程 ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="抖音数据清洗 + AI 标签分类")
    parser.add_argument("--workers", "-w", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--resume", action="store_true", default=True)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="不调API，仅合并+清洗")
    args = parser.parse_args()

    if args.no_resume:
        args.resume = False

    print("=" * 60)
    print("抖音数据清洗 + AI 多维标签分类")
    print("=" * 60)

    # 1. 合并
    print("\n📂 阶段1: 合并爬取数据")
    rows = merge_crawls()
    if not rows:
        print("❌ 无数据")
        return
    print(f"  总计: {len(rows)} 条视频")

    # 2. 清洗
    print(f"\n🧹 阶段2: 清洗无效评论")
    rows = clean_data(rows)

    if args.dry_run:
        print("\n🔍 Dry-run 模式，跳过 AI 标签")
        # 预览几条
        print("\n📋 数据预览:")
        for i, r in enumerate(rows[:5]):
            title = r.get("视频标题", "")[:60]
            author = r.get("作者昵称", "")
            likes = r.get("点赞数", "0")
            print(f"  [{i+1}] {author} | 👍{likes} | {title}")

        print(f"\n📂 清洗后文件: {CLEANED_CSV}")
        return

    # 3. AI 标签
    print(f"\n🤖 阶段3: DeepSeek AI 标签分类")

    if not API_KEY:
        print("❌ 请在 .env 中设置 DEEPSEEK_API_KEY=sk-xxx")
        return

    try:
        label_results = label_all(rows, workers=args.workers, resume=args.resume)
    except KeyboardInterrupt:
        print("\n⚠️ 中断，进度已保存。下次 --resume 继续")
        return

    # 4. 生成输出
    print(f"\n📊 阶段4: 生成输出")
    output_rows = build_output(rows, label_results)

    if output_rows:
        fieldnames = list(output_rows[0].keys())
        with open(LABELED_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(output_rows)
        print(f"📂 标签结果: {LABELED_CSV}")

        # Excel
        try:
            excel_path = csv_to_excel(
                LABELED_CSV,
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

    # 5. 汇总
    print_summary(output_rows)

    # 清理进度文件
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()

    print(f"\n{'='*60}")
    print("✅ 全流程完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
