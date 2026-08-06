#!/usr/bin/env bash
# 新机器初始化：创建独立 .venv、安装依赖、重建 .claude 薄壳（.claude/ 不入 git）
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet pymupdf requests python-dotenv pytest playwright
.venv/bin/python -m playwright install chromium --only-shell

mkdir -p .claude/commands
cat > .claude/commands/paper.md <<'EOF'
---
description: 论文 PDF → 解读文章 → 公众号草稿箱（全流程）
---
严格按照本仓库 pipeline/PAPER_WORKFLOW.md 定义的工作流，处理论文：$ARGUMENTS
EOF

echo "setup 完成。请复制 .env.example 为 .env 并填入公众号凭据，"
echo "并确认本机公网 IP 已加入公众号后台的 API IP 白名单。"
