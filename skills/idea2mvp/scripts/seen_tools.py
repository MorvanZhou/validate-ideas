#!/usr/bin/env python3
"""
已推荐工具的去重记录管理

存储格式：JSON Lines（.jsonl），每行一条记录：
  {"date": "2026-03-02", "name": "ToolName", "desc": "一句话定位"}

使用方式：

  # 读取（默认只返回最近 90 天的记录，自动清理过期条目）
  python3 scripts/seen_tools.py read
  python3 scripts/seen_tools.py read --days 180

  # 写入（追加一条或多条记录，日期自动填充为今天）
  python3 scripts/seen_tools.py add --tools "ToolA|一句话定位" "ToolB|描述"

  # 批量写入（从 JSON 字符串追加，适合程序调用）
  python3 scripts/seen_tools.py add --json '[{"name":"ToolA","desc":"描述"}]'
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import DATA_DIR, ensure_dirs

SEEN_FILE = os.path.join(DATA_DIR, "seen-tools.jsonl")

# 旧版 markdown 文件路径（自动迁移用）
_LEGACY_MD = os.path.join(DATA_DIR, "seen-tools.md")

DEFAULT_RETENTION_DAYS = 90


# ---------------------------------------------------------------------------
# 核心函数
# ---------------------------------------------------------------------------

def _migrate_legacy_md():
    """将旧版 seen-tools.md 迁移为 .jsonl 格式。"""
    if not os.path.exists(_LEGACY_MD):
        return
    entries = []
    current_date = None
    with open(_LEGACY_MD, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("## "):
                # 日期行，如 "## 2026-03-02"
                current_date = line[3:].strip()
            elif line.startswith("- ") and current_date:
                # 工具行，如 "- ToolName — 描述"
                content = line[2:].strip()
                if " — " in content:
                    name, desc = content.split(" — ", 1)
                elif " - " in content:
                    name, desc = content.split(" - ", 1)
                else:
                    name, desc = content, ""
                entries.append({
                    "date": current_date,
                    "name": name.strip(),
                    "desc": desc.strip(),
                })
    if entries:
        ensure_dirs()
        with open(SEEN_FILE, "a", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    os.remove(_LEGACY_MD)
    print(f"📦 已将 seen-tools.md（{len(entries)} 条）迁移到 seen-tools.jsonl", flush=True)


def read_seen_tools(days=DEFAULT_RETENTION_DAYS):
    """读取最近 N 天的已推荐工具，同时清理过期条目。

    Returns:
        list[dict]: 有效记录列表，每条 {"date", "name", "desc"}
    """
    _migrate_legacy_md()

    if not os.path.exists(SEEN_FILE):
        return []

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    kept = []
    expired_count = 0

    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("date", "") >= cutoff:
                kept.append(entry)
            else:
                expired_count += 1

    # 如果有过期条目，回写精简后的文件
    if expired_count > 0:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            for entry in kept:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return kept


def add_seen_tools(tools):
    """追加工具记录。

    Args:
        tools: list[dict]，每条至少包含 "name"，可选 "desc" 和 "date"。
               缺省 date 自动填充为今天。
    """
    ensure_dirs()
    today = datetime.now().strftime("%Y-%m-%d")
    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        for tool in tools:
            entry = {
                "date": tool.get("date", today),
                "name": tool["name"],
                "desc": tool.get("desc", ""),
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="已推荐工具去重记录管理")
    sub = parser.add_subparsers(dest="command")

    # read
    read_p = sub.add_parser("read", help="读取近期已推荐工具（自动清理过期）")
    read_p.add_argument("--days", type=int, default=DEFAULT_RETENTION_DAYS,
                        help=f"保留天数（默认 {DEFAULT_RETENTION_DAYS}）")

    # add
    add_p = sub.add_parser("add", help="追加工具记录")
    add_p.add_argument("--tools", nargs="+", metavar="NAME|DESC",
                       help='工具列表，格式: "ToolName|一句话描述"')
    add_p.add_argument("--json", dest="json_str",
                       help='JSON 数组字符串: \'[{"name":"X","desc":"Y"}]\'')

    args = parser.parse_args()

    if args.command == "read":
        entries = read_seen_tools(days=args.days)
        if not entries:
            print("（无历史推荐记录）", flush=True)
        else:
            # 按日期分组输出
            by_date = {}
            for e in entries:
                by_date.setdefault(e["date"], []).append(e)
            for date in sorted(by_date.keys(), reverse=True):
                print(f"\n[{date}]")
                for e in by_date[date]:
                    desc = f" — {e['desc']}" if e.get("desc") else ""
                    print(f"  • {e['name']}{desc}")
            print(f"\n共 {len(entries)} 条记录（最近 {args.days} 天）", flush=True)

    elif args.command == "add":
        tools = []
        if args.tools:
            for t in args.tools:
                if "|" in t:
                    name, desc = t.split("|", 1)
                    tools.append({"name": name.strip(), "desc": desc.strip()})
                else:
                    tools.append({"name": t.strip()})
        if args.json_str:
            try:
                items = json.loads(args.json_str)
                if isinstance(items, list):
                    tools.extend(items)
            except json.JSONDecodeError as e:
                print(f"❌ JSON 解析失败: {e}", file=sys.stderr)
                sys.exit(1)
        if not tools:
            print("❌ 请提供 --tools 或 --json 参数", file=sys.stderr)
            sys.exit(1)
        add_seen_tools(tools)
        print(f"✅ 已追加 {len(tools)} 条记录", flush=True)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
