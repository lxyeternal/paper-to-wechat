# 会议盘点工作流：接收名单 → 一期论文清单

输入：一个会议的官方接收论文列表。输出：公众号草稿箱里一篇按主题分组的清单文章。
和 PAPER_WORKFLOW 的关系：封面、排版、发布、去 AI 味规则全部复用，下面只写差异。

## 和单篇解读的根本差异

盘点文章的可信度全部押在**数据准确**上，一条编错的单位或一个不存在的标题，
比写得浅严重得多。所以规则是：**核实不到就不写进正表**，宁可少列。

## 步骤

### 1. 取全量标题，自己筛，不要让工具替你筛

- 数据源：`conf.researchr.org/track/<会议>/<轨道>` 的 Accepted Papers。
- **不要**丢一组关键词让抓取工具返回"相关的论文"。实测同样的关键词分多次问，
  返回的子集每次都不一样，会漏。正确做法是**按字母分段把全量标题抓下来**
  （"输出所有以 A 或 B 开头的标题，逐字，不要总结"），拿到完整清单后自己判断相关性。
- 抓取有长度上限，长列表会被截断。抓完务必问一句"页面内容是否被截断、列表到哪个字母为止"，
  截断了就在文章里**明写覆盖范围**，不要假装完整。
- 别忘了主轨之外的轨道：NIER、Industry Showcase、Tools and Datasets、Journal First。
- **抓取工具被 403 挡住时，用 Playwright 起一个 headless Chromium 直接取 `inner_text`**。
  usenix.org 对抓取工具返 403，但对真实浏览器正常放行，拿到全文后在本地解析，
  既没有长度截断也不经过模型转述，是四家里数据质量最好的一次。列表页结构通常很规整
  （标题 / 作者行 / "AVAILABLE MEDIA"），写十行解析器就能拿到全量 (title, authors)。
  **能本地解析就不要让抓取工具帮你筛**，这是这套流程里最重要的一条。

### 1.5 researchr 的两种页面，单位取法完全不同

会议开过或程序已出的（FSE、ICSE），用 **Program 页**：
`conf.researchr.org/track/<会议>/<轨道>`，HTML 里每位作者后面紧跟
`<span class="prog-aff">单位</span>`，一条正则就能拿到 (标题, 轨道, [(作者, 单位)])，
**单位是官方原文，不需要再去查作者主页**。同一篇论文在程序页会出现多次（会场视图、
轨道视图），==只有部分出现带 prog-aff，去重时要保留"带单位最多"的那一条==，
否则会拿到一条作者齐全但单位全空的记录。程序页还会把
"Distinguished Paper Award"这类奖项拼在标题文本末尾，解析时要剥掉并单独记下来，
获奖信息本身是很好的正文素材。

会议还没开的（ISSTA），只有 **Accepted Papers 页**，没有单位，只有指向
`/profile/<会议>/<id>` 的作者链接。这时逐个抓作者主页取 `Affiliation:` 字段，
**用带浏览器 User-Agent 的普通 HTTP 请求就行，不必起 Playwright，8 线程 150 个主页
不到一分钟**。主页里的 contributions 列表天然完成了交叉验证：链接是从这篇论文那一行
取的，profile id 唯一，不存在重名问题。

### 2. 核单位

- researchr 的作者主页 `conf.researchr.org/profile/<会议>/<姓名小写连写>` 会给单位。
- **必须交叉验证**：该主页列出的 ASE 论文里要包含目标论文，否则就是重名的另一个人。
  实测重名很常见，只看到单位就采用会写错。
- 主页设了私密、或重名对不上，就换一位共同作者再试；仍然核不到，把这篇挪到
  "同样相关但单位没核实到"那一节，只列标题。
- 本仓库已解读过的论文，单位直接从 `papers/<slug>/paper.pdf` 的题头取，最可靠。

### 3. 查重与串联

- 用 PAPER_WORKFLOW §0 的多信号查重，对照 `papers/` 和 `talks/`。
- **camera-ready 标题常和预印本不同**（实例：ASE 版 MalSkills = arXiv 版
  "Elementary, My Dear Watson"，同作者同系统），要靠作者名和系统名交叉确认。
- 已解读过的篇目在正文里标注出来，方便发布时在公众号编辑器里插站内超链接
  （超链接 → 公众号文章 → 搜标题）。草稿 API 拿不到已发布文章的 URL，
  `freepublish/batchget` 在订阅号上返回 48001 无权限，所以链接只能手动加。

### 4. 写稿

- `kind: roundup`（橙色，封面标签"会议盘点"）；`collection: 顶会论文清单`。
  **盘点不要放进「供应链攻击与防御」**：那个合集是深度解读，索引型内容混进去会被淹掉。
  合集在公众号后台按会议召开时间排序，读起来才像一份索引。
- 结构：本期说明（会议、来源、口径、**覆盖范围声明**）→ 按主题分组的清单 →
  "同样相关但没核实到"→ 一点观察。
- 每篇用**论文卡片**写，语法是一个 `### ` 开头的块，块内不空行：

  ```
  ### English Paper Title
  Author A, Author B, Author C | Institution X, Institution Y
  一段导读正文，可以用 **粗体** 和 ==红色重点==。
  ```

  首行是标题，次行用 `|` 分开作者名和单位，其余是导读。**作者名和单位一律保持英文原文，
  不要翻译成中文**，只有导读是中文（用户 2026-08 明确要求）。渲染成浅底卡片：
  左侧强调色竖条、左上角自动编号、作者行浅灰、单位行强调色、两行下面压一条分隔线。
  **清单类文章一定要用卡片**，十几条平铺下来读者分不清哪条是哪条，这是实测反馈。
- **导读的边界**：会议没开、全文多数未公开时，导读只能写标题和团队背景支撑得住的内容，
  不替作者把结论说满。已解读过的那几篇才写实际结论。
- 配图：论文清单没有现成图，用 Playwright 渲一张主题分布概览图（见本期 assets/overview.png 的做法）。

### 5-6. 封面、排版、发布

同 PAPER_WORKFLOW。`cover_stat` 填篇数（如 "12 篇"），`cover_stat_label` 填口径
（如 "ASE 2026 供应链相关论文"），走 B 版数据块正好合适。

## 写稿禁区（用户 2026-09 明确要求）

- **不要在盘点之间做排名式对比**（"四大安全会里只有 X 还在做 Y""这在另外三家看不到"）。
  草稿箱里同时压着多期，发布顺序由用户临时决定，==任何"另一期已经发过"的预设都可能不成立==。
  要跨会议对比就落到具体论文上（"CCS 2026 有一篇…"），别落到"那一期"。
- **正文不写流程自夸**（"数据质量最好的一期""没有截断、没有靠关键词猜"）。
  口径该交代的是范围和来源，不是我怎么抓的。自夸一旦和事实有出入，杀伤力比不写大得多。
- **`##`、`###`、`![]` 前后必须各留一个空行**。少一个空行，渲染器会把标题并进上一块，
  草稿里就是一坨裸 markdown。`render_article.py` 已加结构自检，会直接报错拦下。

## 附：跨年趋势盘点（2026-09 新增，2026-09-07 扩到八会）

盘点的一个变体：不是一届会议的清单，而是一个会议多年的方向趋势。已做十期：
安全四会（`2026-09-usenixsec/ccs/ndss/sp-10yr-trends`）、软工四会（`2026-09-icse/fse/ase/issta-10yr-trends`）、
两篇综合（`2026-09-security-4conf-synthesis`、`2026-09-se-4conf-synthesis`）。和单届盘点的差异：

### 数据

- USENIX 直接用 usenix.org 每届 `technical-sessions` 页：`scripts/fetch_usenix_sessions.py fetch/parse`，
  页面内联标题、单位、摘要、分会场名，逐年篇数要和官方接收数对上（2016 到 2025 为 72/85/100/113/157/246/256/422/417/438）。
- 其余七会按论文集 DOI 走 Crossref + OpenAlex：`scripts/confdata.py`（列全标题作者，再补摘要/单位/国家），
  副标题被 Crossref 截断的用 `scripts/fetch_subtitles.py` 从出版社页补（它最后会整体重写 papers.jsonl，跑的时候别动文件）。
  研究轨以外的轨道按分会场/页数剔除（正文不足 8 页视为非正式论文）。
- **完整性必须逐年和 DBLP 目录对一遍**（`dblp.org/db/conf/<conf>/<conf>20XX.html`，有 Anubis 反爬，
  curl 拿不到，用 Playwright 等 `li.entry` 出现后再取页面；按 `<li class="entry ` 切条目，
  读 `span.title` 和 `span[itemprop=pagination]`，`header.h2/h3` 是分会场名）。Crossref 论文集里混着
  keynote、industry、workshop、NIER，DBLP 的分区名能把它们认出来；FSE 2019 到 2023 的工业轨（每年 20 到 34 篇）
  和 ASE 2023 到 2025 的工业轨（每年 12 到 54 篇）就是这样剔掉的。研究轨录用清单也可以对 researchr 各届的
  `Accepted Papers` 表（标题会带 "[Remote]"、奖项后缀，要先去掉）。对完的总数要和官网公布的研究轨接收数一致。
- **几千篇的全量数据不进 git**：`.gitignore` 已排除 `roundups/*/data/raw/` 与 `roundups/*/data/*.jsonl`，
  留下的是 `labels.txt`、`stats.json`、`inst_stats.json`、`awards.md`、`verify.md`。

### 分类

- 两套分类都在 `roundups/_shared/`：`taxonomy_security.json`（18 方向）、`taxonomy_se.json`（15 方向），
  按 CFP 主题分区对齐，同一系列必须用同一套。**软工的 `chain` 是区块链与智能合约，不是供应链**；
  供应链论文分在 security / maint / human 里，文中单独拉一段。
- 规则："用大模型做某任务"归任务方向、大模型记次方向；只有研究代码大模型本身才记 llm4se / llm 主方向。
  这样能同时得到"任务份额"和"大模型渗透率"。
- 逐篇人工判定，标签写 `data/labels.txt`（`id cat [cat2]`），`scripts/merge_labels.py <data_dir>` 合并出
  `papers_labeled.jsonl`，`scripts/confstats.py <data_dir> <taxonomy.json>` 出 `stats.json` / `inst_stats.json`。

### 配图

- `scripts/mktrend.py <data> <assets> --conf "X" --partial 0|2026 --order ... --lines "名=cat+cat;..."`
  出 overview（小倍数柱图）、ai_rise（四条折线）、institutions、regions 四张；纵轴会按峰值自适应。
- 单会再加一张机构 × 方向热力图：`python3 scripts/mkheat.py <conf-key> <security|se> "<会议名>"` 出 `assets/heatmap.png`（前 15 家）。
- 综合篇的"判断类"配图用 `scripts/mkfind.py <security|se> <synthesis_dir>` 出 shift（方向涨跌哑铃图）/ types（论文类型构成）/
  awards（获奖倾向指数）/ aimethod（AI 作为方法的渗透）四张，并写 `data/findings.json`（还含方向集中度、新进入者比例、主次方向组合）。
  论文类型由 `scripts/ptype.py` 按标题摘要规则粗分（攻击 / 方法 / 测量 / 用户研究 / SoK，抽样准确率约八成，只看趋势），
  获奖论文由 `scripts/awards_match.py` 把各会 `data/awards.md` 对到数据库。
- 综合篇用 `scripts/mksynth.py <security|se> <assets>` 出 scale / compare / ai / china / heatmap 五张，
  数据库是四会 `papers_labeled.jsonl` 拼起来放在综合篇的 `data/` 下，这样 verify 也能跑。

### 写稿与核对

- 综合篇按"切面"组织而不是按方向罗列：方向涨跌 → 论文类型 → 获奖倾向 → 四家性格 → AI（对象与方法）→ 老方向题材更替 →
  供应链 → 机构地区 → 给投稿人的判断。每节先图后三到五条判断，单篇论文只作锚点；多维对比用 `@table`（每行 `- a | b | c`，
  首行表头，手机上五列以内、单元格十字以内最稳）。
- 逐会篇结构：LIST INFO（范围/来源/口径）→ 图 1 + `@stats` → BIG PICTURE（`####` 三个大迁移）→ 各方向
  （`@timeline` + `####` 阶段小标题 + 要点用 `- ` 列表）→ SUPPLY（单独一段）→ AWARDS → WHO → TAKEAWAYS。
- WHO 段写成"机构图谱"：图 3 单位榜 → 图 4 热力图 → 每个大方向一个 `####`（头部单位、团队和作者的"N 篇署名"、
  每家的路线、2 到 4 篇 `20XX 年 **标题**` 代表论文，★ 才叫杰出论文）→ `#### 人在动，方向跟着动` → 图 5 地区。
  素材用 `python3 scripts/confteams.py <conf-key> <security|se>` 生成的 `data/teams.txt`（机构 × 方向 × 作者 × 代表论文，
  不进 git），作者署名数统一指该作者在本会的署名总数。
  每个方向讲"曲线为什么这样走"，用占比不用绝对数；杰出论文要逐篇和 `data/awards.md` 对过再写"杰出论文"。
- **文中点名的每篇论文都要过 `scripts/verify_mentions.py <dir>`**，必须 0 flagged 才能发：
  它抽出所有加粗英文标题回数据库匹配（去 HTML 标签、LaTeX、大小写），并检查加粗前 160 字内最近的
  "20XX 年 / 20XX Cycle" 是否与论文年份一致。列多篇不同年份的论文时每篇前面都写年份，别用"次年/同年/2024 到 2025 年"。
  数据库之外的论文（比如还没进 Crossref 的下一届杰出论文）不要加粗，正文说明来源。
- 封面：标题必须带会议名和主题；B 版式标题超过约 15 字会截断，长标题加 `cover_layout: a`。
- 单位统计按 OpenAlex 归一化后的机构名，但同一机构仍有多种写法（Purdue / Purdue University West Lafayette、
  ETH Zurich / ETH Zürich、CISPA / Helmholtz Center for Information Security、中科院各研究所），一个作者的
  `aff` 字段还会用 `;` 连着几家单位。`mksynth.canon_insts()` 里的 RULES 表负责拆分和合并，机构和作者的署名数
  都要用它算（`scratchpad/inst_teams.py` 那套：机构 × 方向 × 作者），文中"N 篇署名"统一指作者在四会的署名总数。地区按第一作者单位推断，未识别的不进分母，正文要交代（NDSS 2017 缺 68%）。
- 已知缺口：ICSE 2026 研究轨未进 Crossref；S&P 2026 只有 1/4 有摘要；ASE 2021/2023、ISSTA 2023、ICSE 2022
  部分杰出论文名单没有官方页；ISSTA 2025 按 PACMSE 登记为 110 篇（3 篇原被 Crossref 登在 FSE 卷）。
  补下一年时只做该会 labels 增量，跑同一条链，最后同样过一遍 DBLP 核对。
