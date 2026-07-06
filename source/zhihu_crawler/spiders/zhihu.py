"""
知乎爬虫 — HTML 解析方案（从 js-initialData 提取完整数据）

支持类型：
  - /question/{qid}/answer/{aid}  → HTML → entities.answers + entities.questions
  - /question/{qid}               → HTML → entities.questions
  - /p/{post_id}                  → HTML → entities.articles 或 initialData.post
  - /zvideo/{id}                  → 跳过

输出 12 字段：关键词、问题浏览量、问题回答数、问题评论数、问题标题、
            问题内容、答主昵称、回答时间、赞同数、评论数、回答内容、问答链接
"""

import re
import time
import json
import random
import html as html_mod
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from ..config import config
from ..utils import clean_text
from source.common.csv_utils import extract_links_from_csv


class ZhihuScraper:
    """知乎爬虫：HTML 解析方案，一次请求拿到全部字段"""

    def __init__(self, cookie: str = None):
        self.cookie = cookie or config.COOKIE
        if not self.cookie:
            raise ValueError("未设置知乎 Cookie！请在 .env 中设置 ZHIHU_COOKIE=...")

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Cookie": self.cookie,
        })
        self.session.timeout = config.REQUEST_TIMEOUT
        self._request_count = 0

    # ── URL 路由 ────────────────────────────────

    @staticmethod
    def categorize_url(url: str) -> str:
        if '/answer/' in url:   return 'answer'
        if '/zvideo/' in url:  return 'video'
        if '/question/' in url: return 'question'
        if '/p/' in url:       return 'article'
        return 'unknown'

    @staticmethod
    def extract_ids(url: str) -> tuple[Optional[str], Optional[str]]:
        m = re.search(r'/question/(\d+)/answer/(\d+)', url)
        if m: return m.group(1), m.group(2)
        m = re.search(r'/question/(\d+)', url)
        if m: return m.group(1), None
        m = re.search(r'/p/(\d+)', url)
        if m: return None, m.group(1)
        return None, None

    # ── HTML 获取 ───────────────────────────────

    def _fetch_html(self, url: str, log: Callable = None) -> Optional[BeautifulSoup]:
        """获取页面 HTML"""
        self._request_count += 1
        for attempt in range(config.MAX_RETRIES):
            try:
                resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                if resp.status_code == 404:
                    _write(log, f"  ⚠️ HTTP 404 — 内容已删除或不存在")
                    return None
                if resp.status_code == 403:
                    _write(log, f"  ⚠️ HTTP 403 — Cookie 失效或被拦截")
                    return None
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "lxml")
            except requests.RequestException as e:
                if attempt < config.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                else:
                    _write(log, f"  ❌ 请求失败: {e}")
        return None

    def _delay(self):
        t = config.REQUEST_DELAY + random.uniform(0.3, 1.0)
        time.sleep(t)

    def _extract_initial_data(self, soup: BeautifulSoup) -> Optional[dict]:
        script = soup.find("script", id="js-initialData")
        if not script or not script.string:
            return None
        try:
            return json.loads(script.string)
        except json.JSONDecodeError:
            return None

    # ── 解析器 ──────────────────────────────────

    def parse_answer_page(self, qid: str, aid: str, log: Callable = None) -> dict:
        url = f"https://www.zhihu.com/question/{qid}/answer/{aid}"
        self._delay()
        soup = self._fetch_html(url, log)
        if soup is None:
            return {"_error": "fetch_failed"}
        data = self._extract_initial_data(soup)
        if data is None:
            return {"_error": "no_initialData"}
        entities = data.get("initialState", {}).get("entities", {})
        answers = entities.get("answers", {})
        answer = answers.get(str(aid), list(answers.values())[0] if answers else {})
        questions = entities.get("questions", {})
        question = questions.get(str(qid), list(questions.values())[0] if questions else {})
        return self._build_result(answer, question, url, post_type="问答帖")

    def parse_question_page(self, qid: str, log: Callable = None) -> dict:
        url = f"https://www.zhihu.com/question/{qid}"
        self._delay()
        soup = self._fetch_html(url, log)
        if soup is None:
            return {"_error": "fetch_failed"}
        data = self._extract_initial_data(soup)
        if data is None:
            return {"_error": "no_initialData"}
        entities = data.get("initialState", {}).get("entities", {})
        questions = entities.get("questions", {})
        question = questions.get(str(qid), {})
        return self._build_result({}, question, url, post_type="问题帖")

    def parse_article_page(self, post_id: str, log: Callable = None) -> dict:
        url = f"https://zhuanlan.zhihu.com/p/{post_id}"
        self._delay()
        soup = self._fetch_html(url, log)
        if soup is None:
            return {"_error": "fetch_failed"}
        data = self._extract_initial_data(soup)
        if data is None:
            return {"_error": "no_initialData"}
        # entities.articles（新版）
        entities = data.get("initialState", {}).get("entities", {})
        articles = entities.get("articles", {})
        article = articles.get(str(post_id), {})
        if article:
            return self._build_result(article, {}, url, is_article=True, post_type="专栏文章")
        # initialData.post（旧版）
        init = data.get("initialState", {}) or data.get("initialData", {}) or data
        post = init.get("post", {}) or data.get("post", {})
        if post:
            return self._build_result(post, {}, url, is_article=True, post_type="专栏文章")
        return {"_error": "article_not_found"}

    # ── 字段映射 ─────────────────────────────────

    def _build_result(self, answer_or_article: dict, question: dict, url: str,
                      is_article: bool = False, post_type: str = "") -> dict:
        author = answer_or_article.get("author", {})
        if isinstance(author, str):
            author = {}
        content_html = answer_or_article.get("content", "")
        content_text = clean_text(self._strip_html(content_html))
        ts = (answer_or_article.get("createdTime") or
              answer_or_article.get("created_time") or
              answer_or_article.get("publishedTime") or 0)
        if isinstance(ts, str):
            try: ts = int(ts)
            except ValueError:
                m = re.search(r'\d+', ts); ts = int(m.group()) if m else 0
        time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else ""
        voteup = answer_or_article.get("voteupCount") or answer_or_article.get("voteup_count") or 0
        comments = answer_or_article.get("commentCount") or answer_or_article.get("comment_count") or 0
        q_title = clean_text(question.get("title", ""))
        q_detail = clean_text(self._strip_html(question.get("detail", "")))
        q_visits = question.get("visitCount") or question.get("visit_count") or 0
        q_answers = question.get("answerCount") or question.get("answer_count") or 0
        q_comments = question.get("commentCount") or question.get("comment_count") or 0
        topics = question.get("topics", []) or answer_or_article.get("topics", []) or []
        keywords = ", ".join(t.get("name", "") for t in topics) if topics else ""
        return {
            "关键词": keywords,
            "帖子类型": post_type,
            "问题被浏览次数": q_visits,
            "问题回答个数": q_answers,
            "问题评论个数": q_comments,
            "问题标题": q_title,
            "问题内容": q_detail,
            "答主昵称": author.get("name", ""),
            "回答时间": time_str,
            "赞同数": voteup,
            "评论数": comments,
            "回答内容": content_text,
            "问答链接": url,
            "_error": None,
        }

    # ── 主入口 ──────────────────────────────────

    def scrape(self, url: str, log: Callable = None) -> dict:
        """爬取单条链接，返回 12 字段字典"""
        url_type = self.categorize_url(url)
        qid, aid = self.extract_ids(url)

        try:
            if url_type == "answer" and qid and aid:
                result = self.parse_answer_page(qid, aid, log)
            elif url_type == "question" and qid:
                result = self.parse_question_page(qid, log)
            elif url_type == "article" and aid:
                result = self.parse_article_page(aid, log)
            elif url_type == "video":
                _write(log, f"  ⏭️ VIDEO跳过 — {url[:70]}")
                result = {"_error": "video_skipped", "帖子类型": "视频"}
            else:
                _write(log, f"  ❌ 未知类型 — {url[:70]}")
                result = {"_error": f"unknown: {url_type}"}
        except Exception as e:
            _write(log, f"  ❌ 异常 — {url[:70]} | {e}")
            result = {"_error": f"exception: {e}"}

        base = {
            "关键词": "", "帖子类型": "", "问题被浏览次数": 0, "问题回答个数": 0, "问题评论个数": 0,
            "问题标题": "", "问题内容": "", "答主昵称": "", "回答时间": "",
            "赞同数": 0, "评论数": 0, "回答内容": "", "问答链接": url,
            "_error": None,
        }
        base.update(result)
        return base

    # ── 工具 ────────────────────────────────────

    @staticmethod
    def _strip_html(html_text: str) -> str:
        if not html_text: return ""
        text = re.sub(r'<br\s*/?>', '\n', html_text)
        text = re.sub(r'</p>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        return html_mod.unescape(text)


def _write(log: Callable, msg: str):
    """安全调用日志函数"""
    if log:
        try:
            log(msg)
        except Exception:
            print(msg)
    else:
        print(msg)


# ──────────────────────────────────────────────
# 批量爬取 & 进度管理
# ──────────────────────────────────────────────

def load_links_from_csv(csv_path: Path) -> list[str]:
    """从 CSV 读取所有链接（兼容跨行记录）"""
    import csv
    links = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        link_col = 1
        for i, h in enumerate(header):
            if "内容" in h.strip().replace("﻿", ""):
                link_col = i; break
        current = None
        for row in reader:
            has_link = len(row) > link_col and row[link_col].strip().startswith("http")
            if has_link:
                if current is not None:
                    links.append(current[link_col].strip() if len(current) > link_col else "")
                current = row
        if current is not None:
            links.append(current[link_col].strip() if len(current) > link_col else "")
    return [l for l in links if l]


def run_batch_scrape(
    input_csv: Path,
    output_csv: Path,
    cookie: str = None,
    resume: bool = True,
):
    """批量爬取主函数"""
    from tqdm import tqdm
    import csv

    # ── 加载链接 ──
    links = load_links_from_csv(input_csv)
    print(f"\n{'='*60}")
    print(f"知乎内容爬虫")
    print(f"{'='*60}")
    print(f"📂 输入: {input_csv.name}  ({len(links)} 条链接)")
    type_counts = {}
    for url in links:
        t = ZhihuScraper.categorize_url(url)
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"   类型: " + " | ".join(f"{k}={v}" for k, v in sorted(type_counts.items(), key=lambda x: -x[1])))

    # ── 断点续爬 ──
    processed_urls = set()
    if resume and output_csv.exists():
        with open(output_csv, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                u = row.get("问答链接", "").strip()
                if u: processed_urls.add(u)
        print(f"📥 已处理: {len(processed_urls)} 条（断点续爬）")

    pending = [(i, url) for i, url in enumerate(links) if url not in processed_urls]
    if not pending:
        print("✅ 所有链接已处理完毕")
        return
    print(f"📋 待处理: {len(pending)} 条")
    print(f"{'='*60}\n")

    # ── 初始化 ──
    scraper = ZhihuScraper(cookie)
    fieldnames = [
        "关键词", "帖子类型", "问题被浏览次数", "问题回答个数", "问题评论个数",
        "问题标题", "问题内容", "答主昵称", "回答时间",
        "赞同数", "评论数", "回答内容", "问答链接",
    ]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    file_mode = "a" if resume and output_csv.exists() else "w"
    out_file = open(output_csv, file_mode, encoding="utf-8-sig", newline="")
    writer = csv.DictWriter(out_file, fieldnames=fieldnames)
    if file_mode == "w":
        writer.writeheader()
        out_file.flush()

    # ── tqdm 进度条（使用 sys.stderr 避免 conda run 缓冲 stdout）──
    import sys
    pbar = tqdm(
        total=len(pending),
        desc="爬取进度",
        unit="条",
        ncols=100,
        mininterval=0.5,
        file=sys.stderr,
        bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]",
    )

    success = 0
    failed = 0

    for idx, url in pending:
        # 处理本条 — scrape 内部日志通过 tqdm.write 输出
        result = scraper.scrape(url, log=pbar.write)

        err = result.get("_error")
        if err:
            failed += 1
            short = url.split("/")[-1][:20]
            pbar.write(f"  ❌ [{short}] {err}")
        else:
            success += 1
            vote_str = f"赞{result['赞同数']}" if result['赞同数'] else ""
            cmt_str = f"评{result['评论数']}" if result['评论数'] else ""
            stats = " ".join(x for x in [vote_str, cmt_str] if x)
            title = result['问题标题'] or result['答主昵称'] or ""
            ptype = result.get('帖子类型', '')
            pbar.write(f"  ✅ [{ptype}] {title[:30]}  {stats}")

        # 写入 CSV
        row = {k: result.get(k, "") for k in fieldnames}
        writer.writerow(row)
        out_file.flush()

        # 更新进度条后缀
        pbar.set_postfix_str(f"✔{success} ✘{failed}")
        pbar.update(1)

    pbar.close()
    out_file.close()

    print(f"\n{'='*60}")
    print(f"✅ 批量爬取完成")
    print(f"   成功: {success}  失败: {failed}  总请求: {scraper._request_count}")
    print(f"   输出: {output_csv}")
    print(f"{'='*60}")
