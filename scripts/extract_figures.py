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
    p1 = sub.add_parser("pages", help="每页渲染为 PNG")
    p1.add_argument("pdf")
    p1.add_argument("outdir")
    p2 = sub.add_parser("crop", help="按 spec.json 裁剪")
    p2.add_argument("pdf")
    p2.add_argument("paper_dir")
    p2.add_argument("spec")
    p3 = sub.add_parser("header", help="首页题头截图")
    p3.add_argument("pdf")
    p3.add_argument("out")
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
