"""
DeepSeek API 批量筛选帖子脚本
功能：调用 DeepSeek API 对知乎帖子进行语义分类，保留与以下主题相关的帖子：

  智能水杯 / 智能保温杯 / 智能恒温杯 / 温控水杯 / 恒温水杯 / 加热水杯 / 智能马克杯
  米家水杯 / 华为水杯 / 鸿蒙智联水杯
  Ember / OHOM / Nextmug / Cauldryn / HidrateSpark / LARQ / 麦开
  哈尔斯 / 苏泊尔 / 富光 / 希诺 / 物生物
  膳魔师 / 象印 / 虎牌 / Stanley / YETI
  恒温杯 vs 保温杯对比

过滤掉不相关的内容（如飞机杯、普通杯子无品牌/无智能功能的帖子等）。
"""

import csv
import json
import time
import argparse
from pathlib import Path
from typing import Iterator

import requests


# ============================================================
# 配置
# ============================================================

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 每批处理多少条后休息一下
BATCH_SIZE = 10
BATCH_SLEEP = 1.0
# 请求失败重试次数
MAX_RETRIES = 3
# 请求超时（秒）
REQUEST_TIMEOUT = 60

# 进度文件（支持断点续跑）
PROGRESS_FILE = "filter_progress.json"


# ============================================================
# 提示词
# ============================================================

SYSTEM_PROMPT = """你是一个内容审核助手，专门筛选与"智能水杯/温控杯/恒温杯/加热杯/特定品牌杯"相关的知乎帖子。

## 保留的主题（满足任一条即返回 true）

### 1. 智能/温控/恒温/加热功能的水杯
- 智能水杯、智能保温杯、智能恒温杯、智能马克杯
- 温控水杯、恒温水杯、恒温杯、加热水杯
- 电热水杯、55度杯、便携电热水杯

### 2. 智能杯品牌（无论正负面）
- Ember 温控杯/智能马克杯
- OHOM 水杯
- Nextmug 杯
- Cauldryn 杯
- HidrateSpark 智能水杯
- LARQ 自净化水杯
- 麦开（Moikit）智能水杯

### 3. 米家/华为/鸿蒙生态水杯
- 米家智能水杯、米家水杯
- 华为智选水杯、华为智能水杯
- 鸿蒙智联水杯、搭载鸿蒙的水杯

### 4. 需关注的国内品牌杯
- 哈尔斯（智能/保温/恒温系列）
- 苏泊尔（智能/保温/恒温系列）
- 富光（智能/保温系列）
- 希诺（智能/保温系列）
- 物生物（智能/保温/钛杯系列）

### 5. 国际品牌杯
- 膳魔师（Thermos）
- 象印（Zojirushi）
- 虎牌（Tiger）
- Stanley
- YETI

### 6. 相关对比/横评
- Ember 与膳魔师对比
- 恒温杯与保温杯对比
- 多个品牌杯子的横评/推荐

## 必须过滤的内容（返回 false）

- 飞机杯、成人用品（TENGA 等品牌的情趣用品）
- 只讲普通水杯/茶杯，不涉及任何上述品牌或智能/温控/恒温/加热功能
- 只讲咖啡/茶叶而不涉及杯子的
- "世界杯"、"奖杯"、"欧洲杯"等与饮水容器无关的
- 帖子只是顺带提了一句上述品牌但通篇主题无关

## 判定指南

关键判断：帖子是否在认真讨论上述品牌或功能的杯子？
- 评测/推荐/对比/使用体验 → true
- 真假鉴别/开箱/晒单 → true
- 行业分析/品牌动态/代工信息 → true
- 询问/求推荐 → true
- 顺带提到但主题完全无关 → false

请只返回 JSON 格式，不要有任何其他文字：
{"relevant": true/false, "reason": "简练说明命中哪个主题或为何过滤"}"""


def build_user_prompt(title: str, content: str) -> str:
    """构造用户消息"""
    # 截断过长文本，保留关键信息
    content_preview = content[:800] if content else "(无内容)"
    title_text = title[:300] if title else "(无标题)"
    return f"""请判断以下知乎帖子是否与杯子主题相关：

标题：{title_text}

内容摘要：{content_preview}"""


# ============================================================
# CSV 解析
# ============================================================

def parse_records(csv_path: Path) -> list[dict]:
    """
    解析多行 CSV 文件，将每条记录合并为一行。
    CSV 中某些字段包含换行符，导致一条记录跨多行。
    策略：以"内容"列（知乎链接）非空作为新记录开始的标志。
    """
    records = []

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        # 清理 header 中的 BOM 和空白
        header = [h.strip().replace("\ufeff", "") for h in header]

        current = None
        for row in reader:
            # 判断是否为新记录：第2列（内容/链接）有值
            has_link = len(row) >= 2 and row[1].strip().startswith("http")

            if has_link:
                # 保存上一条记录
                if current is not None:
                    records.append(_build_record(header, current))
                # 开始新记录
                current = row
            else:
                # 续行：拼接到上一条记录的最后一个字段
                if current is not None:
                    current[-1] = current[-1] + "\n" + (row[0] if row else "")

        # 最后一条记录
        if current is not None:
            records.append(_build_record(header, current))

    return records


def _build_record(header: list[str], parts: list[str]) -> dict:
    """将 CSV 行列表转为字典"""
    record = {}
    for i, key in enumerate(header):
        if i < len(parts):
            record[key] = parts[i].strip()
        else:
            record[key] = ""
    return record


# ============================================================
# DeepSeek API 调用
# ============================================================

class DeepSeekClassifier:
    def __init__(self, api_key: str, model: str = DEEPSEEK_MODEL):
        self.api_key = api_key
        self.model = model
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def classify(self, title: str, content: str) -> tuple[bool, str]:
        """
        返回 (是否相关, 原因)
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(title, content)},
            ],
            "temperature": 0.1,
            "max_tokens": 256,
        }

        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.post(
                    DEEPSEEK_API_URL,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                raw = data["choices"][0]["message"]["content"].strip()

                # 解析 JSON 响应
                result = self._parse_response(raw)
                return result

            except requests.RequestException as e:
                print(f"  [尝试 {attempt + 1}/{MAX_RETRIES}] 请求失败: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
            except (KeyError, json.JSONDecodeError) as e:
                print(f"  [尝试 {attempt + 1}/{MAX_RETRIES}] 解析失败: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)

        # 全部重试失败，默认保留（宁可多留不要误删）
        print(f"  [!] 分类失败，默认保留")
        return True, "分类失败，默认保留"

    @staticmethod
    def _parse_response(raw: str) -> tuple[bool, str]:
        """解析模型返回的 JSON"""
        # 去掉可能的 markdown 代码块标记
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:]) if len(lines) > 1 else raw
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()

        result = json.loads(raw)
        relevant = bool(result.get("relevant", True))
        reason = result.get("reason", "")
        return relevant, reason


# ============================================================
# 进度管理（断点续跑）
# ============================================================

def load_progress(output_dir: Path) -> tuple[set[int], list[dict]]:
    """加载已处理的进度和结果"""
    progress_path = output_dir / PROGRESS_FILE
    if progress_path.exists():
        with open(progress_path, "r") as f:
            data = json.load(f)
        return set(data.get("processed_indices", [])), data.get("kept_records", [])
    return set(), []


def save_progress(output_dir: Path, processed: set[int], kept: list[dict]):
    """保存进度"""
    progress_path = output_dir / PROGRESS_FILE
    with open(progress_path, "w") as f:
        json.dump({
            "processed_indices": list(processed),
            "kept_records": kept,
        }, f, ensure_ascii=False, indent=2)


# ============================================================
# 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="DeepSeek API 批量筛选帖子")
    parser.add_argument("--input", "-i", default="res/data/zhihu/raw/标题筛选版1.0.csv",
                        help="输入 CSV 文件路径（相对于项目根目录）")
    parser.add_argument("--output", "-o", default="res/data/zhihu/output/筛选结果.csv",
                        help="输出 CSV 文件路径（相对于项目根目录）")
    parser.add_argument("--api-key", "-k", default="",
                        help="DeepSeek API Key（也可通过 DEEPSEEK_API_KEY 环境变量设置）")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅解析 CSV 不调用 API，用于测试")
    parser.add_argument("--resume", action="store_true",
                        help="从上次中断处继续")
    args = parser.parse_args()

    # 确定项目根目录（脚本在 source/cleandata/ 下，根目录在三级之上）
    project_root = Path(__file__).resolve().parent.parent.parent
    input_path = project_root / args.input
    output_path = project_root / args.output
    output_dir = output_path.parent

    api_key = args.api_key or "your-api-key-here"

    # 1. 解析 CSV
    print(f"[1/3] 解析 CSV: {input_path}")
    records = parse_records(input_path)
    print(f"  共解析到 {len(records)} 条记录")

    if args.dry_run:
        print("\n[Dry-Run] 前5条记录预览:")
        for i, rec in enumerate(records[:5]):
            title = rec.get("highlight", "") or rec.get("richtext", "")
            content = rec.get("richtext", "") or ""
            print(f"  [{i}] 标题: {title[:80]}")
            print(f"      内容: {content[:120]}...")
            print()
        return

    # 2. 加载进度（断点续跑）
    processed_indices, kept_records = set(), []
    if args.resume:
        processed_indices, kept_records = load_progress(output_dir)
        print(f"  恢复进度: 已处理 {len(processed_indices)} 条，已保留 {len(kept_records)} 条")

    # 3. 调用 DeepSeek API 分类
    print(f"\n[2/3] 调用 DeepSeek API 分类...")
    print(f"  API: {DEEPSEEK_API_URL}")
    print(f"  Model: {DEEPSEEK_MODEL}")

    classifier = DeepSeekClassifier(api_key)

    try:
        for i, rec in enumerate(records):
            if i in processed_indices:
                continue

            # 提取标题和内容
            title = rec.get("highlight", "") or rec.get("richtext", "")
            content = rec.get("richtext", "") or ""

            print(f"  [{i + 1}/{len(records)}] {title[:60]}...", end=" ", flush=True)

            relevant, reason = classifier.classify(title, content)

            if relevant:
                kept_records.append(rec)
                print(f"✓ 保留 ({reason[:40]})")
            else:
                print(f"✗ 过滤 ({reason[:40]})")

            processed_indices.add(i)

            # 每批休息一下
            if (i + 1) % BATCH_SIZE == 0:
                # 保存进度
                save_progress(output_dir, processed_indices, kept_records)
                time.sleep(BATCH_SLEEP)

    except KeyboardInterrupt:
        print("\n\n[!] 用户中断，保存进度...")
        save_progress(output_dir, processed_indices, kept_records)
        print(f"  进度已保存: {len(processed_indices)}/{len(records)}")
        print(f"  下次运行加 --resume 继续")
        return

    # 最终保存进度
    save_progress(output_dir, processed_indices, kept_records)

    # 4. 输出结果
    print(f"\n[3/3] 输出结果...")
    print(f"  原始记录: {len(records)} 条")
    print(f"  保留记录: {len(kept_records)} 条")
    print(f"  过滤记录: {len(records) - len(kept_records)} 条")

    if kept_records:
        # 使用原始 CSV 的表头
        with open(input_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            original_header = next(reader)
            original_header = [h.strip().replace("\ufeff", "") for h in original_header]

        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=original_header)
            writer.writeheader()
            writer.writerows(kept_records)

        print(f"  结果已保存至: {output_path}")

    # 清理进度文件
    progress_path = output_dir / PROGRESS_FILE
    if progress_path.exists():
        progress_path.unlink()
        print(f"  进度文件已清理")


if __name__ == "__main__":
    main()
