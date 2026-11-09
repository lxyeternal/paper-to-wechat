#!/usr/bin/env python3
"""论文题头封面：把 PDF 第一页的标题 + 作者区块原样排进 1800x766 白底封面。

题头区域取 figspec.json 里 out 为 assets/header.png 的那一项（页码 + bbox，单位 PDF point），
用矢量方式贴到 2.35:1 的画布中央再栅格化，所以字是清晰的，不是放大位图。
输出 assets/cover.png，wechat_publish.py 会照常上传它作为封面。

用法：python scripts/header_cover.py papers/<slug> [--margin 0.08]
"""
import argparse
import json
import sys
from pathlib import Path

import fitz

W, H = 1800, 766  # 与 render_cover.py 产出的封面同尺寸


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_dir")
    ap.add_argument("--margin", type=float, default=0.08, help="四周留白占画布短边的比例")
    a = ap.parse_args()

    d = Path(a.paper_dir)
    spec = json.loads((d / "figspec.json").read_text())
    head = next((s for s in spec if s["out"] == "assets/header.png"), None)
    if head is None:
        sys.exit("figspec.json 里没有 out 为 assets/header.png 的题头项")

    src = fitz.open(d / "paper.pdf")
    clip = fitz.Rect(head["bbox"])

    # 画布按 point 建，宽高比与最终 PNG 一致；题头等比缩放后居中
    cw, ch = 900.0, 900.0 * H / W
    pad = min(cw, ch) * a.margin
    scale = min((cw - 2 * pad) / clip.width, (ch - 2 * pad) / clip.height)
    w, h = clip.width * scale, clip.height * scale
    target = fitz.Rect((cw - w) / 2, (ch - h) / 2, (cw + w) / 2, (ch + h) / 2)

    out = fitz.open()
    page = out.new_page(width=cw, height=ch)
    page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
    page.show_pdf_page(target, src, head["page"] - 1, clip=clip)

    pix = page.get_pixmap(matrix=fitz.Matrix(W / cw, H / ch), alpha=False)
    dst = d / "assets/cover.png"
    pix.save(dst)
    print(f"header cover -> {dst} ({pix.width}x{pix.height})")


if __name__ == "__main__":
    main()
