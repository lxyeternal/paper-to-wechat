# /paper 工作流：论文 PDF → 公众号草稿箱

输入：论文 PDF 路径。输出：公众号草稿箱中一篇图文草稿。
凭据在仓库根 `.env`，绝不打印。发布动作永远由用户在公众号后台手动完成。
所有 Python 命令用仓库的 `.venv/bin/python` 执行。

## 步骤

### 1. 建目录

- slug 规则：`YYYY-MM-<论文短名小写>`（如 `2026-08-malskillbench`）
- `mkdir -p papers/<slug>/assets` 并复制 PDF 为 `papers/<slug>/paper.pdf`

### 2. 读论文

- 用 Read 工具直接读 `paper.pdf`（分段读完全文），掌握：问题、挑战、方法、实验结果、局限。
- 提取元信息：英文原题、作者与机构、发表 venue、arXiv 链接、代码仓库链接（通常在摘要或脚注）。

### 3. 提图

- `.venv/bin/python scripts/extract_figures.py pages papers/<slug>/paper.pdf papers/<slug>/pages`
- 用 Read 目视各页 PNG，选定：1-2 张核心架构/方法图、1-3 张关键结果图。
- 写 `papers/<slug>/figspec.json`（bbox 单位为 PDF point；从 150dpi 页面图的像素坐标换算：`pt = px ÷ 150 × 72`），架构图 out 到 `assets/fig/`，结果图到 `assets/result/`。
- `.venv/bin/python scripts/extract_figures.py crop papers/<slug>/paper.pdf papers/<slug> papers/<slug>/figspec.json`
- `.venv/bin/python scripts/extract_figures.py header papers/<slug>/paper.pdf papers/<slug>/assets/header.png`
- 用 Read 逐一目视裁剪结果：图必须完整、无截断、无邻栏文字混入；不合格就调 bbox 重裁。

### 4. 写文稿

- 按 `templates/article_template.md` 的结构写 `papers/<slug>/article.md`。
- 叙事线：读者视角——整体干什么 / 解决什么问题 / 领域挑战 / 怎么做 / 结果如何 / 有何启发。
- 图插在对应章节，图注为中文、格式"图N：说明"。
- 「启发与点评」结合软件供应链安全领域上下文，写观点不写套话。
- title 中文 ≤64 字；digest ≤120 字；highlights 恰好 3 条、每条 ≤14 字。
- **去 AI 味（用户明确要求）**：正文和图注禁用破折号"——"（改用冒号、逗号或拆成两句；
  排版自动加的图注前缀"— "不算）。写完后 `grep -c "——" article.md` 自查，必须为 0。
- front matter 加 `collection:` 字段（不参与排版，纯提示）：从公众号已预设的合集中选一个，
  用户发布时照此手动勾选（草稿 API 不支持设置合集）。合集清单：
  「AI Agent 安全」（恶意 Skill、提示注入、MCP、Agent 控制面）；
  「恶意包与威胁情报」（PyPI/NPM 恶意包检测、测量、情报聚合）；
  「供应链攻击与防御」（攻击机理、事件复盘、防御机制、SBOM）；
  「开源与安全测量」（大规模实证研究、基准测评）。

### 5. 封面

- `.venv/bin/python scripts/render_cover.py --title-zh "<中文短题>" --title-en "<英文原题>" --venue "<venue>" --out papers/<slug>/assets/cover.png`
- 用 Read 目视封面，文字溢出则缩短标题重渲。

### 6. 排版 + 发布

- `.venv/bin/python scripts/render_article.py papers/<slug>`
- `.venv/bin/python scripts/wechat_publish.py papers/<slug>`
- 成功后告知用户去 公众号后台 → 内容管理 → 草稿箱 查看。

### 7. 修改重发

- 用户改完 `article.md` 后说"重新发布"：只重跑步骤 6 两条命令（`publish.json` 已有 `draft_media_id`，会走 `draft/update`，不产生重复草稿）。

## 失败恢复

- 每步产物都在 `papers/<slug>/` 内，从失败步骤继续，不从头跑。
- 40164 = IP 白名单失效，提示用户更新（脚本报错信息里有指引）。
- 换新机器：`bash scripts/setup.sh` 重装依赖并重建 `.claude/commands/paper.md` 薄壳。
