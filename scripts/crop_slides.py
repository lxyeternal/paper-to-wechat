#!/usr/bin/env python3
"""会场照片 → 幻灯片配图：自动裁掉会场环境，只留投影屏，并压到公众号能传的尺寸。

用法：
    python scripts/crop_slides.py <照片目录或文件...> <输出目录> [--width 1800] [--quality 82]

原理：会场是暗的、屏幕是亮的，按行/列统计亮像素占比找出屏幕边界；
允许中间有小缺口（幻灯片栏间空白、前排观众的头），所以观众挡住底部也不会误切。
幻灯片标题条常是深色，会被亮度阈值切掉，因此找到屏幕后再往上多留一截。
"""
import argparse
from pathlib import Path

import fitz

IMG_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic"}


def _band(vals, thresh, max_gap):
    """最长的一段 >= thresh 的区间，允许中间有不超过 max_gap 的低谷。"""
    runs, cur, last = [], None, 0
    for i, v in enumerate(vals):
        if v >= thresh:
            if cur is None:
                cur = i
            last = i
        elif cur is not None and i - last > max_gap:
            runs.append((cur, last + 1))
            cur = None
    if cur is not None:
        runs.append((cur, last + 1))
    return max(runs, key=lambda r: r[1] - r[0]) if runs else (0, len(vals))


def crop_slide(path: Path, out: Path, max_width: int = 1800, quality: int = 82,
               row_t: float = 0.40, col_t: float = 0.35, top_pad: float = 0.16,
               inset: float = 0.005, shrink: int = 4) -> None:
    src = fitz.Pixmap(str(path))
    if src.alpha:
        src = fitz.Pixmap(fitz.csRGB, src)
    W, H = src.width, src.height

    small = fitz.Pixmap(src)
    small.shrink(shrink)
    w, h, n, s = small.width, small.height, small.n, small.samples
    lum = [[(s[(y*w + x)*n]*299 + s[(y*w + x)*n + 1]*587 + s[(y*w + x)*n + 2]*114) // 1000
            for x in range(w)] for y in range(h)]
    flat = sorted(v for row in lum for v in row)
    thr = max(60, int(flat[int(len(flat)*0.97)] * 0.55))
    rows = [sum(1 for v in row if v >= thr)/w for row in lum]
    cols = [sum(1 for y in range(h) if lum[y][x] >= thr)/h for x in range(w)]

    y0, y1 = _band(rows, row_t, max(2, h//25))
    x0, x1 = _band(cols, col_t, max(2, w//25))
    y0 = max(0, y0 - int((y1 - y0) * top_pad))       # 给深色标题条留出空间
    x0 = max(0, x0 - int((x1 - x0) * 0.01))
    x1 = min(w, x1 + int((x1 - x0) * 0.01))

    clip = fitz.IRect(int((x0/w + inset)*W), int((y0/h + inset)*H),
                      int((x1/w - inset)*W), int((y1/h - inset)*H))
    dst = fitz.Pixmap(src.colorspace, clip, src.alpha)
    dst.copy(src, clip)
    while dst.width > max_width * 1.5:                # shrink 只能整倍减半
        dst.shrink(1)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = dst.tobytes(output="jpg", jpg_quality=quality)
    for q in (75, 68, 60):                            # 公众号正文图上限 1MB
        if len(data) <= 950_000:
            break
        data = dst.tobytes(output="jpg", jpg_quality=q)
    out.write_bytes(data)
    print(f"{path.name} -> {out} ({dst.width}x{dst.height}, {len(data)//1024}KB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="照片目录或单张照片")
    ap.add_argument("out_dir")
    ap.add_argument("--width", type=int, default=1800)
    ap.add_argument("--quality", type=int, default=82)
    a = ap.parse_args()

    files = []
    for item in a.inputs:
        p = Path(item)
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.suffix.lower() in IMG_SUFFIXES)
        else:
            files.append(p)
    for f in files:
        crop_slide(f, Path(a.out_dir) / (f.stem + ".jpg"), a.width, a.quality)


if __name__ == "__main__":
    main()
