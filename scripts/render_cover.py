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
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print("cover ->", render_cover(a.title_zh, a.title_en, a.venue, a.out))
