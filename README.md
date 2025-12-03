# 邮箱检查 Keepalive 工具

基于 Microsoft Graph 的自动化脚本：创建邮箱摘要任务、可选删除重复与过期任务，并支持一键清空包含 Planner 计划的组。

## 快速开始
- Python 3.10+，建议虚拟环境：`python -m venv .venv && .\.venv\Scripts\activate`
- 安装依赖：`pip install msal requests`
- 配置环境变量：复制 `.env.sample` 为 `.env`，填入真实值（不要提交 `.env`）。

关键环境变量：
- `CLIENT_ID` / `CLIENT_SECRET` / `TENANT_ID` / `USER_EMAIL` / `NOTIFICATION_EMAIL`
- `APP_SCOPE`、`DELEGATED_SCOPES`、`MAIL_PLAN_TITLE`
- `AUTH_MODE`（`app` 或 `delegated`），`REQUEST_TIMEOUT_SECONDS`，`MAX_DELETE_PER_RUN`，`CLEANUP_TIME_BUDGET_SECONDS`
- 可选：`MAIL_PLAN_GROUP`、`TASK_TITLE_PREFIX`、`ENABLE_OLD_CLEANUP`

## 运行
- keepalive（创建邮箱检查任务，仅保留最新一条；可选清理 7 天前任务）：`python main.py keepalive`
- 删除所有包含 Planner 计划的组（谨慎）：`python main.py delete_groups`

说明：
- 仅当设置 `ENABLE_OLD_CLEANUP=true` 时才会尝试清理 7 天前任务。
- `CLEANUP_TIME_BUDGET_SECONDS` 用于限制清理耗时，避免长时间阻塞。

## 测试
- 运行单元测试：`python -m pytest -q`
