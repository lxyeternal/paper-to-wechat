# paper-to-wechat

「供应链安全前沿」公众号的论文解读 pipeline：**丢一个论文 PDF 进去 → 中文深度解读 + 自动配图 + 品牌排版 → 直达公众号草稿箱**，你只需最后点发布。

由 Claude Code 驱动，不配置任何 LLM API：需要判断力的环节（读论文、挑图、写稿）由 Claude 完成，确定性环节（提图、封面、排版、上传）由四个独立 Python 脚本完成。

## 用法

在 Claude Code 中一句话：

```
/paper ~/Downloads/xxx.pdf
```

改稿后重发：编辑 `papers/<slug>/article.md`，对 Claude 说"重新发布"（幂等，走草稿更新不产生重复）。

## 全流程（七步）

1. **建档** — 每篇论文一个隔离目录 `papers/<slug>/`
2. **读论文** — Read 通读全文，提取元信息
3. **判类型** — survey / benchmark / method / empirical / system，**一次决定后面所有模板**（见下）
4. **提图** — 页面渲染 + 坐标裁剪 + 首页题头，逐张目视核对完整性（强制）
5. **写稿** — 按类型的结构骨架和分析侧重写 `article.md`
6. **封面** — 品牌封面按类型渲染点缀色/标签/背景水印
7. **排版 + 发布** — Markdown → 微信内联 HTML → 上传配图 + 封面 → 进草稿箱

## 按论文类型分模板（核心）

排版骨架对所有类型统一（保持公众号视觉一致），只在四个维度按类型切换。`kind` 写进 front matter，封面与排版自动同色系联动。

| 类型 kind | 分析侧重 | 图片选择 | 封面色 · 标签 |
|---|---|---|---|
| **survey** 综述/SoK | 全景框架 + 交叉发现 + 系列串联 | 分类树 + 覆盖热图 + 对比表 | 青绿 · 综述解读 |
| **benchmark** 基准 | 构建严谨性 + 反直觉结论 | 构建流水线 + 主结果表 + 对比图 | 天蓝 · 基准解读 |
| **method** 技术/方法 | 痛点→核心洞察→方法→**那张消融**→边界 | 架构图 + 动机图 + 消融/对比表 | 浅紫 · 方法解读 |
| **empirical** 实证/测量 | 数字冲击 + 方法论严谨 + 反直觉发现 | 威胁模型图 + 核心数据图 + 发现图 | 琥珀 · 实测解读 |
| **system** 系统/工具 | 工程取舍 + 规模化 + 实战战果 | 系统架构图 + 主结果表 + 成本图 | 珊瑚 · 系统解读 |

- 封面：品牌骨架（深蓝底 + 链环 + "供应链安全前沿"）不变，只切换**右上角标签 + 点缀色 + 背景水印大字**。类型只靠视觉体现，绝不写进标题文字。
- 「启发与点评」节所有类型都保留，只是侧重不同。

## 写作规范（去 AI 味）

- **禁破折号**：正文与图注不用「——」，改冒号/逗号/拆句（发布前 `grep` 自查为 0）
- **安全术语按业界惯例**：`1day`/`0day` 不意译成"一日/零日"，CVE/RCE/MCP 等保留英文
- **两级强调**：`**xx**` = 类型色粗体（一般重点）；`==xx==` = 红色加粗（最重要的金句，全篇 1-3 处）
- **引用块**：`> ` 开头 = 左边框高亮块，用于核心洞察 / 定理 / 关键定义

## 目录结构

```
pipeline/PAPER_WORKFLOW.md   # /paper 完整执行手册（含 §2.5 类型化模板）
scripts/                     # 四个独立 CLI（用 .venv/bin/python 运行）
  extract_figures.py         #   提图：页面渲染 / 坐标裁剪 / 题头
  render_cover.py            #   封面：品牌模板 + --kind → 1800×766 PNG
  render_article.py          #   排版：article.md → 微信内联 HTML
  wechat_publish.py          #   发布：上传配图/封面 → 草稿箱（幂等）
  setup.sh                   #   新机器初始化
templates/
  cover.html                 #   品牌封面模板（点缀色/标签/水印按 kind）
  theme.py                   #   排版主题（强调色按 kind 切换）
  article_template.md        #   文章结构模板
papers/<slug>/               # 每篇论文的全部素材与产物（严格隔离）
  paper.pdf · figspec.json · assets/ · article.md · publish.json
tests/                       # 脚本单元测试
```

## 新机器初始化

```
bash scripts/setup.sh          # 建 .venv、装依赖、装 chromium、重建 .claude 薄壳
cp .env.example .env           # 填入公众号 AppID / AppSecret
```

再到 公众号后台 → 设置与开发 → 开发接口管理 → API IP白名单 加入本机公网 IP（`curl -s https://ifconfig.me`）。

## 测试

```
.venv/bin/python -m pytest tests/
```

## 注意

- `.env`（公众号密钥）和 `.claude/` 不入 git；工作流定义在 `pipeline/` 下受追踪。
- 发布动作永远由人在公众号后台手动完成；脚本最多写到草稿箱。
- 报 `40164` = 校园网公网 IP 变了，去后台更新 IP 白名单。
