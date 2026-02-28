#!/usr/bin/env python3
"""
idea2mvp 脚本公共工具模块

提供 .env.idea2mvp 配置文件的自动创建和加载功能。
"""

import os

ENV_FILE = os.path.join(os.getcwd(), ".env.idea2mvp")

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
"""


def ensure_env_file():
    """确保 .env.idea2mvp 文件存在，不存在则创建模板并提示用户。"""
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
    """加载 .env.idea2mvp 配置文件到环境变量（不覆盖已有环境变量）。

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
