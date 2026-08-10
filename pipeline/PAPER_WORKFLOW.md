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

**图表完整性检查（强制，不可跳过）**：用 Read 工具**逐一**打开每一张裁剪产物（含 header），
按下面的清单逐张核对，任何一条不满足就调整 bbox 重裁并重新 Read，直到全部通过：

- **无截断**：图/表的四条边都在画面内，没有半个字、半行、半列、半个坐标轴被切掉。
  特别检查顶边和底边——多栏论文的图常常上边贴着正文，容易切掉标题行或第一行元素。
- **题头完整**：`header.png` 必须包含论文标题的**全部行**和**全部作者行**。
  很多论文作者排成两行或多行（如 3+2），只截到第一行是最常见的错误；
  用 `get_text("blocks")` 查出作者区块最大的 y1，bbox 底边取"该 y1 + 4pt"再到 Abstract 上沿之间。
- **纯图无杂质**：不含原文的图注/表注文字（图注由我们用中文另写）、不含相邻栏的正文、不含正文段落。
- **表格完整**：表头行、所有数据行、最右一列都在内，没有被切掉的单元格。
- **定位辅助**：拿不准边界时，用 `page.get_text("blocks")` 或 `page.get_drawings()` 打印
  目标区域的文本块与图形 bbox，据此定 bbox，不要凭页面缩略图估。

只有当每一张图都通过上述清单，才能进入下一步。

### 4. 写文稿

- 按 `templates/article_template.md` 的结构写 `papers/<slug>/article.md`。
- 叙事线：读者视角——整体干什么 / 解决什么问题 / 领域挑战 / 怎么做 / 结果如何 / 有何启发。
- 图插在对应章节，图注为中文、格式"图N：说明"。
- 「启发与点评」结合软件供应链安全领域上下文，写观点不写套话。
- title 中文 ≤64 字；digest ≤120 字；highlights 恰好 3 条、每条 ≤14 字。
- **去 AI 味（用户明确要求）**：正文和图注禁用破折号"——"（改用冒号、逗号或拆成两句；
  排版自动加的图注前缀"— "不算）。写完后 `grep -c "——" article.md` 自查，必须为 0。
- **安全术语按业界惯例（用户明确要求）**：one-day/N-day 写 `1day`（或 1-day），zero-day 写 `0day`，
  不要意译成"一日/零日"；CVE、RCE、POC、MCP 等固定术语保留英文/数字写法，不硬翻中文。
  写完 `grep -n "一日\|零日" article.md` 自查应为空。
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
