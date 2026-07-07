"""
抖音搜索爬虫 — 根据关键词搜索视频，自动爬取完整内容

流程：关键词 → 搜索 API / CDP 浏览器 → 收集视频 ID → 爬取完整内容 → CSV+Excel

用法：
  conda run -n SmartCup python -u -m source.douyin_crawler.search_main \
    --keywords "智能水杯,恒温杯" \
    --pages 5
"""

import re
import time
import random
from typing import Iterator

from ..config import config
from ..sign import Request
from .douyin import DouyinScraper


class DouyinSearcher:
    """抖音搜索器 — 根据关键词查找视频"""

    SEARCH_API = "/aweme/v1/web/general/search/single/"

    def __init__(self, cookie: str = None):
        self.cookie = cookie or config.COOKIE
        self.api = Request(cookie=self.cookie)

    def search(self, keyword: str, pages: int = 5) -> list[dict]:
        """
        搜索关键词，返回视频列表。
        优先尝试 API 搜索，失败则回退到 CDP 浏览器搜索。

        返回 list[dict]，每项包含: aweme_id, desc, author, url
        """
        # 先尝试 API
        results = self._search_api(keyword, pages)
        if results:
            return results

        # API 失败，尝试 CDP 浏览器搜索
        print(f"  ⚠️ API 搜索被风控，尝试 CDP 浏览器搜索...")
        results = self._search_cdp(keyword, pages)
        return results

    def _search_api(self, keyword: str, pages: int = 5) -> list[dict]:
        """通过 API 搜索（需要 websign 签名）"""
        results = []
        offset = 0
        count = 20

        for page in range(pages):
            try:
                resp, status = self.api.getJSON(
                    self.SEARCH_API,
                    {
                        'keyword': keyword,
                        'search_channel': 'aweme_general',
                        'enable_history': 'enable_history',
                        'query_correct_type': '1',
                        'offset': offset,
                        'count': count,
                        'need_filter_settings': 'need_filter_settings',
                        'list_type': 'single',
                    }
                )
            except Exception:
                break

            if status != 200 or not resp:
                break

            # 检查是否被风控
            if resp.get('status_code') != 0:
                nil_info = resp.get('search_nil_info', {}) or {}
                if nil_info.get('search_nil_type') == 'verify_check':
                    return []  # 被风控，回退到 CDP
                break

            items = []
            data = resp.get("data") or []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("data") or []

            if not items:
                break

            for item in items:
                aweme_info = item.get("aweme_info") or {}
                if not aweme_info:
                    continue

                aweme_id = aweme_info.get("aweme_id", "")
                if not aweme_id:
                    continue

                results.append({
                    "aweme_id": aweme_id,
                    "desc": aweme_info.get("desc", ""),
                    "author": (
                        aweme_info.get("author", {}).get("nickname", "")
                        if isinstance(aweme_info.get("author"), dict) else ""
                    ),
                    "url": f"https://www.douyin.com/video/{aweme_id}",
                    "keyword": keyword,
                })

            offset += count
            time.sleep(config.REQUEST_DELAY + random.uniform(0, 1.0))

        return results

    def _search_cdp(self, keyword: str, pages: int = 5) -> list[dict]:
        """通过 CDP 浏览器搜索（需要 Chrome 开启远程调试）"""
        try:
            from ..lib.cdp2 import CDP, get_ws
        except ImportError:
            print("  ❌ CDP 模块不可用，请安装 websocket-client")
            return []

        ws = get_ws()
        if not ws:
            print("  ❌ 未找到 Chrome 调试端口")
            print("  请用以下命令启动 Chrome：")
            print('  chrome.exe --remote-debugging-port=9222 --remote-allow-origins=*')
            print("  然后打开 www.douyin.com 并登录")
            return []

        cdp = CDP(ws)
        cdp.cmd("Page.enable")
        cdp.cmd("Runtime.enable")

        results = []
        all_ids = set()

        try:
            for page in range(min(pages, 5)):  # CDP 最多 5 页避免太慢
                if page == 0:
                    # 第一页：导航到搜索页
                    import urllib.parse
                    search_url = f'https://www.douyin.com/search/{urllib.parse.quote(keyword)}?type=general'
                    cdp.cmd("Page.navigate", {"url": search_url})
                    time.sleep(5)  # 等页面渲染
                else:
                    # 翻页：滚动到底部加载更多
                    cdp.cmd("Runtime.evaluate", {
                        "expression": "window.scrollTo(0, document.body.scrollHeight)",
                        "returnByValue": True
                    })
                    time.sleep(3)

                # 提取视频 ID（从 React fiber）
                js_extract = """
                (function(){
                  var cards = document.querySelectorAll('.search-result-card');
                  var ids = [];
                  var descs = [];

                  function deepFind(obj, depth) {
                    if (!obj || depth > 50 || typeof obj !== 'object') return null;
                    if (obj.aweme_id || obj.awemeId) {
                      return String(obj.aweme_id || obj.awemeId);
                    }
                    var keys = Object.keys(obj);
                    for (var i = 0; i < keys.length; i++) {
                      var k = keys[i];
                      if (k === 'aweme_id' || k === 'awemeId') return String(obj[k]);
                      try {
                        if (typeof obj[k] === 'object' && obj[k] !== null && k !== 'owner' && k !== 'parent' && k !== 'source') {
                          var result = deepFind(obj[k], depth + 1);
                          if (result) return result;
                        }
                      } catch(e) {}
                    }
                    return null;
                  }

                  cards.forEach(function(card) {
                    var fiberKey = Object.keys(card).find(function(k){
                      return k.startsWith('__reactFiber');
                    });
                    var videoId = null;
                    if (fiberKey) videoId = deepFind(card[fiberKey], 0);
                    if (videoId) {
                      ids.push(videoId);
                      var text = card.textContent.replace(/\\s+/g, ' ').trim().substring(0, 100);
                      descs.push(text);
                    }
                  });
                  return JSON.stringify({ids: ids, descs: descs});
                })()
                """

                result = cdp.cmd("Runtime.evaluate", {
                    "expression": js_extract,
                    "returnByValue": True
                })

                value = result.get("result", {}).get("result", {}).get("value", "")
                if value:
                    import json
                    data = json.loads(value)
                    ids = data.get("ids", [])
                    descs = data.get("descs", [])

                    new_count = 0
                    for i, vid in enumerate(ids):
                        if vid not in all_ids:
                            all_ids.add(vid)
                            desc = descs[i] if i < len(descs) else ""
                            results.append({
                                "aweme_id": vid,
                                "desc": desc[:120],
                                "author": "",
                                "url": f"https://www.douyin.com/video/{vid}",
                                "keyword": keyword,
                            })
                            new_count += 1

                    print(f"  📄 '{keyword}' 第{page+1}页: {len(ids)}条, 新增 {new_count} 条")

                    if len(ids) < 10:
                        break  # 不够一页，可能没有更多结果了

        finally:
            cdp.close()

        return results

    def search_multi(self, keywords: list[str], pages: int = 5) -> list[dict]:
        """多关键词搜索，自动去重"""
        seen = set()
        all_results = []

        for kw in keywords:
            print(f"  搜索: {kw}", flush=True)
            results = self.search(kw, pages)
            for r in results:
                if r["aweme_id"] not in seen:
                    seen.add(r["aweme_id"])
                    r["keyword"] = kw
                    all_results.append(r)
            print(f"    → {len(results)} 条（去重后累计 {len(all_results)}）", flush=True)

        return all_results


def search_and_crawl(
    keywords: list[str],
    search_pages: int = 5,
    output_dir: str = None,
    cookie: str = None,
    auto_crawl: bool = True,
    search_only: bool = False,
):
    """
    完整的搜索 + 爬取流程。

    Args:
        keywords: 搜索关键词列表
        search_pages: 每个关键词最多翻几页
        output_dir: 输出目录（默认 res/data/douyin/output/）
        cookie: 抖音 Cookie
        auto_crawl: 是否自动爬取完整内容
        search_only: 仅搜索不爬取
    """
    from pathlib import Path
    from datetime import datetime
    import csv

    from source.common.paths import get_output_dir

    if output_dir is None:
        output_dir = get_output_dir("douyin")
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # ── 阶段 1：搜索 ──
    print(f"\n{'='*60}")
    print(f"阶段1: 抖音关键词搜索")
    print(f"{'='*60}")
    print(f"  关键词: {', '.join(keywords)}")
    print(f"  每个关键词翻页: {search_pages} 页（每页 20 条）")
    print()

    searcher = DouyinSearcher(cookie)
    results = searcher.search_multi(keywords, search_pages)

    if not results:
        print("❌ 未找到任何结果")
        return

    # 保存搜索结果
    search_csv = output_dir / f"搜索结果_{timestamp}.csv"
    with open(search_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["aweme_id", "desc", "author", "url", "keyword"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\n📂 搜索结果: {search_csv}  ({len(results)} 条)")

    if search_only:
        print("✅ 仅搜索模式完成")
        return

    # ── 阶段 2：爬取完整内容 ──
    print(f"\n{'='*60}")
    print(f"阶段2: 爬取视频完整内容")
    print(f"{'='*60}")

    crawl_csv = output_dir / f"爬取结果_{timestamp}.csv"
    scraper = DouyinScraper(cookie)

    from tqdm import tqdm

    with open(crawl_csv, "w", encoding="utf-8-sig", newline="") as f:
        from ..items import DouyinVideo
        writer = csv.DictWriter(f, fieldnames=DouyinVideo.FIELDNAMES)
        writer.writeheader()

        success = 0
        for item in tqdm(results, desc="爬取视频", unit="个"):
            video = scraper.scrape(item["url"], item.get("keyword", ""))
            if video:
                row = video.to_dict()
                row["关键词"] = item.get("keyword", "")
                writer.writerow(row)
                f.flush()
                success += 1

    print(f"\n✅ 爬取完成: {success}/{len(results)} 个视频")

    # ── 阶段 3：转 Excel ──
    if Path(crawl_csv).exists():
        print(f"\n📊 正在生成 Excel...")
        try:
            from source.common.excel_style import csv_to_excel
            excel_path = csv_to_excel(
                Path(crawl_csv),
                sheet_title="抖音爬取结果",
                column_widths={
                    "关键词": 20, "视频类型": 10, "播放数": 12, "评论数": 10,
                    "视频标题": 45, "视频文案": 55, "作者昵称": 14,
                    "发布时间": 16, "点赞数": 10, "分享数": 10,
                    "视频时长": 10, "视频链接": 35,
                },
                link_columns={"视频链接"},
                number_columns={"播放数", "评论数", "点赞数", "分享数", "视频时长"},
            )
            print(f"✅ Excel 已保存: {excel_path}")
        except Exception as e:
            print(f"⚠️ Excel 生成失败: {e}")

    print(f"\n{'='*60}")
    print(f"✅ 全流程完成")
    print(f"{'='*60}")
    print(f"   搜索关键词: {', '.join(keywords)}")
    print(f"   搜索结果: {search_csv}")
    print(f"   爬取结果: {crawl_csv}")

    return crawl_csv
