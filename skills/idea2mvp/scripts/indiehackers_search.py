#!/usr/bin/env python3
"""
Indie Hackers 产品搜索

通过 Indie Hackers 内置的 Algolia 搜索 API 获取独立开发者产品信息。
无需认证，无需 Token，直接 POST 请求即可。

Usage:
    # 搜索产品
    python3 indiehackers_search.py --keyword "AI tool"
    python3 indiehackers_search.py --keyword "productivity"
    python3 indiehackers_search.py --keywords "newsletter" "SaaS" "automation"
    python3 indiehackers_search.py --keyword "developer tools" --limit 10
    python3 indiehackers_search.py --keyword "AI" --min-revenue 100
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import SEARCH_RESULTS_DIR, ensure_dirs

RESULT_FILE = os.path.join(SEARCH_RESULTS_DIR, "ih_results.txt")

# Algolia search-only credentials (public, embedded in IH frontend)
ALGOLIA_APP_ID = "N86T1R3OWZ"
ALGOLIA_API_KEY = "5140dac5e87f47346abbda1a34ee70c3"
ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/products/query"

DEFAULT_KEYWORDS = ["productivity tool", "AI tool", "developer tool", "side project"]


def _ensure_output_dir():
    ensure_dirs()


def search_products(keyword, hits_per_page=20):
    """搜索 Indie Hackers 产品。

    Args:
        keyword: 搜索关键词
        hits_per_page: 每页返回数量（最大 1000）

    Returns:
        dict with 'hits' list, 'nbHits' total count, etc.
    """
    payload = json.dumps({
        "query": keyword,
        "hitsPerPage": hits_per_page,
    }).encode("utf-8")

    headers = {
        "X-Algolia-Application-Id": ALGOLIA_APP_ID,
        "X-Algolia-API-Key": ALGOLIA_API_KEY,
        "Content-Type": "application/json",
        "Referer": "https://www.indiehackers.com/",
    }

    req = urllib.request.Request(ALGOLIA_URL, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"⚠️ Algolia API error {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"⚠️ Network error: {e.reason}", file=sys.stderr)
        return None


def parse_tags(tags):
    """解析 _tags 列表，提取结构化信息。"""
    info = {
        "verticals": [],
        "revenue_model": "",
        "funding": "",
        "commitment": "",
        "employees": "",
        "platform": [],
    }
    for tag in (tags or []):
        if tag.startswith("vertical-"):
            info["verticals"].append(tag.replace("vertical-", ""))
        elif tag.startswith("revenue-model-"):
            info["revenue_model"] = tag.replace("revenue-model-", "")
        elif tag.startswith("funding-"):
            if not info["funding"]:
                info["funding"] = tag.replace("funding-", "")
        elif tag.startswith("commitment-"):
            info["commitment"] = tag.replace("commitment-", "")
        elif tag.startswith("employees-"):
            info["employees"] = tag.replace("employees-", "")
        elif tag.startswith("platform-"):
            info["platform"].append(tag.replace("platform-", ""))
    return info


def format_as_text(all_products, keywords_used, min_revenue=0):
    """将产品列表格式化为纯文本。"""
    lines = [
        f"Indie Hackers 产品搜索结果 — 关键词: {', '.join(keywords_used)}",
        "=" * 60,
        "",
    ]

    # 去重（同一产品可能被不同关键词命中）
    seen_ids = set()
    unique = []
    for p in all_products:
        pid = p.get("productId", p.get("objectID", ""))
        if pid and pid not in seen_ids:
            seen_ids.add(pid)
            if p.get("revenue", 0) >= min_revenue:
                unique.append(p)

    # 按 revenue 降序排列
    unique.sort(key=lambda p: (p.get("revenue", 0) or 0), reverse=True)

    for i, p in enumerate(unique, 1):
        name = p.get("name", "(unknown)")
        tagline = p.get("tagline", "")
        description = p.get("description", "")
        revenue = p.get("revenue", 0) or 0
        website = p.get("websiteUrl", "")
        pid = p.get("productId", p.get("objectID", ""))
        followers = p.get("numFollowers", 0) or 0

        # 时间
        start_date = p.get("startDateStr", "")

        # 解析标签
        tag_info = parse_tags(p.get("_tags", []))
        verticals = ", ".join(tag_info["verticals"]) if tag_info["verticals"] else ""
        platforms = ", ".join(tag_info["platform"]) if tag_info["platform"] else ""
        rev_model = tag_info["revenue_model"]
        funding = tag_info["funding"]
        commitment = tag_info["commitment"]

        ih_url = f"https://www.indiehackers.com/product/{pid}" if pid else ""

        lines.append(f"#{i} {name}")
        meta_parts = []
        if revenue > 0:
            meta_parts.append(f"💰 ${revenue}/mo")
        else:
            meta_parts.append("💰 $0/mo")
        if followers:
            meta_parts.append(f"👥 {followers} followers")
        if start_date:
            meta_parts.append(f"📅 {start_date}")
        lines.append(f"  {' | '.join(meta_parts)}")

        if tagline:
            lines.append(f"  {tagline}")

        detail_parts = []
        if verticals:
            detail_parts.append(f"领域: {verticals}")
        if platforms:
            detail_parts.append(f"平台: {platforms}")
        if rev_model:
            detail_parts.append(f"模式: {rev_model}")
        if funding:
            detail_parts.append(f"融资: {funding}")
        if commitment:
            detail_parts.append(f"投入: {commitment}")
        if detail_parts:
            lines.append(f"  {' | '.join(detail_parts)}")

        if description:
            desc = description if len(description) <= 200 else description[:200] + "..."
            lines.append(f"  {desc}")

        if website:
            lines.append(f"  🔗 {website}")
        if ih_url:
            lines.append(f"  📄 {ih_url}")
        lines.append("")

    lines.append(f"共 {len(unique)} 个产品（已去重、按月收入排序）")
    if min_revenue > 0:
        lines.append(f"（已过滤月收入 < ${min_revenue} 的产品）")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Indie Hackers 产品搜索")
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
        help="限制输出产品数量"
    )
    parser.add_argument(
        "--min-revenue", type=int, default=0,
        help="最低月收入过滤（美元）"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="输出文件路径（默认 data/search-results/ih_results.txt）"
    )
    args = parser.parse_args()

    # 确定关键词列表
    if args.keyword:
        keywords = [args.keyword]
    elif args.keywords:
        keywords = args.keywords
    else:
        keywords = DEFAULT_KEYWORDS

    all_products = []
    for kw in keywords:
        print(f"🔍 搜索 Indie Hackers: {kw}...", file=sys.stderr, flush=True)
        resp = search_products(kw, hits_per_page=50)
        if resp:
            hits = resp.get("hits", [])
            total = resp.get("nbHits", 0)
            print(f"  → 获取 {len(hits)} 个产品（共 {total} 个匹配）", file=sys.stderr, flush=True)
            all_products.extend(hits)
        else:
            print(f"  ⚠️ 搜索失败", file=sys.stderr)

        if len(keywords) > 1:
            time.sleep(0.3)

    if not all_products:
        print("❌ 未获取到任何产品", file=sys.stderr)
        sys.exit(1)

    # 去重 + 排序后截断
    if args.limit:
        seen_ids = set()
        unique = []
        for p in all_products:
            pid = p.get("productId", p.get("objectID", ""))
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                if p.get("revenue", 0) >= args.min_revenue:
                    unique.append(p)
        unique.sort(key=lambda p: (p.get("revenue", 0) or 0), reverse=True)
        all_products = unique[:args.limit]

    text = format_as_text(all_products, keywords, min_revenue=args.min_revenue)

    _ensure_output_dir()
    output_file = args.output or RESULT_FILE
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print(text)
    print(f"\n📄 结果已保存到 {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
