#!/usr/bin/env python3
"""品牌封面渲染：templates/cover.html + 论文标题 → 1800x766 PNG。"""
import argparse
import html
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "cover.html"

# 每类论文的封面点缀色（深蓝底上用浅亮色）+ 右上角标签，与 theme.py 强调色同色系
KIND_STYLE = {
    "survey":    ("#67e8b9", "综述解读"),
    "benchmark": ("#7dd3fc", "基准解读"),
    "method":    ("#c4b5fd", "方法解读"),
    "empirical": ("#fcd34d", "实测解读"),
    "system":    ("#fda4af", "系统解读"),
}
_DEFAULT = ("#67e8b9", "论文解读")


def render_cover(title_zh: str, title_en: str, venue: str, out_path: str,
                 kind: str = "") -> str:
    accent, kind_label = KIND_STYLE.get(kind, _DEFAULT)
    page_html = TEMPLATE.read_text(encoding="utf-8")
    fields = {"title_zh": title_zh, "title_en": title_en, "venue": venue,
              "accent": accent, "kind_label": kind_label,
              "kind_word": kind_label[:2]}  # 背景水印大字，取标签前两字（综述/基准/方法…）
    for key, val in fields.items():
        page_html = page_html.replace("{{" + key + "}}", html.escape(val or ""))
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                     encoding="utf-8") as f:
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
    ap.add_argument("--kind", default="",
                    help="论文类型 survey/benchmark/method/empirical/system，决定点缀色与标签")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print("cover ->", render_cover(a.title_zh, a.title_en, a.venue, a.out, a.kind))
