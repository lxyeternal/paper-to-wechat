# paper-to-wechat

「供应链安全前沿」公众号论文解读 pipeline：论文 PDF → 中文解读 + 配图 + 排版 → 公众号草稿箱。

## 用法

在 Claude Code 中：

```
/paper ~/Downloads/xxx.pdf
```

Claude Code 会按 `pipeline/PAPER_WORKFLOW.md` 完成全流程：读论文 → 提取配图（架构图/结果图/首页题头）→ 写中文解读 → 品牌封面 → 微信排版 → 进草稿箱。你只需最后在公众号后台点发布。

改稿后重发：编辑 `papers/<slug>/article.md`，对 Claude 说"重新发布"。

## 新机器初始化

```
bash scripts/setup.sh
cp .env.example .env   # 填入公众号 AppID/AppSecret
```

并在 公众号后台 → 设置与开发 → 开发接口管理 → API IP白名单 中加入本机公网 IP（`curl -s https://ifconfig.me`）。

## 结构

- `pipeline/PAPER_WORKFLOW.md` — /paper 工作流定义（Claude Code 执行手册）
- `scripts/` — 提图 / 封面 / 排版 / 发布 四个独立 CLI（用 `.venv/bin/python` 运行）
- `templates/` — 封面模板、排版主题、文章结构模板
- `papers/<slug>/` — 每篇论文的全部素材与产物（严格隔离）
- `tests/` — 脚本单元测试（`.venv/bin/python -m pytest tests/`）
