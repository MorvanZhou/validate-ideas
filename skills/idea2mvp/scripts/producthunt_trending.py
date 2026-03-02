#!/usr/bin/env python3
"""
Product Hunt Trending - 通过官方 API v2 获取热门产品

需要环境变量：PRODUCTHUNT_TOKEN（Developer Token）
获取方式：https://www.producthunt.com/v2/oauth/applications → 创建应用 → 获取 Developer Token

使用方式：
  python3 producthunt_trending.py
  python3 producthunt_trending.py --days 3 --limit 20
  python3 producthunt_trending.py --topic productivity --days 7

结果自动保存到 .skills-data/idea2mvp/data/search-results/ph_results.txt
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import load_env, SEARCH_RESULTS_DIR, ensure_dirs

API_URL = "https://api.producthunt.com/v2/api/graphql"
RESULT_FILE = os.path.join(SEARCH_RESULTS_DIR, "ph_results.txt")

GRAPHQL_QUERY = """
{
  posts(order: VOTES, postedAfter: "%sT00:00:00Z", postedBefore: "%sT23:59:59Z", after: "%s", topic: "%s") {
    nodes {
      id
      name
      tagline
      description
      votesCount
      createdAt
      featuredAt
      website
      url
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

GRAPHQL_QUERY_NO_TOPIC = """
{
  posts(order: VOTES, postedAfter: "%sT00:00:00Z", postedBefore: "%sT23:59:59Z", after: "%s") {
    nodes {
      id
      name
      tagline
      description
      votesCount
      createdAt
      featuredAt
      website
      url
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


def fetch_posts(token, date_after, date_before, topic=None, limit=30):
    """通过 PH API v2 获取产品列表。"""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Idea2MVP/1.0",
    }

    all_posts = []
    cursor = ""
    has_next = True

    while has_next and len(all_posts) < limit:
        if topic:
            query = GRAPHQL_QUERY % (date_after, date_before, cursor, topic)
        else:
            query = GRAPHQL_QUERY_NO_TOPIC % (date_after, date_before, cursor)

        body = json.dumps({"query": query}).encode("utf-8")
        req = urllib.request.Request(API_URL, data=body, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("❌ Token 无效或已过期，请检查 PRODUCTHUNT_TOKEN 环境变量", file=sys.stderr)
            elif e.code == 429:
                print("❌ API 请求频率超限，请稍后重试", file=sys.stderr)
            else:
                print(f"❌ API 错误 {e.code}: {e.read().decode()[:200]}", file=sys.stderr)
            return None
        except urllib.error.URLError as e:
            print(f"❌ 网络错误: {e.reason}", file=sys.stderr)
            return None

        if "errors" in data:
            print(f"❌ GraphQL 错误: {data['errors'][0].get('message', '')}", file=sys.stderr)
            return None

        posts_data = data.get("data", {}).get("posts", {})
        nodes = posts_data.get("nodes", [])
        all_posts.extend(nodes)

        page_info = posts_data.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor", "")

    # 按票数排序取 top N
    all_posts.sort(key=lambda x: x.get("votesCount", 0), reverse=True)
    return all_posts[:limit]


def format_as_text(posts, date_after, date_before, topic=None):
    """将产品列表格式化为纯文本摘要。"""
    title = f"Product Hunt 热门产品 ({date_after} ~ {date_before})"
    if topic:
        title += f" [topic: {topic}]"
    lines = [title, "=" * 50, ""]

    for i, p in enumerate(posts, 1):
        desc = p.get("description", "") or ""
        if len(desc) > 150:
            desc = desc[:150] + "..."
        votes = p.get("votesCount", 0)
        featured = "✅ Featured" if p.get("featuredAt") else ""

        lines.append(f"#{i} {p['name']} ({votes} votes) {featured}".strip())
        lines.append(f"  {p.get('tagline', '')}")
        if desc:
            lines.append(f"  {desc}")
        if p.get("website"):
            lines.append(f"  Website: {p['website']}")
        lines.append(f"  {p.get('url', '')}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Product Hunt 热门产品获取（官方 API v2）")
    parser.add_argument("--days", type=int, default=1,
                        help="获取最近 N 天的产品 (default: 1)")
    parser.add_argument("--limit", type=int, default=15,
                        help="展示产品数量上限 (default: 15)")
    parser.add_argument("--topic", type=str, default=None,
                        help="按 topic 筛选，如 productivity, developer-tools, artificial-intelligence")
    args = parser.parse_args()

    load_env()
    token = os.environ.get("PRODUCTHUNT_TOKEN")
    if not token:
        print(
            "⚠️ 未配置 PRODUCTHUNT_TOKEN，无法使用 API。\n"
            "请改用 web_search 搜索 Product Hunt 相关信息，推荐搜索词：\n"
            "  - \"Product Hunt\" best new tools {当月} {当年}\n"
            "  - \"Product Hunt\" trending productivity tools {当年}\n"
            "  - site:producthunt.com top products this week\n\n"
            "如需配置 Token：\n"
            "  1. 访问 https://www.producthunt.com/v2/oauth/applications\n"
            "  2. 创建应用，获取 Developer Token\n"
            "  3. 在 .skills-data/idea2mvp/.env 中写入：PRODUCTHUNT_TOKEN=your_token",
            file=sys.stderr,
        )
        sys.exit(1)

    now = datetime.now(timezone.utc)
    date_before = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    date_after = (now - timedelta(days=args.days)).strftime("%Y-%m-%d")

    topic_str = f" [topic: {args.topic}]" if args.topic else ""
    print(f"🔍 获取 Product Hunt 热门产品 ({date_after} ~ {date_before}){topic_str}...", file=sys.stderr)

    posts = fetch_posts(token, date_after, date_before, args.topic, args.limit)
    if posts is None:
        sys.exit(1)

    if not posts:
        print("💡 该时间范围内未找到产品", file=sys.stderr)
        sys.exit(1)

    text = format_as_text(posts, date_after, date_before, args.topic)
    ensure_dirs()
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\n📄 结果已保存到 {RESULT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
