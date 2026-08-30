#!/usr/bin/env python3
"""品牌封面渲染：templates/cover_*.html + front matter → 1800x766 PNG。

论文解读有两套版式，A「看点分栏」和 B「数据对比」，共用同一套设计语言，
按文章目录名做确定性哈希二选一（同一篇每次渲染结果稳定，整个列表看起来是混排的）。
会议报告固定走浅色底的 cover_talk.html。
"""
import argparse
import html
import sys
import re
import tempfile
import zlib
from pathlib import Path

from playwright.sync_api import sync_playwright

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
LAYOUTS = {"a": TEMPLATES / "cover_a.html", "b": TEMPLATES / "cover_b.html"}
# 会议报告走浅色底模板，和论文解读的深色底一眼区分开
TEMPLATE_BY_KIND = {"talk": TEMPLATES / "cover_talk.html"}

# 每类论文的封面点缀色（深色底上用浅亮色）+ 右上角标签，与 theme.py 强调色同色系
KIND_STYLE = {
    "survey":    ("#67e8b9", "综述解读"),
    "benchmark": ("#7dd3fc", "基准解读"),
    "method":    ("#c4b5fd", "方法解读"),
    "empirical": ("#fcd34d", "实测解读"),
    "system":    ("#fda4af", "系统解读"),
    "talk":      ("#4f46e5", "现场报告"),  # 浅底模板，用深色强调色
    "roundup":   ("#fdba74", "会议盘点"),
}
_DEFAULT = ("#67e8b9", "论文解读")


def _em(text: str) -> float:
    """文本的视觉宽度，按 em 估算：中日韩字符算 1，其余算 0.55。"""
    return sum(1.0 if ord(c) > 0x2E80 else 0.55 for c in text) or 0.1


def _fit(text: str, box_px: int, lines: int, lo: int, hi: int) -> int:
    """挑一个能在 box_px 宽、lines 行内放下这段文字的字号。"""
    return max(lo, min(hi, int(box_px * lines / _em(text) * 0.92)))


def split_stat(stat: str):
    """把 "13.9% → 62.5%" 拆成 (前, 后)；没有箭头就只有后一个值。"""
    parts = re.split(r"\s*(?:→|->|=>)\s*", (stat or "").strip(), maxsplit=1)
    return (parts[0], parts[1]) if len(parts) == 2 else ("", parts[0])


def pick_layout(meta: dict, seed: str) -> str:
    """A / B 版式二选一：显式指定 > 数据块不完整只能走 A > 按 seed 做确定性哈希。

    B 版要求 cover_stat 和 cover_stat_label 同时存在：一个没有标签的数字
    既没有语境、又容易和旁边那句结论重复，所以宁可退回 A 版。
    """
    explicit = (meta.get("cover_layout") or "").strip().lower()
    if explicit in LAYOUTS:
        return explicit
    if not ((meta.get("cover_stat") or "").strip()
            and (meta.get("cover_stat_label") or "").strip()):
        return "a"
    return "b" if zlib.crc32(seed.encode("utf-8")) & 1 else "a"


def render_cover(title_zh: str, title_en: str, venue: str, out_path: str,
                 kind: str = "", template: str = "", highlights=None,
                 stat: str = "", layout: str = "a", stat_label: str = "") -> str:
    accent, kind_label = KIND_STYLE.get(kind, _DEFAULT)
    if template:
        tpl = Path(template)
    elif kind in TEMPLATE_BY_KIND:
        tpl = TEMPLATE_BY_KIND[kind]
    else:
        tpl = LAYOUTS.get(layout, LAYOUTS["a"])
    page_html = tpl.read_text(encoding="utf-8")

    hl = list(highlights or []) + ["", "", ""]
    stat_from, stat_to = split_stat(stat)
    is_b = layout == "b" and not template
    # A 版标题占 424px 宽的左栏，B 版结论句在数据块右边只剩约 450px
    title_box, title_cap = (450, 30) if is_b else (424, 42)
    fields = {
        "title_zh": title_zh, "title_en": title_en, "venue": venue,
        "accent": accent, "kind_label": kind_label,
        "kind_word": kind_label[:2],          # 老模板的背景水印大字
        "h1": hl[0], "h2": hl[1], "h3": hl[2],
        "stat": stat, "stat_label": stat_label,
        "stat_from": stat_from, "stat_to": stat_to,
        "stat_size": str(_fit(stat_to, 300, 1, 30, 50)) if stat_to else "46",
        # A 版右栏每条看点必须单行放下，否则会折出孤字
        "hl_size": str(_fit(max(hl[:3], key=_em) if any(hl[:3]) else "", 260, 1, 19, 26)),
        "title_size": str(_fit(title_zh, title_box, 3, 22, title_cap)),
    }
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


def render_from_dir(paper_dir: str, out_path: str = "") -> str:
    """从 <dir>/article.md 的 front matter 取参数渲染封面。

    用到的字段：cover_title（封面那句结论，缺省退回 title）、cover_stat（数据，
    可写成 "13.9% → 62.5%" 的对比，也可只写一个值）、cover_stat_label（这组数
    是什么，B 版必需）、cover_layout（可选，强制 a/b）、highlights（三条看点，
    直接上封面）、title_en、venue、kind。
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_article import parse_front_matter

    d = Path(paper_dir)
    meta, _ = parse_front_matter((d / "article.md").read_text(encoding="utf-8"))
    layout = pick_layout(meta, d.resolve().name)
    out = out_path or str(d / "assets" / "cover.png")
    print(f"版式 {layout.upper()}", end=" ")
    return render_cover(meta.get("cover_title") or meta.get("title", ""),
                        meta.get("title_en", ""), meta.get("venue", ""), out,
                        meta.get("kind", ""), "", meta.get("highlights", []),
                        (meta.get("cover_stat") or "").strip(), layout,
                        (meta.get("cover_stat_label") or "").strip())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_dir", default="",
                    help="从某篇文章目录的 article.md 取全部字段渲染（推荐用法）")
    ap.add_argument("--title-zh", default="")
    ap.add_argument("--title-en", default="")
    ap.add_argument("--venue", default="")
    ap.add_argument("--kind", default="",
                    help="论文类型 survey/benchmark/method/empirical/system，决定点缀色与标签")
    ap.add_argument("--stat", default="", help='B 版的数据，如 "13.9% → 62.5%" 或单个值')
    ap.add_argument("--stat-label", default="", help="B 版数据块的标签，说明这是什么的数字")
    ap.add_argument("--hl", action="append", default=[], help="看点，可重复，最多 3 条")
    ap.add_argument("--layout", default="a", choices=["a", "b"], help="版式，默认 a")
    ap.add_argument("--template", default="", help="覆盖模板路径，试新版式时用")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.from_dir:
        print("cover ->", render_from_dir(a.from_dir, a.out))
        raise SystemExit
    if not a.title_zh or not a.out:
        ap.error("需要 --title-zh 与 --out（或改用 --from <文章目录>）")
    print("cover ->", render_cover(a.title_zh, a.title_en, a.venue, a.out, a.kind,
                                   a.template, a.hl, a.stat, a.layout, a.stat_label))
