#!/usr/bin/env python3
"""从 papers/*/article.md 的 front matter 生成 README 里的论文清单。

按合集分组、组内从新到旧，每行：时间 | 会议 | 论文英文原题（链到论文） | 三条看点 | 原稿链接。
写进 README.md 中 <!-- PAPER-INDEX:START --> 和 <!-- PAPER-INDEX:END --> 之间，
并同步更新顶部"单篇解读-N"徽章。每推一篇新论文后跑一次。

用法：python scripts/gen_readme_index.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
START, END = "<!-- PAPER-INDEX:START -->", "<!-- PAPER-INDEX:END -->"

# 合集顺序、图标、默认是否展开
GROUPS = [
    ("AI Agent 安全", "🤖", True),
    ("恶意包与威胁情报", "📦", False),
    ("供应链攻击与防御", "🔗", False),
    ("开源与安全测量", "📊", False),
]


def field(fm: str, key: str) -> str:
    m = re.search(rf"^{key}:\s*(.*)$", fm, re.M)
    return m.group(1).strip().strip('"').strip("'") if m else ""


VENUE_FIX = [
    (r"^CCS ", "ACM CCS "),
    (r"^TOSEM ", "ACM TOSEM "),
    (r"^USENIX Security (\d\d)$", r"USENIX Security 20\1"),
]


def venue_of(fm: str) -> str:
    v = field(fm, "venue")
    for pat, rep in VENUE_FIX:
        v = re.sub(pat, rep, v)
    award = re.search(r"(最佳论文|杰出论文)", field(fm, "title"))
    return f"{v} 🏆" if award else v


def paper_link(text: str) -> str:
    """优先【论文链接】；缺失或是占位 DOI 时退回到其它【…】里的链接。"""
    links = re.findall(r"【([^】]+)】\s*(https?://\S+)", text)
    for label, url in links:
        if label == "论文链接" and "nnnn" not in url:
            return url
    for label, url in links:
        if "nnnn" not in url:
            return url
    return ""


def load():
    rows = []
    for f in sorted((ROOT / "papers").glob("*/article.md")):
        text = f.read_text(encoding="utf-8")
        fm = text.split("---")[1]
        slug = f.parent.name
        rows.append({
            "slug": slug,
            "date": slug[:7],
            "title": field(fm, "title_en").replace("|", "\\|"),
            "venue": venue_of(fm),
            "collection": field(fm, "collection"),
            "highlights": re.findall(r"^  - (.*)$", fm, re.M),
            "link": paper_link(text),
        })
    return rows


def table(rows) -> str:
    out = ["| 时间 | 会议 | 论文 | 看点 | 解读 |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: r["slug"], reverse=True):
        title = f"[{r['title']}]({r['link']})" if r["link"] else r["title"]
        hl = " · ".join(h.strip() for h in r["highlights"])
        out.append(f"| {r['date']} | {r['venue']} | {title} | {hl} | "
                   f"[原稿](papers/{r['slug']}/article.md) |")
    return "\n".join(out)


def build(rows) -> str:
    parts = []
    known = {g for g, _, _ in GROUPS}
    others = [r for r in rows if r["collection"] not in known]
    for name, icon, open_ in GROUPS:
        sub = [r for r in rows if r["collection"] == name]
        if not sub:
            continue
        parts.append(f"<details{' open' if open_ else ''}>\n"
                     f"<summary><b>{icon} {name}</b>（{len(sub)} 篇）</summary>\n\n"
                     f"{table(sub)}\n\n</details>")
    if others:
        parts.append(f"<details>\n<summary><b>其他</b>（{len(others)} 篇）</summary>\n\n"
                     f"{table(others)}\n\n</details>")
    return "\n\n".join(parts)


def main() -> None:
    rows = load()
    md = README.read_text(encoding="utf-8")
    if START not in md or END not in md:
        raise SystemExit(f"README 里没有 {START} / {END} 标记")
    head, rest = md.split(START, 1)
    _, tail = rest.split(END, 1)
    md = f"{head}{START}\n\n{build(rows)}\n\n{END}{tail}"
    md = re.sub(r"(badge/单篇解读-)\d+", rf"\g<1>{len(rows)}", md)
    README.write_text(md, encoding="utf-8")
    print(f"README 论文清单已更新：{len(rows)} 篇")


if __name__ == "__main__":
    main()
