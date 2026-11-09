#!/usr/bin/env python3
"""小红书素材包：图片用论文原图，文字写在笔记正文里。

小红书没有面向个人创作者的发布 API，发布由用户在 creator.xiaohongshu.com 网页端完成。

做法（2026-11 用户定）：不自己设计信息卡片，图片就是论文原图。但论文图大多是 3:1 到 5:1 的横条，
单张放进 3:4 竖框会空掉七成、字很小，所以每张小红书图是一"页"：
  - 一页放 2 到 3 个图块，上下堆叠撑满画面；
  - 多子图的横图（(a)(b) 并排）用 clip 切成单个子图再竖着堆，每块放大约一倍；
  - 每个图块上方一行中文小标题，说这张图看什么（图本身仍是原图）；
  - 图直接从 paper.pdf 按 figspec 的 bbox 矢量渲染，放大也清晰。

papers/<slug>/xhs/xhs.json：
{
  "title": "笔记标题 ≤20 字", "body": "正文 ≤1000 字", "tags": ["AI安全", ...],
  "pages": [                                   // 每个元素是一张小红书图
    [                                          // 一页里的若干图块，自上而下
      {"fig": "assets/header.png"},            // fig = figspec.json 里的 out，用它的 page+bbox
      {"fig": "assets/result/x.png", "caption": "一句话说明这张图看什么",
       "clip": [0, 0, 0.5, 1]}                 // 可选：在 bbox 内按比例再裁（x0,y0,x1,y1），用于拆子图
    ],
    ...
  ]
}

用法：python scripts/render_xhs.py papers/<slug>
输出：papers/<slug>/xhs/images/01.png ...，papers/<slug>/xhs/post.txt
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import fitz

W, H = 1080, 1440
MARGIN_X, MARGIN_Y = 44, 56
GAP = 46                 # 图块之间
CAP_SIZE = 30            # 小标题字号
CAP_GAP = 14             # 小标题与图之间
INK = (0.08, 0.13, 0.24)
ACCENT = (0.85, 0.47, 0.02)   # 小标题左侧色条，与公众号 empirical/method 琥珀色系接近
FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
TITLE_MAX, BODY_MAX = 20, 1000


def resolve(d: Path, spec: list, block: dict):
    item = next((s for s in spec if s["out"] == block["fig"]), None)
    if item is None:
        sys.exit(f"figspec.json 里没有 {block['fig']}")
    x0, y0, x1, y1 = item["bbox"]
    if "clip" in block:
        fx0, fy0, fx1, fy1 = block["clip"]
        w, h = x1 - x0, y1 - y0
        x0, y0, x1, y1 = x0 + fx0 * w, y0 + fy0 * h, x0 + fx1 * w, y0 + fy1 * h
    return item["page"] - 1, fitz.Rect(x0, y0, x1, y1)


def caption_height(text: str) -> float:
    if not text:
        return 0
    per_line = int((W - 2 * MARGIN_X - 22) / CAP_SIZE)
    lines = -(-len(text) // per_line)
    return lines * CAP_SIZE * 1.35 + CAP_GAP


def render_page(src: fitz.Document, d: Path, spec: list, blocks: list, out: Path) -> None:
    box_w = W - 2 * MARGIN_X
    items = [(b, *resolve(d, spec, b)) for b in blocks]
    caps = [caption_height(b.get("caption", "")) for b, _, _ in items]
    fig_h = [box_w * r.height / r.width for _, _, r in items]
    avail = H - 2 * MARGIN_Y - GAP * (len(items) - 1) - sum(caps)
    s = min(1.0, avail / sum(fig_h))            # 太高就整体缩小图（小标题字号不变）
    total = sum(caps) + sum(h * s for h in fig_h) + GAP * (len(items) - 1)
    y = (H - total) / 2

    doc = fitz.open()
    page = doc.new_page(width=W, height=H)
    page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
    page.insert_font(fontname="cjk", fontfile=FONT)
    for (b, pno, clip), ch, fh in zip(items, caps, fig_h):
        if ch:
            page.draw_rect(fitz.Rect(MARGIN_X, y + 4, MARGIN_X + 7, y + CAP_SIZE * 1.15),
                           color=None, fill=ACCENT)
            page.insert_textbox(fitz.Rect(MARGIN_X + 22, y, W - MARGIN_X, y + ch),
                                b["caption"], fontname="cjk", fontsize=CAP_SIZE,
                                color=INK, lineheight=1.35)
            y += ch
        w, h = box_w * s, fh * s
        x = (W - w) / 2
        page.show_pdf_page(fitz.Rect(x, y, x + w, y + h), src, pno, clip=clip)
        y += h + GAP
    page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False).save(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_dir")
    d = Path(ap.parse_args().paper_dir)
    cfg = json.loads((d / "xhs" / "xhs.json").read_text(encoding="utf-8"))
    spec = json.loads((d / "figspec.json").read_text(encoding="utf-8"))
    src = fitz.open(d / "paper.pdf")

    problems = []
    if len(cfg["title"]) > TITLE_MAX:
        problems.append(f"标题 {len(cfg['title'])} 字，超过 {TITLE_MAX}")
    if len(cfg["body"]) > BODY_MAX:
        problems.append(f"正文 {len(cfg['body'])} 字，超过 {BODY_MAX}")
    if not 1 <= len(cfg["pages"]) <= 18:
        problems.append("图片数量必须在 1 到 18 张之间")

    shutil.rmtree(d / "xhs" / "cards", ignore_errors=True)   # 旧版自绘卡片，已弃用
    out_dir = d / "xhs" / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):
        old.unlink()
    for i, blocks in enumerate(cfg["pages"], 1):
        out = out_dir / f"{i:02d}.png"
        render_page(src, d, spec, blocks, out)
        print(f"image -> {out}")

    tags = " ".join("#" + t.lstrip("#") for t in cfg.get("tags", []))
    (d / "xhs" / "post.txt").write_text(f"{cfg['title']}\n\n{cfg['body']}\n\n{tags}\n", encoding="utf-8")
    print(f"post -> {d / 'xhs' / 'post.txt'}（标题 {len(cfg['title'])} 字，正文 {len(cfg['body'])} 字）")
    if problems:
        print("\n需要处理：\n- " + "\n- ".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
