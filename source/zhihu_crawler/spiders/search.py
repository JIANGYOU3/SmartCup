"""
知乎搜索爬虫 — 根据关键词搜索帖子，自动爬取完整内容

流程：关键词 → 搜索API → 收集链接 → 调用已有爬虫获取完整内容 → 输出CSV+Excel

用法：
  conda run -n SmartCup python -u -m source.zhihu_crawler.search_main \
    --keywords "智能水杯,恒温杯,Ember温控杯" \
    --pages 5
"""

import re
import time
import random
import json
from typing import Iterator
from urllib.parse import quote

import requests

from ..config import config
from .zhihu import ZhihuScraper, load_links_from_csv
from source.common.paths import get_output_dir


class ZhihuSearcher:
    """知乎搜索器 — 根据关键词查找帖子"""

    SEARCH_API = "https://www.zhihu.com/api/v4/search_v3"

    def __init__(self, cookie: str = None):
        self.cookie = cookie or config.COOKIE
        if not self.cookie:
            raise ValueError("未设置知乎 Cookie！")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Cookie": self.cookie,
            "x-requested-with": "fetch",
        })
        self._count = 0

    def _delay(self):
        time.sleep(config.REQUEST_DELAY / 2 + random.uniform(0.3, 0.8))

    def search(self, keyword: str, max_pages: int = 5) -> list[dict]:
        """
        搜索关键词，返回帖子列表。

        Args:
            keyword: 搜索关键词，如 "智能水杯"
            max_pages: 最多翻几页（每页 20 条）

        Returns:
            [{"链接": url, "标题": title, "类型": type, "摘要": excerpt, "赞同": votes}, ...]
        """
        results = []
        seen_urls = set()

        for page in range(max_pages):
            offset = page * 20
            url = f"{self.SEARCH_API}?q={quote(keyword)}&type=content&offset={offset}&limit=20&t=general"

            self._delay()
            self._count += 1

            try:
                resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                if resp.status_code != 200:
                    print(f"  ⚠️ 搜索 '{keyword}' 第{page+1}页 HTTP {resp.status_code}")
                    if resp.status_code == 403:
                        break  # 被拦截，停止翻页
                    continue

                data = resp.json()
                items = data.get("data", [])

                if not items:
                    break  # 无更多结果

                for item in items:
                    obj = item.get("object", {})
                    obj_type = obj.get("type", "")
                    link = obj.get("url", "")

                    # 只看回答和文章，跳过视频
                    if obj_type not in ("answer", "article"):
                        continue
                    if not link or link in seen_urls:
                        continue

                    seen_urls.add(link)

                    # 提取基础信息
                    question = obj.get("question", {})
                    title = question.get("title", "") or obj.get("title", "")
                    excerpt = obj.get("excerpt", "")
                    votes = obj.get("voteup_count", 0) or 0

                    results.append({
                        "链接": link if link.startswith("http") else f"https://www.zhihu.com{link}",
                        "标题": title,
                        "类型": "问答帖" if obj_type == "answer" else "专栏文章",
                        "搜索关键词": keyword,
                        "摘要": re.sub(r'<[^>]+>', '', excerpt or ""),
                        "预估赞同": votes,
                    })

                print(f"  📄 '{keyword}' 第{page+1}页: {len(items)}条, 累计 {len(seen_urls)}条")

            except Exception as e:
                print(f"  ❌ 搜索 '{keyword}' 第{page+1}页异常: {e}")
                continue

        return results

    def search_multi(self, keywords: list[str], max_pages: int = 5) -> list[dict]:
        """
        批量搜索多个关键词，自动去重。

        Returns:
            去重后的帖子列表
        """
        all_results = []
        seen = set()

        for kw in keywords:
            print(f"\n🔍 搜索: '{kw}'")
            results = self.search(kw.strip(), max_pages)
            new_count = 0
            for r in results:
                if r["链接"] not in seen:
                    seen.add(r["链接"])
                    all_results.append(r)
                    new_count += 1
            print(f"   ✅ '{kw}': 新增 {new_count} 条（去重后）")

        return all_results


def search_and_crawl(
    keywords: list[str],
    search_pages: int = 5,
    output_dir: Path = None,
    cookie: str = None,
    auto_crawl: bool = True,
):
    """
    搜索 + 爬取的完整工作流。

    1. 搜索关键词 → 收集链接
    2. 保存搜索结果为 CSV
    3. 自动调用爬虫获取完整内容
    4. 输出最终 Excel

    Args:
        keywords: 搜索关键词列表
        search_pages: 每个关键词最多翻几页
        output_dir: 输出目录（默认 res/data/zhihu/output/）
        cookie: 知乎 Cookie
        auto_crawl: 是否自动爬取完整内容
    """
    from pathlib import Path
    from datetime import datetime
    import csv

    if output_dir is None:
        output_dir = get_output_dir("zhihu")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    search_csv = output_dir / f"搜索结果_{timestamp}.csv"

    # ── 阶段1：搜索 ──
    print(f"\n{'='*60}")
    print(f"阶段1: 知乎关键词搜索")
    print(f"{'='*60}")
    print(f"  关键词: {', '.join(keywords)}")
    print(f"  每个关键词翻页: {search_pages} 页（每页20条）")
    print()

    searcher = ZhihuSearcher(cookie)
    results = searcher.search_multi(keywords, search_pages)

    if not results:
        print("\n❌ 未找到任何结果，请检查关键词或 Cookie")
        return None

    # 保存搜索结果
    with open(search_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["链接", "标题", "类型", "搜索关键词", "摘要", "预估赞同"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n📁 搜索结果已保存: {search_csv}")
    print(f"   共 {len(results)} 条（去重后）")
    print(f"   搜索请求: {searcher._count} 次")

    # 统计
    type_counts = {}
    for r in results:
        t = r.get("类型", "未知")
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"   类型分布: {dict(type_counts)}")

    if not auto_crawl:
        print(f"\n⏸️ 停止（auto_crawl=False），如需爬取完整内容请运行：")
        print(f"   conda run -n SmartCup python -u -m source.zhihu_crawler.main -i {search_csv}")
        return search_csv

    # ── 阶段2：爬取完整内容 ──
    print(f"\n{'='*60}")
    print(f"阶段2: 爬取完整内容")
    print(f"{'='*60}")

    crawl_output = output_dir / f"搜索内容_{timestamp}.csv"

    # 复用现有爬虫的批量逻辑
    from .zhihu import run_batch_scrape
    run_batch_scrape(
        input_csv=search_csv,
        output_csv=crawl_output,
        cookie=cookie,
        resume=False,
    )

    # ── 阶段3：转 Excel ──
    if crawl_output.exists():
        print(f"\n{'='*60}")
        print(f"阶段3: 生成 Excel")
        print(f"{'='*60}")
        try:
            from source.common.excel_style import csv_to_excel
            excel_path = csv_to_excel(
                crawl_output,
                sheet_title="爬取结果",
                column_widths={
                    "关键词": 25, "帖子类型": 10, "问题被浏览次数": 14, "问题回答个数": 14,
                    "问题评论个数": 14, "问题标题": 40, "问题内容": 50, "答主昵称": 14,
                    "回答时间": 16, "赞同数": 10, "评论数": 10, "回答内容": 55, "问答链接": 35,
                },
                link_columns={"问答链接"},
                number_columns={"赞同数", "评论数", "问题被浏览次数", "问题回答个数", "问题评论个数"},
            )
            print(f"✅ Excel 已保存: {excel_path}")
        except Exception as e:
            print(f"⚠️ Excel 生成失败: {e}")

        print(f"\n{'='*60}")
        print(f"✅ 全流程完成")
        print(f"{'='*60}")
        print(f"   搜索关键词: {', '.join(keywords)}")
        print(f"   发现帖子: {len(results)} 条")
        print(f"   搜索结果: {search_csv}")
        print(f"   完整内容: {crawl_output}")

    return crawl_output
