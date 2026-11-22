#!/usr/bin/env python3
"""从 papers/*/article.md 和 awesome/meta.json 生成 Awesome-Agent-Security-Research 仓库。

只输出英文的论文清单（题目、作者、会议、链接），不含中文解读。
每篇论文在 awesome/meta.json 里有一条记录：
  topic      主分类，取值见 TOPICS
  authors    作者列表；缺失且论文链接是 arXiv 时自动抓取并写回
  benchmark  可选，{"name": ..., "focus": ...}，有则同时进 benchmarks.md
  venue/link 可选，覆盖 article.md 里的值
  exclude    可选，true 则不输出
没有记录的论文不会输出，脚本结尾会列出来提醒补 topic。

用法：python3 scripts/gen_awesome_list.py [输出目录]
默认输出到与本仓库同级的 Awesome-Agent-Security-Research/。
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "awesome" / "meta.json"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "Awesome-Agent-Security-Research"
SCOPE = "AI Agent 安全"
RECENT = 10

# key, 标题, 文件名, 一句话说明
TOPICS = [
    ("skills", "Agent Skills and Plugin Ecosystems", "skills.md",
     "Malicious, vulnerable, and harmful agent skills; skill marketplaces; skill vetting and least privilege."),
    ("tools", "MCP and Tool Chains", "mcp-and-tools.md",
     "Attacks and analyses on MCP servers, tool pools, third-party plugins, and agent dependencies."),
    ("defenses", "Prompt Injection, Guardrails, and Permissions", "defenses.md",
     "Prompt injection and jailbreak defenses, runtime guardrails, and permission models."),
    ("web", "Agents on the Web and Privacy", "web-and-privacy.md",
     "Web and mobile agents, agent detection and fingerprinting, content manipulation, and privacy leakage."),
    ("surveys", "Surveys and SoKs", "surveys.md",
     "Surveys, systematizations, and literature reviews of agent security."),
]

VENUE_FIX = [
    (r"^CCS ", "ACM CCS "),
    (r"^TOSEM ", "ACM TOSEM "),
    (r"^USENIX Security (\d\d)$", r"USENIX Security 20\1"),
]


def field(fm, key):
    m = re.search(rf"^{key}:\s*(.*)$", fm, re.M)
    return m.group(1).strip().strip('"').strip("'") if m else ""


def paper_link(text):
    links = re.findall(r"【([^】]+)】\s*(https?://\S+)", text)
    for label, url in links:
        if label == "论文链接" and "nnnn" not in url:
            return url
    for _, url in links:
        if "nnnn" not in url:
            return url
    return ""


def fetch_arxiv_authors(arxiv_id):
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            xml = r.read().decode("utf-8")
    except Exception as e:  # 网络失败不阻塞生成
        print(f"  arXiv 抓取失败 {arxiv_id}: {e}")
        return []
    return [" ".join(a.split()) for a in re.findall(r"<name>(.*?)</name>", xml)]


def fmt_authors(authors):
    if not authors:
        return ""
    return ", ".join(authors) if len(authors) <= 3 else ", ".join(authors[:3]) + ", et al."


def cell(s):
    return s.replace("|", "\\|")


def load():
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    rows, missing, changed = [], [], False
    for f in sorted((ROOT / "papers").glob("*/article.md")):
        text = f.read_text(encoding="utf-8")
        fm = text.split("---")[1]
        if field(fm, "collection") != SCOPE:
            continue
        slug = f.parent.name
        m = meta.get(slug)
        if not m or not m.get("topic"):
            missing.append(slug)
            continue
        if m.get("exclude"):
            continue
        link = m.get("link") or paper_link(text)
        if not m.get("authors"):
            ax = re.search(r"arxiv\.org/abs/([\d.]+)", link)
            if ax:
                m["authors"] = fetch_arxiv_authors(ax.group(1))
                changed = bool(m["authors"]) or changed
        venue = m.get("venue") or field(fm, "venue")
        for pat, rep in VENUE_FIX:
            venue = re.sub(pat, rep, venue)
        rows.append({
            "slug": slug,
            "title": field(fm, "title_en"),
            "authors": fmt_authors(m.get("authors", [])),
            "venue": venue,
            "link": link,
            "topic": m["topic"],
            "benchmark": m.get("benchmark"),
        })
    if changed:
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows, missing


def paper_table(rows, with_topic=False):
    names = {k: (t, fn) for k, t, fn, _ in TOPICS}
    head = "| Paper | Authors | Venue |" + (" Topic |" if with_topic else "")
    out = [head, "|---|---|---|" + ("---|" if with_topic else "")]
    for r in rows:
        tag = " `Benchmark`" if r["benchmark"] else ""
        title = f"[{cell(r['title'])}]({r['link']})" if r["link"] else cell(r["title"])
        line = f"| {title}{tag} | {cell(r['authors'])} | {r['venue']} |"
        if with_topic:
            t, fn = names[r["topic"]]
            line += f" [{t}](papers/{fn}) |"
        out.append(line)
    return "\n".join(out)


def main():
    rows, missing = load()
    rows.sort(key=lambda r: r["slug"], reverse=True)
    (OUT / "papers").mkdir(parents=True, exist_ok=True)

    toc = []
    for key, title, fn, desc in TOPICS:
        sub = [r for r in rows if r["topic"] == key]
        toc.append(f"| [{title}](papers/{fn}) | {len(sub)} | {desc} |")
        page = f"# {title}\n\n{desc}\n\n{len(sub)} papers, newest additions first. [Back to index](../README.md)\n\n{paper_table(sub)}\n"
        (OUT / "papers" / fn).write_text(page, encoding="utf-8")

    bench = [r for r in rows if r["benchmark"]]
    lines = ["| Benchmark | What it evaluates | Paper | Authors | Venue |", "|---|---|---|---|---|"]
    for r in bench:
        b = r["benchmark"]
        lines.append(f"| **{b['name']}** | {cell(b['focus'])} | [{cell(r['title'])}]({r['link']}) | {cell(r['authors'])} | {r['venue']} |")
    (OUT / "benchmarks.md").write_text(
        "# Benchmarks and Datasets\n\nBenchmarks for evaluating agent security. Each one also appears on its topic page, "
        f"marked `Benchmark`.\n\n{len(bench)} benchmarks. [Back to index](README.md)\n\n" + "\n".join(lines) + "\n",
        encoding="utf-8")
    toc.append(f"| [Benchmarks and Datasets](benchmarks.md) | {len(bench)} | Benchmarks, listed separately for quick lookup. |")

    readme = f"""# Awesome Agent Security Research

![Papers](https://img.shields.io/badge/papers-{len(rows)}-blue) ![Benchmarks](https://img.shields.io/badge/benchmarks-{len(bench)}-green)

A curated, daily-updated list of research papers on AI agent security. Each entry gives the title, authors, and venue, and links to the paper. Benchmarks are also listed on their own page.

## Contents

| Topic | Papers | Scope |
|---|---|---|
{chr(10).join(toc)}

## Recently Added

{paper_table(rows[:RECENT], with_topic=True)}

## Contributing

Missing a paper? Open an issue or a pull request with the title, authors, venue, and link.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    print(f"输出到 {OUT}：{len(rows)} 篇论文，{len(bench)} 个 benchmark")
    for key, title, _, _ in TOPICS:
        print(f"  {title}: {sum(r['topic'] == key for r in rows)}")
    noauth = [r["slug"] for r in rows if not r["authors"]]
    if noauth:
        print("缺作者，请在 awesome/meta.json 里补 authors：", ", ".join(noauth))
    if missing:
        print("未分类（未输出），请在 awesome/meta.json 里补 topic：", ", ".join(missing))


if __name__ == "__main__":
    main()
