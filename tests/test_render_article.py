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


def test_red_emphasis():
    html = render_body("这是**普通重点**和 ==最重要发现== 的对比。")
    assert 'color:#dc2626' in html  # 红色重点
    assert html.count("<strong") == 2  # 两级强调各一处


def test_render_document_has_highlights_cards():
    html = render_document(SAMPLE)
    assert html.count("要点") >= 3
    assert "本文看点" in html
    assert html.startswith("<section")
