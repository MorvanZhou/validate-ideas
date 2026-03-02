#!/usr/bin/env python3
"""
idea2mvp 脚本公共工具模块

统一管理 skill 的运行时数据目录结构（遵循 .skills-data 规范）：

    <project_root>/.skills-data/idea2mvp/
        .env            — 配置文件（Token、偏好、邮件等）
        data/           — 持久化数据
            search-results/ — 各平台搜索结果（ph_results.txt、github_results.txt 等）
            user-profile.md、idea-brief/、报告等
        cache/          — 可安全删除的缓存（如浏览器数据）
        logs/           — 日志文件

skill 源码（SKILL.md、scripts/、references/）保持不可变。
"""

import os

# ---------------------------------------------------------------------------
# 核心路径
# ---------------------------------------------------------------------------

SKILL_NAME = "idea2mvp"

# 项目根目录（运行脚本时的工作目录）
PROJECT_ROOT = os.getcwd()

# 运行时数据根目录
SKILL_DATA_DIR = os.path.join(PROJECT_ROOT, ".skills-data", SKILL_NAME)

# 各子目录
DATA_DIR = os.path.join(SKILL_DATA_DIR, "data")
SEARCH_RESULTS_DIR = os.path.join(DATA_DIR, "search-results")
CACHE_DIR = os.path.join(SKILL_DATA_DIR, "cache")
LOGS_DIR = os.path.join(SKILL_DATA_DIR, "logs")

# 配置文件
ENV_FILE = os.path.join(SKILL_DATA_DIR, ".env")

# ---------------------------------------------------------------------------
# .env 模板
# ---------------------------------------------------------------------------

ENV_TEMPLATE = """\
# idea2mvp 配置文件
# 各平台 Token / API Key 及用户偏好统一在此配置

# Product Hunt Developer Token
# 获取方式：https://www.producthunt.com/v2/oauth/applications → 创建应用 → Developer Token
# PRODUCTHUNT_TOKEN=your_token_here

# 跳过 Product Hunt API 搜索（设为 true 则改用 web_search 替代）
# SKIP_PH_API=true

# GitHub Token（可选，提高 API 速率限制）
# 获取方式：https://github.com/settings/tokens → Generate new token
# GITHUB_TOKEN=your_token_here

# 跳过小红书 Playwright 浏览器搜索（设为 true 则直接跳过小红书搜索，小红书未开放公网搜索）
# SKIP_XHS_PLAYWRIGHT=true

# 邮件通知配置（用于 send_email.py 发送搜索报告等）
# EMAIL_SMTP_HOST=smtp.qq.com
# EMAIL_SMTP_PORT=465
# EMAIL_SENDER=your_email@qq.com
# EMAIL_PASSWORD=your_auth_code
# EMAIL_RECEIVER=receiver@example.com
"""


# ---------------------------------------------------------------------------
# 目录初始化
# ---------------------------------------------------------------------------

def ensure_dirs():
    """确保运行时数据目录结构存在。"""
    for d in (SKILL_DATA_DIR, DATA_DIR, SEARCH_RESULTS_DIR, CACHE_DIR, LOGS_DIR):
        os.makedirs(d, exist_ok=True)


def ensure_env_file():
    """确保 .env 文件存在，不存在则创建模板并提示用户。"""
    ensure_dirs()
    if os.path.exists(ENV_FILE):
        return
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(ENV_TEMPLATE)
    print(
        f"📝 已创建配置文件：{ENV_FILE}\n"
        "   请在其中填写所需的 Token / API Key。\n",
        flush=True,
    )


def load_env():
    """加载 .env 配置文件到环境变量（不覆盖已有环境变量）。

    自动调用 ensure_env_file() 确保文件存在。
    """
    ensure_env_file()
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
