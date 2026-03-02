#!/usr/bin/env python3
"""
少数派文章搜索与详情获取

通过少数派搜索 API 获取工具/产品相关文章，支持获取文章完整正文。
无需认证，无需 Token，直接 GET 请求即可。

Usage:
    # 搜索文章列表
    python3 sspai_search.py --keyword "效率工具"
    python3 sspai_search.py --keyword "AI工具推荐"
    python3 sspai_search.py --keyword "独立开发者" --limit 20

    # 获取单篇文章详情
    python3 sspai_search.py --detail 60079
    python3 sspai_search.py --detail 60079 73051 55239
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import SEARCH_RESULTS_DIR, ensure_dirs

RESULT_FILE = os.path.join(SEARCH_RESULTS_DIR, "sspai_results.txt")

SEARCH_API = "https://sspai.com/api/v1/search/all/info/get"
DETAIL_API = "https://sspai.com/api/v1/article/info/get"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)

# 默认搜索关键词列表（与产品/工具发现相关）
DEFAULT_KEYWORDS = ["效率工具", "独立开发", "小工具推荐"]


def _ensure_output_dir():
    ensure_dirs()


def _request_json(url, referer="https://sspai.com/"):
    """发送 GET 请求并返回 JSON。"""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Referer": referer,
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"⚠️ 少数派 API error {e.code}: {url}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"⚠️ Network error: {e.reason}", file=sys.stderr)
        return None


def search_sspai(keyword, etime=None):
    """搜索少数派文章。"""
    if etime is None:
        etime = int(time.time())
    params = urllib.parse.urlencode({
        "title": keyword,
        "search_types": "",
        "stime": 0,
        "etime": etime,
    })
    url = f"{SEARCH_API}?{params}"
    referer = f"https://sspai.com/search?q={urllib.parse.quote(keyword)}"
    return _request_json(url, referer)


def fetch_article_detail(article_id):
    """获取单篇文章的完整详情（含正文）。

    Args:
        article_id: 文章 ID（数字）

    Returns:
        dict with article data including 'body' (HTML), 'title', 'tags', etc.
    """
    params = urllib.parse.urlencode({
        "id": article_id,
        "support_webp": "true",
        "view": "second",
    })
    url = f"{DETAIL_API}?{params}"
    referer = f"https://sspai.com/post/{article_id}"
    resp = _request_json(url, referer)
    if not resp or resp.get("error", -1) != 0:
        return None
    return resp.get("data", {})


def html_to_text(html):
    """简易 HTML → 纯文本转换。"""
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"</h[1-6]>", "\n\n", text)
    text = re.sub(r"</li>", "\n", text)
    text = re.sub(r"<hr\s*/?>", "\n---\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    # 合并连续空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_articles(response):
    """从 API 响应中提取文章列表。"""
    if not response or response.get("error", -1) != 0:
        return []
    data = response.get("data", {})
    return data.get("articles", [])


def format_as_text(all_articles, keywords_used):
    """将文章列表格式化为纯文本。"""
    lines = [
        f"少数派文章搜索结果 — 关键词: {', '.join(keywords_used)}",
        "=" * 60,
        "",
    ]

    # 去重（同一文章可能被不同关键词命中）
    seen_ids = set()
    unique_articles = []
    for a in all_articles:
        aid = a.get("id", 0)
        if aid not in seen_ids:
            seen_ids.add(aid)
            unique_articles.append(a)

    # 按 like_count 降序排列
    unique_articles.sort(key=lambda a: a.get("like_count", 0), reverse=True)

    for i, a in enumerate(unique_articles, 1):
        title = a.get("title", "(no title)")
        slug = a.get("slug", "")
        aid = a.get("id", "")
        summary = a.get("summary", "")
        likes = a.get("like_count", 0)
        comments = a.get("comment_count", 0)
        released = a.get("released_time", 0)

        # 构建链接
        url = f"https://sspai.com/post/{aid}" if aid else ""

        date_str = ""
        if released:
            try:
                date_str = datetime.fromtimestamp(released).strftime("%Y-%m-%d")
            except (OSError, ValueError):
                date_str = str(released)

        # 作者
        author_info = a.get("author", {})
        author = author_info.get("nickname", "N/A") if author_info else "N/A"

        lines.append(f"#{i} {title}")
        lines.append(f"  作者: {author}  👍 {likes}  💬 {comments}  日期: {date_str}")
        if summary:
            # 截断过长摘要
            if len(summary) > 200:
                summary = summary[:200] + "..."
            lines.append(f"  {summary}")
        if url:
            lines.append(f"  {url}")
        lines.append("")

    lines.append(f"共 {len(unique_articles)} 篇文章（已去重、按点赞数排序）")
    return "\n".join(lines)


def format_detail_as_text(detail):
    """将文章详情格式化为纯文本。"""
    title = detail.get("title", "(no title)")
    aid = detail.get("id", "")
    body_html = detail.get("body", "")
    keywords = detail.get("keywords", "")
    summary = detail.get("summary", "")

    # 作者
    author_info = detail.get("author", {})
    author = author_info.get("nickname", "N/A") if author_info else "N/A"

    # 互动数据
    counts = detail.get("article_count", {})
    likes = counts.get("like_count", 0)
    comments = counts.get("comment_count", 0)
    views = counts.get("views_count", 0)

    released = detail.get("released_time", 0)
    date_str = ""
    if released:
        try:
            date_str = datetime.fromtimestamp(released).strftime("%Y-%m-%d")
        except (OSError, ValueError):
            date_str = str(released)

    # 标签
    tags = detail.get("tags", [])
    tag_names = [t.get("title", "") for t in tags if t.get("title")]

    body_text = html_to_text(body_html)

    lines = [
        f"{'=' * 60}",
        f"📄 {title}",
        f"{'=' * 60}",
        f"作者: {author}  日期: {date_str}",
        f"👍 {likes}  💬 {comments}  👀 {views}",
    ]
    if tag_names:
        lines.append(f"标签: {', '.join(tag_names)}")
    if keywords:
        lines.append(f"关键词: {keywords}")
    lines.append(f"链接: https://sspai.com/post/{aid}")
    lines.append("")
    if summary:
        lines.append(f"摘要: {summary}")
        lines.append("")
    lines.append("-" * 60)
    lines.append(body_text)
    lines.append("-" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="少数派文章搜索与详情获取")
    parser.add_argument(
        "--keyword", type=str, default=None,
        help="搜索关键词（单个）"
    )
    parser.add_argument(
        "--keywords", nargs="+", default=None,
        help="多个搜索关键词"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="限制输出文章数量"
    )
    parser.add_argument(
        "--detail", nargs="+", type=int, default=None,
        help="获取文章详情，传入一个或多个文章 ID"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="输出文件路径（默认 data/search-results/sspai_results.txt）"
    )
    args = parser.parse_args()

    _ensure_output_dir()

    # 模式一：获取文章详情
    if args.detail:
        all_text = []
        for aid in args.detail:
            print(f"📖 获取文章详情: {aid}...", file=sys.stderr, flush=True)
            detail = fetch_article_detail(aid)
            if detail:
                text = format_detail_as_text(detail)
                all_text.append(text)
                print(f"  → {detail.get('title', '?')}", file=sys.stderr, flush=True)
            else:
                print(f"  ⚠️ 未能获取文章 {aid}", file=sys.stderr)
            if len(args.detail) > 1:
                time.sleep(0.5)

        if not all_text:
            print("❌ 未能获取任何文章详情", file=sys.stderr)
            sys.exit(1)

        output = "\n\n".join(all_text)
        detail_file = args.output or os.path.join(SEARCH_RESULTS_DIR, "sspai_detail.txt")
        with open(detail_file, "w", encoding="utf-8") as f:
            f.write(output)
        print(output)
        print(f"\n📄 详情已保存到 {detail_file}", file=sys.stderr)
        return

    # 模式二：搜索文章列表
    if args.keyword:
        keywords = [args.keyword]
    elif args.keywords:
        keywords = args.keywords
    else:
        keywords = DEFAULT_KEYWORDS

    all_articles = []
    for kw in keywords:
        print(f"🔍 搜索少数派: {kw}...", file=sys.stderr, flush=True)
        resp = search_sspai(kw)
        articles = extract_articles(resp)
        print(f"  → 获取 {len(articles)} 篇文章", file=sys.stderr, flush=True)
        all_articles.extend(articles)

        # 多关键词搜索间加短暂延迟
        if len(keywords) > 1:
            time.sleep(0.5)

    if not all_articles:
        print("❌ 未获取到任何文章", file=sys.stderr)
        sys.exit(1)

    # 限制数量
    if args.limit:
        # 先去重排序再截断
        seen_ids = set()
        unique = []
        for a in all_articles:
            aid = a.get("id", 0)
            if aid not in seen_ids:
                seen_ids.add(aid)
                unique.append(a)
        unique.sort(key=lambda a: a.get("like_count", 0), reverse=True)
        all_articles = unique[:args.limit]

    text = format_as_text(all_articles, keywords)

    output_file = args.output or RESULT_FILE
    _ensure_output_dir()
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print(text)
    print(f"\n📄 结果已保存到 {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
