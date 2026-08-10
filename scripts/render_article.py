#!/usr/bin/env python3
"""article.md（受控 Markdown 子集）→ 微信兼容 HTML（全内联样式）。

支持的语法：front matter、`## LABEL|中文标题`、`![图注](路径)`、`**粗体**`、空行分段。
不支持链接语法：URL 直接写在文本里（微信会剥外链，纯文本最稳）。
"""
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
        elif block.startswith(">"):
            # 核心洞察 / 定理 / 关键定义高亮块：去掉每行的 "> " 前缀
            quote = "\n".join(re.sub(r"^>\s?", "", ln) for ln in block.splitlines())
            parts.append(theme.quote_block(_inline(quote).replace("\n", "<br/>")))
        else:
            parts.append(theme.paragraph(_inline(block).replace("\n", "<br/>")))
    return "".join(parts)


def render_document(md_text: str) -> str:
    meta, body = parse_front_matter(md_text)
    theme.set_kind(meta.get("kind", "survey"))
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
