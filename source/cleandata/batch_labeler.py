"""
DeepSeek API 批量标签分类 + 证据提取脚本

功能：
  1. 解析多行 CSV，过滤污染数据（成人内容/无关"杯"/空内容）
  2. 并发调用 DeepSeek API 给帖子打标签 + 提取证据
  3. AI 仅返回 JSON: {"labels": [...], "evidence": {...}}
  4. 汇总输出清洗后的 7 字段数据：链接、标签、标题、正文开头、点赞数、评论数、AI证据理由

用法：
  conda run -n SmartCup python src/batch_labeler.py [--workers 8] [--resume]

  API Key 从 .env 文件自动加载，无需每次传入。
"""

import csv
import json
import os
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import requests
from tqdm import tqdm

from source.common.paths import load_env, get_project_root
from source.common.text_utils import clean_text, extract_number, make_content_preview
from source.common.pollution import NSFW_KEYWORDS, IRRELEVANT_CUP_KEYWORDS, is_polluted
from source.common.csv_utils import parse_multiline_csv
from source.common.excel_style import csv_to_excel

# 加载项目根目录的 .env 文件
load_env()

# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

REQUEST_TIMEOUT = 90       # 单次 API 请求超时（秒）
MAX_RETRIES = 3            # 请求失败最大重试次数
PROGRESS_FILE = "labeler_progress.json"  # 断点续跑进度文件

# 并行配置
DEFAULT_MAX_WORKERS = 8    # DeepSeek 付费账户默认并发数
BATCH_SAVE_INTERVAL = 20   # 每处理 20 条保存一次进度



# ──────────────────────────────────────────────
# 标签体系（AI 从下列标签中选择）
# ──────────────────────────────────────────────

LABEL_TAXONOMY = [
    "智能水杯/温控杯",      # 智能控温、恒温、调温功能的水杯
    "电热水杯/加热杯",       # 便携电热水杯、车载加热杯、55度杯
    "Ember温控杯",           # Ember 品牌温控马克杯
    "其他国际智能品牌",      # OHOM / Nextmug / Cauldryn / HidrateSpark / LARQ
    "麦开/Moikit",           # 麦开智能水杯
    "米家/小米水杯",         # 小米、米家生态水杯
    "华为/鸿蒙水杯",         # 华为智选、鸿蒙智联水杯
    "哈尔斯",                # 哈尔斯品牌（智能/保温系列）
    "苏泊尔",                # 苏泊尔品牌水杯
    "富光",                  # 富光品牌水杯
    "希诺",                  # 希诺品牌水杯
    "物生物",                # 物生物品牌水杯
    "膳魔师",                # 膳魔师 / Thermos
    "象印",                  # 象印 / Zojirushi
    "虎牌",                  # 虎牌 / Tiger
    "Stanley",               # Stanley 品牌
    "YETI",                  # YETI 品牌
    "品牌对比/横评",         # 多个品牌或产品的横向对比/测评
    "保温杯推荐/导购",       # 保温杯选购指南、推荐清单
    "其他杯具相关",          # 与水杯相关但不属于上述品牌/类型
    "不相关",                # 与水杯/上述品牌无关的内容
]

# ──────────────────────────────────────────────
# AI Prompt
# ──────────────────────────────────────────────

SYSTEM_PROMPT = f"""你是一个内容标签专家，专门给知乎帖子打标签并提取证据。

## 任务

阅读帖子的**标题**和**内容摘要**，从下列标签中选出帖子涉及的所有标签，并为每个选中的标签提供一句证据（直接从原文引用关键短语）。

## 可选标签

{chr(10).join(f"- {lb}" for lb in LABEL_TAXONOMY)}

## 打标签规则

1. 帖子可能属于 1 个或多个标签（多标签分类）
2. 如果帖子明确提到某个品牌或产品类型，就打上对应标签
3. 如果帖子是对比/推荐/横评，额外打上"品牌对比/横评"或"保温杯推荐/导购"
4. 如果帖子完全没有涉及上述标签中的任何一个，打上"不相关"
5. 证据必须**直接引用原文**，10个字以内，简明扼要
6. "不相关"标签的证据说明为什么无关

## 输出格式

严格输出 JSON，不要任何其他文字：

{{"labels": ["标签1", "标签2"], "evidence": {{"标签1": "原文引用证据", "标签2": "原文引用证据"}}}}

如果只有"不相关"：
{{"labels": ["不相关"], "evidence": {{"不相关": "帖子讨论的是xxx，与水杯/智能杯无关"}}}}"""


def build_user_prompt(title: str, content: str) -> str:
    """构造发送给 DeepSeek 的用户消息"""
    title = title[:200] if title else "(无标题)"
    content = content[:600] if content else "(无内容)"
    return f"标题：{title}\n\n内容摘要：{content}"



# ──────────────────────────────────────────────
# 数据清洗辅助
# ──────────────────────────────────────────────

def extract_content_text(record: dict) -> str:
    """从旧浏览器导出或当前知乎爬虫输出中提取正文。"""
    parts = [
        record.get("richtext", ""),
        record.get("richtext2", ""),
        record.get("richtext3", ""),
        record.get("richtext4", ""),
        record.get("内容5", ""),
        record.get("问题内容", ""),
        record.get("回答内容", ""),
    ]
    return " ".join(p for p in parts if p).strip()


# ──────────────────────────────────────────────
# DeepSeek API 客户端
# ──────────────────────────────────────────────

class DeepSeekLabeler:
    def __init__(self, api_key: str, model: str = DEEPSEEK_MODEL):
        self.api_key = api_key
        self.model = model

    def _make_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        return s

    def label_one(self, title: str, content: str) -> tuple[list[str], dict[str, str], str]:
        """
        调用 API 对单条记录打标签。

        Returns:
            (labels, evidence, raw_response_json_string)
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(title, content)},
            ],
            "temperature": 0.0,
            "max_tokens": 512,
            "response_format": {"type": "json_object"},
        }

        last_error = ""
        for attempt in range(MAX_RETRIES):
            try:
                session = self._make_session()
                resp = session.post(
                    DEEPSEEK_API_URL,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                raw = data["choices"][0]["message"]["content"].strip()

                # 解析 JSON
                result = json.loads(raw)
                labels = result.get("labels", ["不相关"])
                evidence = result.get("evidence", {})

                # 校验 labels 是列表，evidence 是字典
                if not isinstance(labels, list):
                    labels = [str(labels)]
                if not isinstance(evidence, dict):
                    evidence = {"结果": str(evidence)}

                # 过滤无效标签
                labels = [lb for lb in labels if isinstance(lb, str)]

                return labels, evidence, json.dumps(result, ensure_ascii=False)
            except requests.RequestException as e:
                last_error = f"HTTP错误: {e}"
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                last_error = f"解析错误: {e}"
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)

        # 全部失败
        return ["API失败"], {"API失败": last_error}, json.dumps({"error": last_error}, ensure_ascii=False)


# ──────────────────────────────────────────────
# 进度管理（断点续跑）
# ──────────────────────────────────────────────

def load_progress(output_dir: Path) -> dict[int, dict]:
    """加载已处理的结果，返回 {record_index: result_dict}"""
    path = output_dir / PROGRESS_FILE
    if path.exists():
        with open(path, "r") as f:
            data = json.load(f)
        return {int(k): v for k, v in data.get("results", {}).items()}
    return {}


def save_progress(output_dir: Path, results: dict[int, dict]):
    path = output_dir / PROGRESS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump({"results": {str(k): v for k, v in results.items()}}, f, ensure_ascii=False, indent=2)


# ──────────────────────────────────────────────
# 主处理流程
# ──────────────────────────────────────────────

def process_record(idx: int, record: dict, labeler: DeepSeekLabeler) -> dict:
    """处理单条记录（供线程池调用），返回结果字典"""
    title = clean_text(record.get("highlight", "") or record.get("问题标题", ""))
    content = extract_content_text(record)

    # 1. 污染检测
    pollution_reason = is_polluted(title, content)
    if pollution_reason:
        return {
            "index": idx,
            "labels": ["污染"],
            "evidence": {"污染": pollution_reason},
            "ai_raw": json.dumps({"labels": ["污染"], "evidence": {"污染": pollution_reason}}, ensure_ascii=False),
            "status": "skipped",
        }

    # 2. 调用 API
    labels, evidence, ai_raw = labeler.label_one(title, content)

    return {
        "index": idx,
        "labels": labels,
        "evidence": evidence,
        "ai_raw": ai_raw,
        "status": "ok",
    }


def build_output_row(record: dict, ai_result: dict) -> dict:
    """合并原始数据和 AI 结果，输出 7 字段"""
    title = clean_text(record.get("highlight", "") or record.get("问题标题", ""))
    content = extract_content_text(record)
    link = (record.get("内容", "") or record.get("问答链接", "")).strip()
    likes = extract_number(record.get("button", "") or record.get("赞同数", ""))
    comments = extract_number(record.get("内容6", "") or record.get("评论数", ""))

    labels = ai_result.get("labels", [])
    evidence = ai_result.get("evidence", {})

    # 按标签组织的证据理由字符串
    evidence_str = "; ".join(
        f"[{lb}] {evidence.get(lb, '')}" for lb in labels
    ) if labels else ""

    return {
        "链接": link,
        "标签": ", ".join(labels),
        "标题": title,
        "正文开头": make_content_preview(content),
        "点赞数": likes,
        "评论数": comments,
        "AI证据理由": evidence_str,
        "AI原始JSON": ai_result.get("ai_raw", ""),  # 额外保留原始 JSON 用于校验
    }


def main():
    parser = argparse.ArgumentParser(description="DeepSeek API 批量标签分类器")
    parser.add_argument("--input", "-i", default="res/data/zhihu/raw/标题筛选版1.0.csv",
                        help="输入 CSV 文件路径（相对于项目根目录）")
    parser.add_argument("--output", "-o", default="res/data/zhihu/output/标签结果.csv",
                        help="输出 CSV/Excel 文件路径（相对于项目根目录）")
    parser.add_argument("--api-key", "-k", default="",
                        help="DeepSeek API Key（优先用 DEEPSEEK_API_KEY 环境变量）")
    parser.add_argument("--workers", "-w", type=int, default=DEFAULT_MAX_WORKERS,
                        help=f"并发数（默认 {DEFAULT_MAX_WORKERS}）")
    parser.add_argument("--resume", action="store_true", help="断点续跑")
    parser.add_argument("--dry-run", action="store_true", help="仅解析+污染检测，不调 API")
    args = parser.parse_args()

    # API Key：命令行参数 > 环境变量 > .env 文件
    api_key = args.api_key or os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("❌ 未找到 API Key！请通过以下任一方式提供：")
        print("   1. 命令行: --api-key sk-xxxxx")
        print("   2. 环境变量: export DEEPSEEK_API_KEY=sk-xxxxx")
        print("   3. .env 文件: 编辑项目目录下的 .env，设置 DEEPSEEK_API_KEY=sk-xxxxx")
        return

    project_root = get_project_root()
    input_path = project_root / args.input
    output_path = project_root / args.output
    output_dir = output_path.parent

    # ── 1. 解析 CSV ──
    print(f"📂 解析 CSV: {input_path}")
    records = parse_multiline_csv(input_path)
    print(f"   共 {len(records)} 条记录")
    print()

    # ── 2. 污染预检 ──
    polluted_count = 0
    clean_indices = []
    for i, rec in enumerate(records):
        title = clean_text(rec.get("highlight", "") or rec.get("问题标题", ""))
        content = extract_content_text(rec)
        reason = is_polluted(title, content)
        if reason:
            polluted_count += 1
        else:
            clean_indices.append(i)
    print(f"🧹 污染检测: {polluted_count} 条污染, {len(clean_indices)} 条干净")
    print()

    if args.dry_run:
        print("=== Dry-Run: 前10条预览 ===")
        for i in range(min(10, len(records))):
            rec = records[i]
            title = clean_text(rec.get("highlight", "") or rec.get("问题标题", ""))
            content = extract_content_text(rec)
            reason = is_polluted(title, content)
            status = f"❌ {reason}" if reason else "✅ 干净"
            print(f"  [{i}] {status} | {title[:50]}")
        return

    # ── 3. 加载进度 ──
    cached_results: dict[int, dict] = {}
    if args.resume:
        cached_results = load_progress(output_dir)
        print(f"📥 断点续跑: 已缓存 {len(cached_results)} 条结果")

    # ── 4. 并发调用 DeepSeek API ──
    labeler = DeepSeekLabeler(api_key)
    results: dict[int, dict] = dict(cached_results)  # 最终结果 {idx: result_dict}

    # 筛选待处理记录
    pending = [(i, records[i]) for i in clean_indices if i not in results]

    if not pending:
        print("✅ 所有记录已处理完毕")
    else:
        print(f"🚀 开始并发处理 {len(pending)} 条记录（{args.workers} 并发）")
        print()

        # 进度条
        pbar = tqdm(total=len(pending), desc="DeepSeek API", unit="条",
                     ncols=100, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(process_record, idx, rec, labeler): idx
                for idx, rec in pending
            }

            completed_since_save = 0
            for future in as_completed(futures):
                try:
                    result = future.result()
                    idx = result["index"]
                    results[idx] = result
                    pbar.update(1)

                    # 显示标签
                    labels_str = ", ".join(result.get("labels", []))
                    pbar.set_postfix_str(f"tags: {labels_str[:30]}")

                    completed_since_save += 1
                    if completed_since_save >= BATCH_SAVE_INTERVAL:
                        save_progress(output_dir, results)
                        completed_since_save = 0

                except Exception as e:
                    idx = futures[future]
                    tqdm.write(f"  [!] 记录 [{idx}] 线程异常: {e}")
                    results[idx] = {
                        "index": idx,
                        "labels": ["异常"],
                        "evidence": {"异常": str(e)},
                        "ai_raw": "{}",
                        "status": "error",
                    }
                    pbar.update(1)

        pbar.close()
        save_progress(output_dir, results)
        print()

    # ── 5. 处理污染记录（补全结果） ──
    for i, rec in enumerate(records):
        if i not in results:
            title = clean_text(rec.get("highlight", "") or rec.get("问题标题", ""))
            content = extract_content_text(rec)
            reason = is_polluted(title, content) or "未知"
            results[i] = {
                "index": i,
                "labels": ["污染"],
                "evidence": {"污染": reason},
                "ai_raw": "{}",
                "status": "skipped",
            }

    # ── 6. 构建输出行数据 ──
    print(f"📊 统计:")
    label_counter = {}
    status_counter = {}
    for r in results.values():
        status_counter[r.get("status", "?")] = status_counter.get(r.get("status", "?"), 0) + 1
        for lb in r.get("labels", []):
            label_counter[lb] = label_counter.get(lb, 0) + 1

    print(f"   状态分布: {status_counter}")
    print(f"   标签分布（Top 10）:")
    for lb, cnt in sorted(label_counter.items(), key=lambda x: -x[1])[:10]:
        print(f"     {lb}: {cnt} 条")
    print()

    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = ["链接", "标签", "标题", "正文开头", "点赞数", "评论数", "AI证据理由", "AI原始JSON"]

    # 按原始顺序构建所有行
    all_rows = []
    for i in range(len(records)):
        all_rows.append(build_output_row(records[i], results[i]))

    # ── 7. 输出 CSV ──
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"✅ CSV 已保存: {output_path}")

    # ── 8. 输出 Excel ──
    excel_path = csv_to_excel(
        output_path,
        sheet_title="标签结果",
        column_widths={
            "链接": 35, "标签": 30, "标题": 45, "正文开头": 50,
            "点赞数": 10, "评论数": 10, "AI证据理由": 55, "AI原始JSON": 45,
        },
        link_columns={"链接"},
        number_columns={"点赞数", "评论数"},
    )
    print(f"✅ Excel 已保存: {excel_path}")
    print(f"   共 {len(records)} 行（含污染 {polluted_count} 条）")

    # ── 9. 清理进度文件 ──
    progress_path = output_dir / PROGRESS_FILE
    if progress_path.exists():
        progress_path.unlink()
        print(f"   进度文件已清理")


if __name__ == "__main__":
    main()
