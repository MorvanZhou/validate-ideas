# 邮件通知 — 使用指南

## 概述

通过 `scripts/send_email.py` 将任意文本内容（搜索报告、验证结论、MVP 进度等）发送到用户邮箱。仅使用 Python 标准库（smtplib），无额外依赖。

## 前置条件

在 `.env.idea2mvp` 中配置以下参数：

```
EMAIL_SMTP_HOST=smtp.qq.com
EMAIL_SMTP_PORT=465
EMAIL_SENDER=your_email@qq.com
EMAIL_PASSWORD=your_auth_code
EMAIL_RECEIVER=receiver@example.com
```

## 使用方式

### 发送文本内容

```bash
python3 scripts/send_email.py --subject "工具探索报告" --body "报告正文..."
```

### 从文件读取内容发送（支持多个文件合并为一封邮件）

```bash
python3 scripts/send_email.py --subject "工具探索报告" --file tmp/ph_results.txt
python3 scripts/send_email.py --subject "全平台报告" --file tmp/ph_results.txt tmp/github_results.txt tmp/v2ex_results.txt
```

### 从 stdin 读取内容

```bash
cat tmp/ph_results.txt | python3 scripts/send_email.py --subject "Product Hunt 报告"
```

### 指定收件人（覆盖 `.env` 中的默认收件人）

```bash
python3 scripts/send_email.py --subject "报告" --body "内容" --to someone@example.com
```

## 触发时机

邮件发送**不会主动询问用户**，而是在以下条件同时满足时自动执行：

1. `.env.idea2mvp` 中 `EMAIL_SMTP_HOST`、`EMAIL_SENDER`、`EMAIL_PASSWORD`、`EMAIL_RECEIVER` 均已配置且非注释状态
2. 当前阶段有可发送的内容产出（报告、文档等）

如果未配置邮件参数，直接跳过，不询问用户。

### 各阶段触发点

- **阶段一**：工具探索报告生成后
- **阶段二**：可行性评估报告生成后
- **阶段三**：无自动触发（用户可主动要求发送）

## 常用邮箱 SMTP 配置

| 邮箱 | SMTP 地址 | 端口 | 授权码获取 |
|------|----------|------|-----------|
| QQ 邮箱 | smtp.qq.com | 465 | 设置 → 账户 → POP3/SMTP → 生成授权码 |
| Gmail | smtp.gmail.com | 465 | Google 账户 → 安全 → 应用专用密码 |
| 163 邮箱 | smtp.163.com | 465 | 设置 → POP3/SMTP → 开启并获取授权码 |
| Outlook | smtp.office365.com | 587 | 直接使用登录密码 |
