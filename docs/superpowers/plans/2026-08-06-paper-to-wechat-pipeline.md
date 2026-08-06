# paper-to-wechat Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建"论文 PDF → 微信公众号草稿箱"全自动 pipeline，并用两篇测试论文（MalSkillBench、IntelliRadar）端到端跑通。

**Architecture:** 仓库即 Claude Code 工具。智能环节（读论文/挑图/写稿）由 Claude Code 会话按 `pipeline/PAPER_WORKFLOW.md` 执行；确定性环节由 4 个独立可运行的 Python 脚本完成（提图、封面、排版、发布）。素材按论文隔离在 `papers/<slug>/`。

**Tech Stack:** Python 3 (miniconda base)、PyMuPDF (fitz)、Playwright (Python)、requests、pytest。无 LLM API。

## Global Constraints

- 微信 HTML：全部内联 `style`，禁用 class/外部 CSS/script；正文图片 src 必须替换为 mmbiz URL 后才能进草稿
- 草稿字段上限：title ≤ 64 字符，digest ≤ 120 字符
- 微信 API 域名：`https://api.weixin.qq.com/cgi-bin`；凭据从仓库根 `.env` 读取（`WECHAT_APPID` / `WECHAT_APPSECRET`），绝不打印、绝不入 git
- 发布动作永远由用户在公众号后台手动完成；脚本最多写到草稿箱
- bbox 坐标单位：PDF point，原点左上
- 封面比例 2.35:1，视口 900×383，deviceScaleFactor=2（输出 1800×766）
- 所有产物落盘 `papers/<slug>/`，`publish.json` 记录上传状态保证幂等

---

### Task 1: 环境准备 + 仓库脚手架

**Files:**
- Create: `.env.example`, `templates/`（空目录占位由后续任务填充）, `scripts/setup.sh`
- Modify: 无

**Interfaces:**
- Produces: 可用的 playwright Python 环境；`scripts/setup.sh`（新机器初始化：装依赖 + 重建 `.claude/commands/paper.md` 薄壳）

- [ ] **Step 1: 安装 playwright**

```bash
python3 -m pip install playwright && python3 -m playwright install chromium --with-deps 2>/dev/null || python3 -m playwright install chromium
```

Expected: 安装成功（浏览器可能命中已有缓存，无需下载）

- [ ] **Step 2: 验证 playwright 可截图**

```bash
python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page()
    page.set_content('<h1>ok</h1>'); page.screenshot(path='/tmp/pw_smoke.png'); b.close()
print('playwright OK')"
```

Expected: `playwright OK`

- [ ] **Step 3: 写 `.env.example` 与 `scripts/setup.sh`**

`.env.example`:
```
WECHAT_APPID=wx...
WECHAT_APPSECRET=...
```

`scripts/setup.sh`:
```bash
#!/usr/bin/env bash
# 新机器初始化：安装依赖 + 重建 .claude 薄壳（.claude/ 不入 git）
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m pip install --quiet playwright pymupdf requests python-dotenv pytest
python3 -m playwright install chromium
mkdir -p .claude/commands
cat > .claude/commands/paper.md <<'EOF'
---
description: 论文 PDF → 解读文章 → 公众号草稿箱（全流程）
---
严格按照本仓库 pipeline/PAPER_WORKFLOW.md 定义的工作流，处理论文：$ARGUMENTS
EOF
echo "setup 完成。请复制 .env.example 为 .env 并填入公众号凭据。"
```

- [ ] **Step 4: 运行 setup.sh 验证（重建薄壳）**

```bash
bash scripts/setup.sh && cat .claude/commands/paper.md
```

Expected: 输出薄壳内容，无报错

- [ ] **Step 5: Commit**

```bash
git add .env.example scripts/setup.sh && git commit -m "chore: 环境初始化脚本与 .env 模板"
```

---

### Task 2: extract_figures.py（PDF 页面渲染 + 坐标裁剪 + 题头截图）

**Files:**
- Create: `scripts/extract_figures.py`
- Test: `tests/test_extract_figures.py`

**Interfaces:**
- Produces（CLI，供工作流与后续任务使用）:
  - `python3 scripts/extract_figures.py pages <pdf> <outdir>` → `<outdir>/page-01.png ...`（150dpi，供 Claude 目视挑图）
  - `python3 scripts/extract_figures.py crop <pdf> <paper_dir> <spec.json>` → 按 spec 高清裁剪。spec 为 JSON 数组：`[{"page":1,"bbox":[x0,y0,x1,y1],"out":"assets/fig/fig1.png","dpi":220}]`，out 相对 paper_dir
  - `python3 scripts/extract_figures.py header <pdf> <out.png>` → 首页题头（自动检测 Abstract 位置向上裁剪；含标题/作者/单位）

- [ ] **Step 1: 写失败测试**

`tests/test_extract_figures.py`:
```python
import json
import fitz
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from extract_figures import render_pages, crop, header


@pytest.fixture
def sample_pdf(tmp_path):
    """两页合成 PDF：首页含标题/作者/Abstract，第二页含一个矩形图形。"""
    p = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((100, 80), "A Great Paper Title", fontsize=18)
    page.insert_text((100, 110), "Alice, Bob - Some University", fontsize=11)
    page.insert_text((72, 200), "Abstract", fontsize=12)
    page.insert_text((72, 220), "This paper ...", fontsize=10)
    page2 = doc.new_page(width=612, height=792)
    page2.draw_rect(fitz.Rect(100, 100, 400, 300), color=(0, 0, 1), width=2)
    doc.save(p)
    return p


def test_render_pages(sample_pdf, tmp_path):
    out = tmp_path / "pages"
    n = render_pages(str(sample_pdf), str(out))
    assert n == 2
    assert (out / "page-01.png").exists()
    assert (out / "page-02.png").exists()


def test_crop_by_spec(sample_pdf, tmp_path):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(
        [{"page": 2, "bbox": [90, 90, 410, 310], "out": "assets/fig/fig1.png", "dpi": 220}]))
    outs = crop(str(sample_pdf), str(tmp_path), str(spec))
    f = tmp_path / "assets/fig/fig1.png"
    assert f.exists() and outs == [str(f)]
    pix = fitz.Pixmap(str(f))
    assert pix.width > 900  # 320pt * 220dpi/72 ≈ 977px


def test_header_stops_above_abstract(sample_pdf, tmp_path):
    out = tmp_path / "header.png"
    header(str(sample_pdf), str(out))
    assert out.exists()
    pix = fitz.Pixmap(str(out))
    # 裁剪高度应小于 Abstract 的 y(200pt) 对应像素，且包含标题区
    assert pix.height < 200 / 72 * 220 + 10
    assert pix.height > 110 / 72 * 220
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python3 -m pytest tests/test_extract_figures.py -v
```

Expected: FAIL（ModuleNotFoundError: extract_figures）

- [ ] **Step 3: 实现 `scripts/extract_figures.py`**

```python
#!/usr/bin/env python3
"""PDF 图片提取：页面渲染 / 坐标裁剪 / 首页题头。

坐标单位为 PDF point，原点左上。crop 的 spec.json 格式：
  [{"page": 1, "bbox": [x0, y0, x1, y1], "out": "assets/fig/fig1.png", "dpi": 220}]
"""
import argparse
import json
from pathlib import Path

import fitz


def render_pages(pdf: str, outdir: str, dpi: int = 150) -> int:
    doc = fitz.open(pdf)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(doc, 1):
        page.get_pixmap(dpi=dpi).save(out / f"page-{i:02d}.png")
    return len(doc)


def crop(pdf: str, paper_dir: str, spec_path: str) -> list[str]:
    doc = fitz.open(pdf)
    items = json.loads(Path(spec_path).read_text())
    results = []
    for item in items:
        page = doc[item["page"] - 1]
        rect = fitz.Rect(*item["bbox"])
        out = Path(paper_dir) / item["out"]
        out.parent.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(dpi=item.get("dpi", 220), clip=rect).save(out)
        results.append(str(out))
    return results


def header(pdf: str, out_path: str, dpi: int = 220, margin: int = 8) -> str:
    """裁首页题头：从页顶到 Abstract 上沿；找不到 Abstract 则取页高 35%。"""
    doc = fitz.open(pdf)
    page = doc[0]
    y_abstract = None
    for block in page.get_text("blocks"):
        if block[4].strip().lower().startswith("abstract"):
            y_abstract = block[1]
            break
    bottom = (y_abstract - margin) if y_abstract else page.rect.height * 0.35
    # 左右各留 30pt 避开 arXiv 侧边戳记
    rect = fitz.Rect(30, 15, page.rect.width - 30, bottom)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    page.get_pixmap(dpi=dpi, clip=rect).save(out)
    return str(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("pages")
    p1.add_argument("pdf"); p1.add_argument("outdir")
    p2 = sub.add_parser("crop")
    p2.add_argument("pdf"); p2.add_argument("paper_dir"); p2.add_argument("spec")
    p3 = sub.add_parser("header")
    p3.add_argument("pdf"); p3.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "pages":
        print(f"rendered {render_pages(a.pdf, a.outdir)} pages -> {a.outdir}")
    elif a.cmd == "crop":
        for f in crop(a.pdf, a.paper_dir, a.spec):
            print("cropped ->", f)
    elif a.cmd == "header":
        print("header ->", header(a.pdf, a.out))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 测试通过**

```bash
python3 -m pytest tests/test_extract_figures.py -v
```

Expected: 3 passed

- [ ] **Step 5: 用真实 PDF 冒烟（MalSkillBench 首页题头）**

```bash
python3 scripts/extract_figures.py header /Users/blue/Downloads/2606.07131v3.pdf /tmp/p2w_header_smoke.png && python3 -c "import fitz; p=fitz.Pixmap('/tmp/p2w_header_smoke.png'); print(p.width, p.height)"
```

Expected: 输出尺寸；随后用 Read 工具目视 `/tmp/p2w_header_smoke.png` 确认题头完整（标题+作者+单位，无 Abstract 正文）

- [ ] **Step 6: Commit**

```bash
git add scripts/extract_figures.py tests/test_extract_figures.py && git commit -m "feat: PDF 页面渲染/坐标裁剪/题头截图脚本"
```

---

### Task 3: 品牌封面（cover.html + render_cover.py）

**Files:**
- Create: `templates/cover.html`, `scripts/render_cover.py`
- Test: `tests/test_render_cover.py`

**Interfaces:**
- Produces: `python3 scripts/render_cover.py --title-zh <中文题> --title-en <英文题> --venue <会议> --out <png>` → 1800×766 PNG

- [ ] **Step 1: 写 `templates/cover.html`（900×383 品牌模板）**

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { width: 900px; height: 383px; overflow: hidden;
         font-family: -apple-system, "PingFang SC", "Hiragino Sans GB", sans-serif; }
  .cover { position: relative; width: 900px; height: 383px; padding: 40px 48px;
           background: linear-gradient(135deg, #0a1628 0%, #12294b 55%, #0d3a5c 100%);
           display: flex; flex-direction: column; justify-content: space-between; }
  /* 网格底纹 */
  .cover::before { content: ""; position: absolute; inset: 0;
    background-image: linear-gradient(rgba(94, 176, 239, .06) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(94, 176, 239, .06) 1px, transparent 1px);
    background-size: 44px 44px; }
  /* 右侧链环装饰 */
  .chain { position: absolute; right: -60px; top: -40px; width: 340px; height: 340px;
           opacity: .14; }
  .brand { display: flex; align-items: center; gap: 12px; z-index: 1; }
  .brand .logo { width: 30px; height: 30px; border-radius: 8px;
                 background: linear-gradient(135deg, #36d399, #0ea5e9);
                 display: flex; align-items: center; justify-content: center;
                 color: #fff; font-size: 16px; font-weight: 700; }
  .brand .name { color: #9fc3e8; font-size: 17px; letter-spacing: 2px; }
  .brand .tag { margin-left: auto; color: #67e8b9; border: 1px solid rgba(103,232,185,.5);
                border-radius: 999px; padding: 4px 14px; font-size: 14px; letter-spacing: 3px; }
  .title-zh { z-index: 1; color: #ffffff; font-size: 44px; font-weight: 700;
              line-height: 1.3; letter-spacing: 1px;
              display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
              overflow: hidden; }
  .bottom { z-index: 1; display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; }
  .title-en { color: #7da2c9; font-size: 15px; line-height: 1.45; max-width: 640px;
              display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
              overflow: hidden; }
  .venue { flex-shrink: 0; color: #0a1628; background: #67e8b9; font-weight: 700;
           font-size: 16px; padding: 6px 16px; border-radius: 6px; letter-spacing: 1px; }
  .venue:empty { display: none; }
</style>
</head>
<body>
<div class="cover">
  <svg class="chain" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
    <g fill="none" stroke="#67e8b9" stroke-width="6">
      <rect x="8"  y="30" width="34" height="20" rx="10"/>
      <rect x="34" y="30" width="34" height="20" rx="10"/>
      <rect x="60" y="30" width="34" height="20" rx="10"/>
      <rect x="21" y="58" width="34" height="20" rx="10"/>
      <rect x="47" y="58" width="34" height="20" rx="10"/>
    </g>
  </svg>
  <div class="brand">
    <div class="logo">链</div>
    <div class="name">供应链安全前沿</div>
    <div class="tag">论文解读</div>
  </div>
  <div class="title-zh">{{title_zh}}</div>
  <div class="bottom">
    <div class="title-en">{{title_en}}</div>
    <div class="venue">{{venue}}</div>
  </div>
</div>
</body>
</html>
```

- [ ] **Step 2: 写失败测试**

`tests/test_render_cover.py`:
```python
import sys
from pathlib import Path
import fitz
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from render_cover import render_cover


def test_render_cover(tmp_path):
    out = tmp_path / "cover.png"
    render_cover("恶意 Agent Skill 基准测试", "MalSkillBench: A Runtime-Verified Benchmark",
                 "arXiv 2026", str(out))
    assert out.exists()
    pix = fitz.Pixmap(str(out))
    assert (pix.width, pix.height) == (1800, 766)
```

- [ ] **Step 3: 运行测试确认失败**

```bash
python3 -m pytest tests/test_render_cover.py -v
```

Expected: FAIL（ModuleNotFoundError: render_cover）

- [ ] **Step 4: 实现 `scripts/render_cover.py`**

```python
#!/usr/bin/env python3
"""品牌封面渲染：templates/cover.html + 论文标题 → 1800x766 PNG。"""
import argparse
import html
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "cover.html"


def render_cover(title_zh: str, title_en: str, venue: str, out_path: str) -> str:
    page_html = TEMPLATE.read_text(encoding="utf-8")
    for key, val in {"title_zh": title_zh, "title_en": title_en, "venue": venue}.items():
        page_html = page_html.replace("{{" + key + "}}", html.escape(val or ""))
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(page_html)
        tmp = Path(f.name)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 900, "height": 383},
                                    device_scale_factor=2)
            page.goto(tmp.as_uri())
            page.wait_for_timeout(200)
            page.screenshot(path=str(out))
            browser.close()
    finally:
        tmp.unlink()
    return str(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--title-zh", required=True)
    ap.add_argument("--title-en", default="")
    ap.add_argument("--venue", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print("cover ->", render_cover(a.title_zh, a.title_en, a.venue, a.out))
```

- [ ] **Step 5: 测试通过 + 目视**

```bash
python3 -m pytest tests/test_render_cover.py -v && python3 scripts/render_cover.py --title-zh "恶意 Agent Skill 的运行时验证基准" --title-en "MalSkillBench: A Runtime-Verified Benchmark of Malicious Agent Skills" --venue "arXiv 2026" --out /tmp/p2w_cover_smoke.png
```

Expected: 1 passed；用 Read 目视 `/tmp/p2w_cover_smoke.png`，确认排版美观、文字无溢出

- [ ] **Step 6: Commit**

```bash
git add templates/cover.html scripts/render_cover.py tests/test_render_cover.py && git commit -m "feat: 品牌封面模板与渲染脚本"
```

---

### Task 4: 微信排版（theme.py + render_article.py）

**Files:**
- Create: `templates/theme.py`, `scripts/render_article.py`, `templates/article_template.md`
- Test: `tests/test_render_article.py`

**Interfaces:**
- Consumes: `papers/<slug>/article.md`（front matter + 受控 Markdown 子集，见下）
- Produces:
  - `python3 scripts/render_article.py <paper_dir>` → `<paper_dir>/article.html`（全内联样式）
  - `render_article.parse_front_matter(md_text) -> (meta: dict, body: str)`（Task 5 复用读取 title/digest/author）

**article.md 格式约定（受控子集）：**
- front matter（`---` 包围）：`title` / `title_en` / `digest` / `author` / `venue`，以及 `highlights:`（`  - ` 列表，恰好 3 条）
- `## LABEL|中文标题` → 编号大节（01/02/… 自动编号，LABEL 为英文小字）
- `![图注文本](assets/xxx.png)` → 居中图 + "— 图注文本"图注（路径相对 paper_dir）
- `**粗体**`、空行分段；`【论文题目】...` 等行按普通段落
- 不支持链接语法；URL 直接写在文本里（微信会剥外链，纯文本最稳）

- [ ] **Step 1: 写失败测试**

`tests/test_render_article.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from render_article import parse_front_matter, render_body, render_document

SAMPLE = """---
title: 测试文章标题
title_en: Test Paper
digest: 一句话摘要
author: 供应链安全前沿
venue: ICSE 2026
highlights:
  - 要点一
  - 要点二
  - 要点三
---

## OVERVIEW|导读

这是**导读**段落，链接 https://arxiv.org/abs/2409.15049 直接写文本。

## METHOD|方法

![图1：系统架构图](assets/fig/fig1.png)

方法描述段落。
"""


def test_parse_front_matter():
    meta, body = parse_front_matter(SAMPLE)
    assert meta["title"] == "测试文章标题"
    assert meta["highlights"] == ["要点一", "要点二", "要点三"]
    assert body.lstrip().startswith("## OVERVIEW")


def test_render_body_sections_and_images():
    _, body = parse_front_matter(SAMPLE)
    html = render_body(body)
    assert "01" in html and "OVERVIEW" in html and "导读" in html
    assert "02" in html and "方法" in html
    assert '<img' in html and 'src="assets/fig/fig1.png"' in html
    assert "— 图1：系统架构图" in html
    assert "<strong" in html  # 粗体
    assert "class=" not in html  # 全内联，禁 class


def test_render_document_has_highlights_cards():
    html = render_document(SAMPLE)
    assert html.count("要点") >= 3
    assert "本文看点" in html
    assert html.startswith("<section")
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python3 -m pytest tests/test_render_article.py -v
```

Expected: FAIL（ModuleNotFoundError: render_article）

- [ ] **Step 3: 实现 `templates/theme.py`（样式常量 + HTML 构件）**

```python
"""微信排版主题：所有样式内联。参考编号大标题风格，品牌色 #10b981/#0ea5e9 系。"""

ACCENT = "#0d9488"        # 品牌主色（深青绿）
ACCENT_LIGHT = "#67e8b9"
NUM_COLOR = "#e2e8f0"     # 大编号浅灰
LABEL_COLOR = "#94a3b8"   # 英文小标浅灰
TEXT = "#3f3f3f"
CAPTION = "#888888"

P_STYLE = (f"margin:0 0 20px;font-size:15px;line-height:1.9;color:{TEXT};"
           "letter-spacing:.5px;text-align:justify;")

def section_header(num: int, label: str, title_zh: str) -> str:
    return (
        '<section style="margin:36px 0 20px;">'
        f'<p style="margin:0;font-size:44px;font-weight:800;color:{NUM_COLOR};'
        f'line-height:1;">{num:02d}</p>'
        f'<p style="margin:2px 0 0;font-size:11px;letter-spacing:3px;'
        f'color:{LABEL_COLOR};">{label}</p>'
        f'<p style="margin:6px 0 0;font-size:20px;font-weight:700;color:#222;">'
        f'{title_zh}</p>'
        f'<section style="width:36px;height:3px;background:{ACCENT};margin-top:8px;">'
        '</section></section>'
    )

def paragraph(inner_html: str) -> str:
    return f'<p style="{P_STYLE}">{inner_html}</p>'

def image_block(src: str, caption: str) -> str:
    cap = (f'<p style="margin:8px 0 0;font-size:12px;color:{CAPTION};'
           f'text-align:center;line-height:1.6;">— {caption}</p>') if caption else ""
    return ('<section style="margin:20px 0;text-align:center;">'
            f'<img src="{src}" style="max-width:100%;border-radius:4px;" />{cap}</section>')

def highlights_cards(items: list[str]) -> str:
    cards = ""
    for i, text in enumerate(items, 1):
        cards += (
            '<section style="flex:1;background:#f7f9fb;border-top:3px solid '
            f'{ACCENT};border-radius:4px;padding:12px 10px;margin:0 4px;">'
            f'<p style="margin:0;font-size:12px;color:{LABEL_COLOR};">{i:02d}</p>'
            f'<p style="margin:6px 0 0;font-size:13px;font-weight:600;color:#333;'
            f'line-height:1.5;">{text}</p></section>'
        )
    return ('<section style="margin:8px 0 28px;">'
            f'<p style="margin:0 0 12px;font-size:12px;color:{LABEL_COLOR};'
            'letter-spacing:2px;">本文看点</p>'
            f'<section style="display:flex;">{cards}</section></section>')

def document(inner_html: str) -> str:
    return (f'<section style="font-family:-apple-system,BlinkMacSystemFont,'
            f'&quot;PingFang SC&quot;,sans-serif;padding:4px 2px;">{inner_html}</section>')
```

- [ ] **Step 4: 实现 `scripts/render_article.py`**

```python
#!/usr/bin/env python3
"""article.md（受控 Markdown 子集）→ 微信兼容 HTML（全内联样式）。"""
import argparse
import html as html_mod
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "templates"))
import theme


def parse_front_matter(text: str):
    m = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", text, re.S)
    if not m:
        raise ValueError("article.md 缺少 front matter（--- 包围）")
    meta, body = {}, m.group(2)
    current_list = None
    for line in m.group(1).splitlines():
        if re.match(r"^\s+-\s+", line) and current_list is not None:
            meta[current_list].append(line.split("-", 1)[1].strip())
        elif ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if val == "":
                meta[key] = []
                current_list = key
            else:
                meta[key] = val
                current_list = None
    return meta, body


def _inline(text: str) -> str:
    out = html_mod.escape(text, quote=False)
    out = re.sub(r"\*\*(.+?)\*\*",
                 rf'<strong style="color:{theme.ACCENT};">\1</strong>', out)
    return out


def render_body(body: str) -> str:
    blocks = re.split(r"\n\s*\n", body.strip())
    parts, section_num = [], 0
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        m_h = re.match(r"^##\s+([A-Z0-9 &-]+)\|(.+)$", block)
        m_img = re.match(r"^!\[(.*?)\]\((.+?)\)$", block)
        if m_h:
            section_num += 1
            parts.append(theme.section_header(
                section_num, m_h.group(1).strip(), m_h.group(2).strip()))
        elif m_img:
            parts.append(theme.image_block(m_img.group(2), _inline(m_img.group(1))))
        else:
            parts.append(theme.paragraph(_inline(block).replace("\n", "<br/>")))
    return "".join(parts)


def render_document(md_text: str) -> str:
    meta, body = parse_front_matter(md_text)
    inner = ""
    if meta.get("highlights"):
        inner += theme.highlights_cards(meta["highlights"])
    inner += render_body(body)
    return theme.document(inner)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_dir")
    a = ap.parse_args()
    paper = Path(a.paper_dir)
    html = render_document((paper / "article.md").read_text(encoding="utf-8"))
    (paper / "article.html").write_text(html, encoding="utf-8")
    print("article.html ->", paper / "article.html", f"({len(html)} chars)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 测试通过**

```bash
python3 -m pytest tests/test_render_article.py -v
```

Expected: 3 passed

- [ ] **Step 6: 写 `templates/article_template.md`（文章结构模板，供工作流引用）**

```markdown
---
title: （中文标题，≤64字，吸引读者但不标题党）
title_en: （论文英文原题）
digest: （≤120字摘要，显示在会话卡片上）
author: 供应链安全前沿
venue: （会议/期刊 + 年份，如 ICSE 2026；未知则 arXiv + 年份）
highlights:
  - （看点一，≤14字）
  - （看点二，≤14字）
  - （看点三，≤14字）
---

## PAPER INFO|论文信息

【论文题目】...
【论文链接】https://arxiv.org/abs/...
【代码链接】https://github.com/...（无则删除本行）

![论文题头](assets/header.png)

本文由来自 **XX大学** 等机构的研究团队完成，（1-2 句作者团队背景与可信度）。

## OVERVIEW|导读

（3-5 句：这篇论文整体在干什么？核心发现/贡献一句话点破。）

## BACKGROUND|问题与挑战

（领域卡在哪？为什么之前的方法不行？2-3 段。）

## METHOD|方法

（他们怎么做的？巧在哪？配架构图。）

![图1：（中文图注，说明图在讲什么）](assets/fig/fig1.png)

## RESULTS|实验结果

（效果怎么样？关键数字点出来。配结果图表。）

![图2：（中文图注）](assets/result/fig2.png)

## TAKEAWAYS|启发与点评

（结合软件供应链安全领域上下文：对研究者意味着什么？对从业者意味着什么？
 这一节是人工润色重点，写出观点而不是套话。）
```

- [ ] **Step 7: Commit**

```bash
git add templates/theme.py templates/article_template.md scripts/render_article.py tests/test_render_article.py && git commit -m "feat: 微信排版主题与文章渲染器"
```

---

### Task 5: 微信发布（wechat_publish.py）

**Files:**
- Create: `scripts/wechat_publish.py`
- Test: `tests/test_wechat_publish.py`

**Interfaces:**
- Consumes: `render_article.parse_front_matter`；`papers/<slug>/` 下的 `article.md`、`article.html`、`assets/cover.png`
- Produces: `python3 scripts/wechat_publish.py <paper_dir>` → 上传图片、创建/更新草稿、写 `<paper_dir>/publish.json`
- publish.json 结构：`{"images": {"assets/fig/fig1.png": "https://mmbiz.../..."}, "thumb_media_id": "...", "draft_media_id": "..."}`

- [ ] **Step 1: 写失败测试（mock 微信 API，验证幂等与更新逻辑）**

`tests/test_wechat_publish.py`:
```python
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import wechat_publish as wp


class FakeResp:
    def __init__(self, data):
        self._data = data
    def json(self):
        return self._data


def make_paper(tmp_path):
    paper = tmp_path / "paper"
    (paper / "assets/fig").mkdir(parents=True)
    (paper / "assets/fig/fig1.png").write_bytes(b"png1")
    (paper / "assets/cover.png").write_bytes(b"cover")
    (paper / "article.md").write_text(
        "---\ntitle: 标题\ndigest: 摘要\nauthor: 供应链安全前沿\n---\n\n正文",
        encoding="utf-8")
    (paper / "article.html").write_text(
        '<section><img src="assets/fig/fig1.png" /></section>', encoding="utf-8")
    return paper


def test_publish_creates_draft(tmp_path, monkeypatch):
    paper = make_paper(tmp_path)
    calls = []

    def fake_post(url, **kw):
        calls.append(url)
        if "uploadimg" in url:
            return FakeResp({"url": "https://mmbiz.qpic.cn/fig1"})
        if "add_material" in url:
            return FakeResp({"media_id": "THUMB1"})
        if "draft/add" in url:
            payload = json.loads(kw["data"].decode("utf-8"))
            assert payload["articles"][0]["title"] == "标题"
            assert "mmbiz.qpic.cn" in payload["articles"][0]["content"]
            return FakeResp({"media_id": "DRAFT1"})
        raise AssertionError(url)

    monkeypatch.setattr(wp.requests, "post", fake_post)
    monkeypatch.setattr(wp, "get_token", lambda: "TOKEN")
    wp.publish(str(paper))
    state = json.loads((paper / "publish.json").read_text())
    assert state["draft_media_id"] == "DRAFT1"
    assert state["images"]["assets/fig/fig1.png"] == "https://mmbiz.qpic.cn/fig1"


def test_publish_idempotent_updates_existing_draft(tmp_path, monkeypatch):
    paper = make_paper(tmp_path)
    (paper / "publish.json").write_text(json.dumps({
        "images": {"assets/fig/fig1.png": "https://mmbiz.qpic.cn/fig1"},
        "thumb_media_id": "THUMB1", "draft_media_id": "DRAFT1"}))
    calls = []

    def fake_post(url, **kw):
        calls.append(url)
        assert "uploadimg" not in url and "add_material" not in url  # 不重复上传
        assert "draft/update" in url
        payload = json.loads(kw["data"].decode("utf-8"))
        assert payload["media_id"] == "DRAFT1" and payload["index"] == 0
        return FakeResp({"errcode": 0, "errmsg": "ok"})

    monkeypatch.setattr(wp.requests, "post", fake_post)
    monkeypatch.setattr(wp, "get_token", lambda: "TOKEN")
    wp.publish(str(paper))
    assert calls == [c for c in calls if "draft/update" in c] and calls
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python3 -m pytest tests/test_wechat_publish.py -v
```

Expected: FAIL（ModuleNotFoundError: wechat_publish）

- [ ] **Step 3: 实现 `scripts/wechat_publish.py`**

```python
#!/usr/bin/env python3
"""上传配图 + 封面，创建/更新公众号草稿。幂等：状态存 <paper_dir>/publish.json。

用法: python3 scripts/wechat_publish.py papers/<slug>
凭据: 仓库根 .env（WECHAT_APPID / WECHAT_APPSECRET），绝不打印。
"""
import argparse
import json
import re
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_article import parse_front_matter

API = "https://api.weixin.qq.com/cgi-bin"
ROOT = Path(__file__).resolve().parent.parent


class WeChatError(RuntimeError):
    pass


def _check(data: dict) -> dict:
    code = data.get("errcode", 0)
    if code:
        msg = f"微信 API 错误 {code}: {data.get('errmsg')}"
        if code == 40164:
            msg += "\n→ IP 不在白名单。请到 公众号后台→设置与开发→开发接口管理→API IP白名单 更新（curl -s https://ifconfig.me 查当前 IP）"
        raise WeChatError(msg)
    return data


def get_token() -> str:
    env = dotenv_values(ROOT / ".env")
    appid, secret = env.get("WECHAT_APPID"), env.get("WECHAT_APPSECRET")
    if not appid or not secret:
        raise WeChatError("缺少 .env 中的 WECHAT_APPID / WECHAT_APPSECRET")
    data = _check(requests.get(f"{API}/token", params={
        "grant_type": "client_credential", "appid": appid, "secret": secret},
        timeout=30).json())
    return data["access_token"]


def upload_content_image(token: str, path: Path) -> str:
    """正文图 → media/uploadimg，返回 mmbiz URL（不占素材库额度）。"""
    with open(path, "rb") as f:
        data = _check(requests.post(
            f"{API}/media/uploadimg?access_token={token}",
            files={"media": (path.name, f, "image/png")}, timeout=60).json())
    return data["url"]


def upload_thumb(token: str, path: Path) -> str:
    """封面 → material/add_material(type=image)，返回 media_id。"""
    with open(path, "rb") as f:
        data = _check(requests.post(
            f"{API}/material/add_material?access_token={token}&type=image",
            files={"media": (path.name, f, "image/png")}, timeout=60).json())
    return data["media_id"]


def publish(paper_dir: str) -> None:
    paper = Path(paper_dir)
    meta, _ = parse_front_matter((paper / "article.md").read_text(encoding="utf-8"))
    html = (paper / "article.html").read_text(encoding="utf-8")
    state_file = paper / "publish.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {"images": {}}

    token = get_token()

    # 1. 上传正文图片（跳过已上传），替换 HTML 中的本地路径
    for src in re.findall(r'<img src="([^"]+)"', html):
        if src.startswith("http"):
            continue
        if src not in state["images"]:
            state["images"][src] = upload_content_image(token, paper / src)
            state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))
            print("上传配图:", src)
        html = html.replace(f'src="{src}"', f'src="{state["images"][src]}"')

    # 2. 封面
    if not state.get("thumb_media_id"):
        state["thumb_media_id"] = upload_thumb(token, paper / "assets/cover.png")
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        print("上传封面 media_id:", state["thumb_media_id"])

    # 3. 草稿
    article = {
        "title": meta["title"][:64],
        "author": meta.get("author", ""),
        "digest": meta.get("digest", "")[:120],
        "content": html,
        "thumb_media_id": state["thumb_media_id"],
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }
    if state.get("draft_media_id"):
        payload = {"media_id": state["draft_media_id"], "index": 0, "articles": article}
        _check(requests.post(f"{API}/draft/update?access_token={token}",
                             data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                             timeout=60).json())
        print("草稿已更新:", state["draft_media_id"])
    else:
        payload = {"articles": [article]}
        data = _check(requests.post(f"{API}/draft/add?access_token={token}",
                                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                    timeout=60).json())
        state["draft_media_id"] = data["media_id"]
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        print("草稿已创建:", state["draft_media_id"])
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    print("完成。请到 公众号后台→内容管理→草稿箱 查看。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_dir")
    publish(ap.parse_args().paper_dir)
```

- [ ] **Step 4: 测试通过**

```bash
python3 -m pytest tests/test_wechat_publish.py -v
```

Expected: 2 passed

- [ ] **Step 5: 全量回归**

```bash
python3 -m pytest tests/ -v
```

Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/wechat_publish.py tests/test_wechat_publish.py && git commit -m "feat: 微信素材上传与草稿发布脚本（幂等）"
```

---

### Task 6: 工作流文档（PAPER_WORKFLOW.md + README）

**Files:**
- Create: `pipeline/PAPER_WORKFLOW.md`, `README.md`

**Interfaces:**
- Consumes: Task 2-5 的全部 CLI
- Produces: `/paper` 命令的执行手册（Claude Code 按此执行）

- [ ] **Step 1: 写 `pipeline/PAPER_WORKFLOW.md`**

内容必须包含以下全部环节（这是 Claude Code 的执行手册，写给"零上下文的下一个会话"看）：

```markdown
# /paper 工作流：论文 PDF → 公众号草稿箱

输入：论文 PDF 路径。输出：公众号草稿箱中一篇图文草稿。
凭据在仓库根 .env，绝不打印。发布动作永远由用户手动完成。

## 步骤

### 1. 建目录
- slug 规则：`YYYY-MM-<论文短名小写>`（如 `2026-08-malskillbench`）
- `mkdir -p papers/<slug>/assets` 并复制 PDF 为 `papers/<slug>/paper.pdf`

### 2. 读论文
- 用 Read 工具直接读 `paper.pdf`（分段读完全文），掌握：问题、挑战、方法、
  实验结果、局限。提取元信息：英文原题、作者与机构、发表 venue、
  arXiv 链接、代码仓库链接（通常在摘要或脚注）。

### 3. 提图
- `python3 scripts/extract_figures.py pages papers/<slug>/paper.pdf papers/<slug>/pages`
- 用 Read 目视各页 PNG，选定：1-2 张核心架构/方法图、1-3 张关键结果图。
- 写 `papers/<slug>/figspec.json`（bbox 为 PDF point，可从 150dpi 页面图
  像素坐标 ÷ 150 × 72 换算），架构图 out 到 `assets/fig/`，结果图到 `assets/result/`。
- `python3 scripts/extract_figures.py crop papers/<slug>/paper.pdf papers/<slug> papers/<slug>/figspec.json`
- `python3 scripts/extract_figures.py header papers/<slug>/paper.pdf papers/<slug>/assets/header.png`
- 用 Read 逐一目视裁剪结果：图必须完整、无截断、无邻栏文字混入；不合格就调 bbox 重裁。

### 4. 写文稿
- 按 `templates/article_template.md` 的结构写 `papers/<slug>/article.md`。
- 叙事线：读者视角——整体干什么/解决什么问题/领域挑战/怎么做/结果如何/有何启发。
- 图插在对应章节，图注为中文、格式"图N：说明"。
- 启发与点评结合软件供应链安全领域上下文，写观点不写套话。
- title 中文≤64字；digest≤120字；highlights 恰好 3 条、每条≤14字。

### 5. 封面
- `python3 scripts/render_cover.py --title-zh "<中文短题>" --title-en "<英文原题>" --venue "<venue>" --out papers/<slug>/assets/cover.png`
- 用 Read 目视封面，文字溢出则缩短标题重渲。

### 6. 排版 + 发布
- `python3 scripts/render_article.py papers/<slug>`
- `python3 scripts/wechat_publish.py papers/<slug>`
- 成功后告知用户去 公众号后台→内容管理→草稿箱 查看。

### 7. 修改重发
- 用户改完 `article.md` 后说"重新发布"：只重跑步骤 6 两条命令
  （publish.json 已有 draft_media_id，会走 draft/update，不产生重复草稿）。

## 失败恢复
- 每步产物都在 papers/<slug>/ 内，从失败步骤继续，不从头跑。
- 40164 = IP 白名单失效，提示用户更新（脚本报错信息里有指引）。
```

- [ ] **Step 2: 写 `README.md`**

```markdown
# paper-to-wechat

「供应链安全前沿」公众号论文解读 pipeline：论文 PDF → 中文解读 + 配图 + 排版 → 公众号草稿箱。

## 用法

在 Claude Code 中：

    /paper ~/Downloads/xxx.pdf

改稿后重发：编辑 `papers/<slug>/article.md`，对 Claude 说"重新发布"。

## 新机器初始化

    bash scripts/setup.sh
    cp .env.example .env   # 填入公众号 AppID/AppSecret
    # 公众号后台把本机公网 IP 加入 API IP 白名单

## 结构

- `pipeline/PAPER_WORKFLOW.md` — /paper 工作流定义（Claude Code 执行手册）
- `scripts/` — 提图 / 封面 / 排版 / 发布 四个独立 CLI
- `templates/` — 封面模板、排版主题、文章结构模板
- `papers/<slug>/` — 每篇论文的全部素材与产物（严格隔离）
```

- [ ] **Step 3: Commit**

```bash
git add pipeline/PAPER_WORKFLOW.md README.md && git commit -m "docs: /paper 工作流手册与 README"
```

---

### Task 7: 端到端跑通论文 1（MalSkillBench）

**Files:**
- Create: `papers/2026-08-malskillbench/`（pdf、assets、article.md、figspec.json、publish.json）

**Interfaces:**
- Consumes: 全部脚本 + `pipeline/PAPER_WORKFLOW.md`
- Produces: 公众号草稿箱中第一篇草稿

本任务由 Claude Code 在会话中亲自按 `pipeline/PAPER_WORKFLOW.md` 执行（即首次真实演练 `/paper /Users/blue/Downloads/2606.07131v3.pdf`）：

- [ ] Step 1: 建目录、复制 PDF
- [ ] Step 2: Read 全文，提取元信息（venue、arXiv/代码链接）
- [ ] Step 3: 渲染页面图 → 目视挑图 → 写 figspec.json → crop + header → 目视验收每张裁剪图
- [ ] Step 4: 写 article.md（读者叙事线 + 中文图注 + 供应链安全视角点评）
- [ ] Step 5: 渲染封面 → 目视验收
- [ ] Step 6: render_article + wechat_publish → 验证输出"草稿已创建"
- [ ] Step 7: 调用只读接口验证 `draft/count` 增加，并请用户在公众号后台确认草稿观感
- [ ] Step 8: Commit（`papers/2026-08-malskillbench/` 全部产物，含 publish.json）

---

### Task 8: 端到端跑通论文 2（IntelliRadar）

与 Task 7 完全相同的流程，输入 `/Users/blue/Downloads/2409.15049v6.pdf`，slug `2026-08-intelliradar`：

- [ ] Step 1-8 同 Task 7
- [ ] 额外验证：`draft/count` 达到 2；两篇论文素材目录互不污染

---

## Self-Review 结论

- 规格覆盖：spec §2-§10 各项均有对应任务（形态→T1/T6，目录→T7/T8，文章结构→T4 模板，提图→T2，封面→T3，发布链→T5，错误处理→T5 脚本 + T6 手册，git 约定→T1 setup.sh 重建薄壳）
- 类型一致性：`parse_front_matter` 在 T4 定义、T5 复用，签名一致；figspec.json 格式在 T2 与 T6 手册一致
- 无占位符
