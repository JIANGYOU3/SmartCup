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

    def __init__(self, cookie: str = None, sort_type: int = 1):
        """
        Args:
            cookie: 抖音 Cookie
            sort_type: 排序方式 0=综合 1=最多点赞 2=最新发布
        """
        self.cookie = cookie or config.COOKIE
        self.api = Request(cookie=self.cookie)
        self.sort_type = sort_type

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
                        'sort_type': str(self.sort_type),
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
        """通过 CDP 浏览器搜索（利用浏览器内置环境绕过签名）

        原理：在已登录的 Chrome 中执行 fetch，浏览器自动处理 Cookie/签名。
        """
        try:
            from ..lib.cdp2 import CDP, get_ws
        except ImportError:
            print("  ❌ CDP 模块不可用，请安装 websocket-client")
            return []

        ws = get_ws()
        if not ws:
            print("  ❌ 未找到 Chrome 调试端口 (localhost:9222)")
            print("  请启动 Chrome 调试模式后重试")
            return []

        cdp = CDP(ws)
        cdp.cmd("Page.enable")
        cdp.cmd("Runtime.enable")

        results = []
        all_ids = set()

        try:
            # 确保已在抖音首页建立会话
            cdp.cmd("Page.navigate", {"url": "https://www.douyin.com/?recommend=1"})
            time.sleep(4)

            for page in range(min(pages, 10)):
                offset = page * 20
                # 用浏览器 fetch 直接调搜索 API（无需签名）
                js_search = f"""
                (async function(){{
                  try {{
                    var params = new URLSearchParams({{
                      keyword: '{keyword}',
                      search_channel: 'aweme_general',
                      sort_type: '{self.sort_type}',
                      offset: '{offset}',
                      count: '20',
                      aid: '6383',
                      device_platform: 'webapp',
                      channel: 'channel_pc_web',
                      pc_client_type: '1',
                      version_code: '190500',
                      version_name: '19.5.0',
                      cookie_enabled: 'true',
                      browser_language: 'zh-CN',
                      browser_platform: 'Win32',
                      browser_name: 'Chrome',
                      engine_name: 'Blink',
                      os_name: 'Windows',
                      os_version: '10',
                    }});
                    var url = 'https://www.douyin.com/aweme/v1/web/general/search/single/?' + params.toString();
                    var resp = await fetch(url, {{
                      credentials: 'include',
                      headers: {{
                        'Accept': 'application/json, text/plain, */*',
                        'Accept-Language': 'zh-CN,zh;q=0.9',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'Referer': 'https://www.douyin.com/search/' + encodeURIComponent('{keyword}') + '?type=general',
                        'sec-ch-ua': '\"Not A(Brand\";v=\"8\", \"Chromium\";v=\"131\"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '\"Windows\"',
                        'sec-fetch-dest': 'empty',
                        'sec-fetch-mode': 'cors',
                        'sec-fetch-site': 'same-origin',
                      }}
                    }});
                    var data = await resp.json();
                    var result = {{status_code: data.status_code}};

                    if (data.search_nil_info && data.search_nil_info.search_nil_type) {{
                      result.nil_type = data.search_nil_info.search_nil_type;
                    }}

                    if (data.data && Array.isArray(data.data)) {{
                      result.count = data.data.length;
                      result.items = [];
                      data.data.forEach(function(item) {{
                        var info = item.aweme_info || {{}};
                        var stats = info.statistics || {{}};
                        result.items.push({{
                          aweme_id: String(info.aweme_id || ''),
                          desc: (info.desc || '').substring(0, 200),
                          author: (info.author || {{}}).nickname || '',
                          digg_count: stats.digg_count || 0,
                          comment_count: stats.comment_count || 0,
                        }});
                      }});
                    }}
                    return JSON.stringify(result);
                  }} catch(e) {{
                    return JSON.stringify({{error: e.message}});
                  }}
                }})()
                """

                r = cdp.cmd("Runtime.evaluate", {
                    "expression": js_search,
                    "returnByValue": True,
                    "awaitPromise": True,
                })

                value = r.get("result", {}).get("result", {}).get("value", "")
                if not value:
                    break

                import json
                data = json.loads(value)

                if data.get("nil_type") == "verify_check":
                    print(f"  ⚠️ '{keyword}' CDP搜索也被风控，请刷新页面重试")
                    break

                if data.get("error"):
                    print(f"  ❌ '{keyword}' JS错误: {data['error']}")
                    break

                items = data.get("items", [])
                if not items:
                    break

                new_count = 0
                for item in items:
                    aid = item["aweme_id"]
                    if aid and aid not in all_ids:
                        all_ids.add(aid)
                        results.append({
                            "aweme_id": aid,
                            "desc": item["desc"],
                            "author": item["author"],
                            "url": f"https://www.douyin.com/video/{aid}",
                            "keyword": keyword,
                        })
                        new_count += 1

                print(f"  📄 '{keyword}' 第{page+1}页: {len(items)}条, 新增 {new_count} 条")

                if len(items) < 15:
                    break

                time.sleep(2)  # 翻页间隔

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
    with_comments: bool = False,
    comment_pages: int = 5,
    sort_type: int = 1,
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
        with_comments: 是否抓取评论（含点赞/回复数）
        comment_pages: 评论翻页数
        sort_type: 排序方式 0=综合 1=最多点赞 2=最新发布
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

    searcher = DouyinSearcher(cookie, sort_type=sort_type)
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
    if with_comments:
        print(f"  含评论抓取（翻页: {comment_pages}）")

    crawl_csv = output_dir / f"爬取结果_{timestamp}.csv"
    scraper = DouyinScraper(cookie)

    from tqdm import tqdm
    from ..items import DouyinVideo

    # 基础字段名
    max_comment_cols = 20 if with_comments else 0
    fieldnames = DouyinVideo.get_fieldnames(max_comment_cols) if with_comments else DouyinVideo.BASE_FIELDNAMES

    with open(crawl_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        success = 0
        for item in tqdm(results, desc="爬取视频", unit="个"):
            if with_comments:
                video = scraper.scrape_with_comments(
                    item["url"], item.get("keyword", ""), max_comment_pages=comment_pages
                )
            else:
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
                    "作者粉丝量": 12, "发布时间": 16, "点赞数": 10,
                    "收藏数": 10, "分享数": 10, "视频时长": 10, "视频链接": 35,
                },
                link_columns={"视频链接"},
                number_columns={"播放数", "评论数", "点赞数", "收藏数", "分享数",
                                "视频时长", "作者粉丝量"},
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
