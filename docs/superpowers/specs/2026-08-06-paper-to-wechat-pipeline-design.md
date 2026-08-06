# paper-to-wechat Pipeline 设计文档

日期：2026-08-06
公众号：供应链安全前沿（个人订阅号，微信号 maliverse）
用户：郭文博（软件供应链安全研究者）

## 1. 目标

用户输入一篇论文 PDF，pipeline 自动完成：中文解读文稿生成、论文配图提取（架构图/结果图/首页题头截图）、品牌封面生成、微信排版、上传至公众号草稿箱。用户只做两件事：**输入 PDF、最后点发布**。

不做：论文发现/监控、论文筛选（选题判断由用户完成）。

## 2. 形态：仓库即工具，Claude Code 驱动

不配置独立 LLM API。仓库是一个 Claude Code 项目，用户日常入口是一条命令：

```
/paper <pdf路径>
```

分工原则：

- **Claude Code 负责需要智能的环节**：读论文、提取元信息、目视挑选核心图、确定裁剪坐标、撰写解读文稿与中文图注。
- **Python 脚本负责确定性环节**：PDF 页面渲染与裁剪、封面渲染、Markdown → 微信 HTML、微信 API 上传。脚本可独立运行、可重跑。

## 3. 目录结构

```
paper-to-wechat/
├── pipeline/
│   └── PAPER_WORKFLOW.md        # /paper 完整工作流定义（git 追踪；.claude 只放引用薄壳）
├── scripts/
│   ├── extract_figures.py       # 页面渲染 + 按坐标高清裁剪 + 首页题头截图
│   ├── render_cover.py          # cover.html 品牌模板 → 900×383 封面图（Playwright 截图）
│   ├── render_article.py        # article.md → 微信兼容 HTML（全内联样式）
│   └── wechat_publish.py        # 上传正文图 + 封面 → 替换图片地址 → draft/add
├── templates/
│   ├── cover.html               # 品牌封面模板（公众号视觉 + 论文中英文标题）
│   ├── theme.py                 # 排版主题（编号大标题风格，参考"AI智能罗盘"样例但更精致）
│   └── article_template.md      # 文章结构模板（见 §4）
├── papers/                      # 素材按论文严格隔离，每篇一个目录
│   └── <YYYY-MM-slug>/
│       ├── paper.pdf
│       ├── assets/
│       │   ├── header.png       # 首页题头（标题+作者+单位）
│       │   ├── fig/             # 架构图/方法图
│       │   ├── result/          # 结果图表
│       │   └── cover.png
│       ├── article.md           # 解读文稿（用户可直接改）
│       └── publish.json        # 上传记录：图片 URL、thumb_media_id、草稿 media_id
├── .env                         # WECHAT_APPID / WECHAT_APPSECRET（gitignore）
├── .env.example
├── .gitignore                   # 忽略 .env、.claude/、__pycache__ 等
└── README.md
```

## 4. 文章结构（读者叙事线）

核心原则：不按论文章节机械翻译，按读者关心的问题组织。

| 栏目 | 回答的问题 | 配图 |
|---|---|---|
| 本文看点（3 要点卡片） | 值不值得往下读？ | — |
| 论文信息 + 作者介绍 | 谁做的？发在哪？可信度？ | **首页题头截图** |
| 一句话导读 | 论文整体在干什么？ | — |
| 问题与挑战 | 领域卡在哪？为何之前没解决？ | — |
| 方法 | 怎么做的？巧在哪？ | 架构图 + 中文图注 |
| 实验结果 | 效果到底怎么样？ | 结果图表 + 中文图注 |
| 启发与点评 | 对研究者/从业者意味着什么？ | — |

- 论文信息栏固定包含：【论文题目】【论文链接】【代码链接】（无代码则省略）。
- 图注风格："— 图2：CSQ 探测方法示例……"。
- "启发与点评"结合软件供应链安全领域上下文撰写，是用户在草稿箱中最可能人工润色的部分。

## 5. 图片处理

1. **提图策略**：不抽 PDF 内嵌图片对象（矢量图会碎片化）。`extract_figures.py` 将每页渲染为高分辨率位图；Claude 目视页面截图，判断哪些是核心架构图、哪些是关键结果图，给出 `(页码, bbox)`；脚本按坐标以 ≥200 DPI 裁剪输出，保证图完整、清晰、边缘规整。
2. **首页题头**：裁剪第一页顶部"标题+作者+单位"区块 → `assets/header.png`，插入作者介绍栏。
3. **封面**：`cover.html` 固定品牌模板，注入论文中英文标题，Playwright 无头截图 900×383（微信 2.35:1 封面）。
4. **归类**：架构图入 `assets/fig/`，结果图入 `assets/result/`，文件名含图号。

## 6. 微信发布链

前置事实（2026-08-06 已实测验证）：该个人订阅号可获取 access_token，草稿箱接口（draft/count）与素材接口（material/get_materialcount）均有权限；IP 白名单已配置（155.69.191.66，NTU 校园网）。

`wechat_publish.py` 步骤：

1. 正文图片走 `media/uploadimg`（"上传发表内容中的图片"，返回 mmbiz URL，不占素材库额度）
2. 封面走 `material/add_material`（type=image，拿 thumb_media_id）
3. 将 HTML 中本地图片路径替换为 mmbiz URL
4. `draft/add` 创建草稿（title、author、digest、content、thumb_media_id）
5. 全部 media_id / URL 写入 `publish.json`

幂等性：每步结果落盘 `publish.json`；重跑时跳过已完成的上传，不产生重复草稿（已有草稿 media_id 时改走 `draft/update` 或提示用户）。

## 7. 错误处理

- 任何一步失败，此前产物均在 `papers/<slug>/` 内，从断点继续，不从头重跑。
- 40164（IP 不在白名单）：明确提示用户去"开发接口管理 → API IP白名单"更新（校园网 IP 变动场景）。
- 文稿修改流：用户直接编辑 `article.md` → 说"重新发布" → 只重跑排版 + 上传两步。
- access_token 每次运行时新取（2h 有效期内可缓存于 publish.json 外的临时文件，不入 git）。

## 8. 技术栈

- Python 3（系统 conda base 即可），依赖：PyMuPDF（页面渲染/裁剪）、Playwright（封面截图）、requests（微信 API）
- 微信 HTML 约束：全部内联 style，不依赖 class/外部 CSS；图片必须为 mmbiz 域名 URL
- 无 LLM API 依赖；智能环节全部由 Claude Code 会话执行

## 9. 测试与验收

- 脚本层：每个脚本可独立 CLI 运行，对样例 PDF 做单步验证。
- 端到端验收：用一篇真实供应链安全论文跑 `/paper`，验证草稿出现在公众号草稿箱、图片显示正常、封面正确、手机预览排版无错乱。
- 微信 API 调用均幂等或只读可测（draft/count 等），不会误发布——发布动作永远由用户在公众号后台手动完成。

## 10. Git 约定

- `.gitignore`：忽略 `.env`、`.claude/`（工作流定义在 `pipeline/` 下受追踪）、`__pycache__/`、`.DS_Store` 等。
- `papers/` 目录入库（内容与素材是公众号资产的一部分）；若日后体积过大再议 LFS 或忽略策略。
- 因 `.claude/` 不入库，README 提供一条初始化命令（或脚本）在新机器上重建 `.claude/commands/paper.md` 薄壳（内容仅为"按 pipeline/PAPER_WORKFLOW.md 执行"的引用）。
