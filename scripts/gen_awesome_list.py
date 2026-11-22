#!/usr/bin/env python3
"""从 papers/*/article.md 和 awesome/meta.json 生成 Awesome-Agent-Security-Research 仓库。

只输出一个英文 README：按主题分节，Benchmarks 在最前，一行一篇（题目、作者、会议），
每行以 [会议] [年份] 开头，有解读的行尾 [Analysis] 链到本仓库里对应的解读；
awesome/extra.json 里是没有解读、手工核对过确属 Agent 安全的论文；清单本身不含中文解读正文。
每篇论文在 awesome/meta.json 里有一条记录：
  topic      主分类，取值见 TOPICS
  authors    作者列表；缺失且论文链接是 arXiv 时自动抓取并写回
  benchmark  可选，{"name": ...}，有则归入最前面的 Benchmarks 一节
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
EXTRA = ROOT / "awesome" / "extra.json"  # 没有解读的论文（如顶会十年数据里筛出的），手工核对后加入
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "Awesome-Agent-Security-Research"
SCOPE = "AI Agent 安全"
RECENT = 10

# key, 标题, 文件名, 一句话说明
TOPICS = [
    ("skills", "Agent Skills and Plugin Ecosystems", "skills.md",
     "Malicious, vulnerable, and harmful agent skills; skill marketplaces; skill vetting and least privilege."),
    ("tools", "MCP and Tool Chains", "mcp-and-tools.md",
     "Attacks and analyses on MCP servers, tool pools, third-party plugins, and agent dependencies."),
    ("apps", "Agent Applications and Frameworks", "apps.md",
     "Vulnerabilities in agent applications, agent frameworks, and multi-agent systems."),
    ("defenses", "Prompt Injection, Guardrails, and Permissions", "defenses.md",
     "Prompt injection attacks and defenses, runtime guardrails, isolation architectures, and permission models."),
    ("web", "Agents on the Web and Privacy", "web-and-privacy.md",
     "Web and mobile agents, detecting and deterring agents, content manipulation, and privacy leakage."),
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
    if not m:
        return ""
    v = m.group(1).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":  # 只剥最外层一对引号，保留题目自带的引号
        v = v[1:-1].replace('\\"', '"')
    return v


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


def norm(title):
    return re.sub(r"[^a-z0-9]", "", title.lower())


def split_venue(venue):
    """'ACM CCS 2026' -> ('CCS', '2026')；'ICLR 2026 Workshop' -> ('ICLR Workshop', '2026')"""
    m = re.search(r"\b(20\d\d)\b", venue)
    year = m.group(1) if m else ""
    name = re.sub(r"\s+", " ", venue.replace(year, "")).strip()
    return re.sub(r"^(ACM|IEEE) ", "", name), year


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
    seen = {norm(r["title"]) for r in rows}
    if EXTRA.exists():
        for e in json.loads(EXTRA.read_text(encoding="utf-8")):
            if norm(e["title"]) in seen:  # 已有解读的不重复
                continue
            rows.append({"slug": "", "title": e["title"], "authors": fmt_authors(e.get("authors", [])),
                         "venue": e["venue"], "link": e.get("link", ""), "topic": e["topic"],
                         "benchmark": e.get("benchmark")})
    if changed:
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows, missing


ANALYSIS = "https://github.com/lxyeternal/paper-to-wechat/blob/main/papers/{slug}/article.md"


def anchor(title):
    return re.sub(r"[^a-z0-9 -]", "", title.lower()).replace(" ", "-")


def entry(r):
    """一行一篇：[会议] [年份] 题目（链到论文）. 作者. [解读]"""
    name, year = split_venue(r["venue"])
    title = f"[{r['title']}]({r['link']})" if r["link"] else r["title"]
    if r["benchmark"]:
        title = f"**{r['benchmark']['name']}**: {title}"
    line = f"- [{name}] [{year}] {title}."
    if r["authors"]:
        line += f" {r['authors'].rstrip('.')}."
    if r["slug"]:
        line += f" [[Analysis]]({ANALYSIS.format(slug=r['slug'])})"
    return line


def order(r):
    """年份新的在前；同年正式发表的排在 arXiv/预印本前面"""
    name, year = split_venue(r["venue"])
    return (-int(year or 0), name in ("arXiv", "Preprint"), name, r["title"])


def main():
    rows, missing = load()
    rows.sort(key=order)
    OUT.mkdir(parents=True, exist_ok=True)

    # benchmark 只出现在最前面的 Benchmarks 一节，不在主题里重复
    bench = [r for r in rows if r["benchmark"]]
    sections = [("Benchmarks", "Benchmarks and datasets for evaluating agent security.", bench)]
    for key, title, _, desc in TOPICS:
        sections.append((title, desc, [r for r in rows if r["topic"] == key and not r["benchmark"]]))
    sections = [s for s in sections if s[2]]

    toc = "\n".join(f"- [{t}](#{anchor(t)}) ({len(rs)})" for t, _, rs in sections)
    body = "\n\n".join(f"## {t}\n\n{d}\n\n" + "\n".join(entry(r) for r in rs) for t, d, rs in sections)
    readme = f"""# Awesome Agent Security Research

A curated, daily-updated list of research papers on AI agent security, grouped by topic. Each entry gives the venue and year, the title (linked to the paper), and the authors. `[Analysis]` links to our write-up of the paper (in Chinese), where we have one.

{len(rows)} papers so far.

## Contents

{toc}

{body}

## Contributing

Missing a paper? Open an issue or a pull request with the title, authors, venue, and link.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    # 旧版的分页文件不再使用
    for old in [OUT / "benchmarks.md", *(OUT / "papers").glob("*.md")]:
        old.unlink(missing_ok=True)
    if (OUT / "papers").is_dir() and not any((OUT / "papers").iterdir()):
        (OUT / "papers").rmdir()

    print(f"输出到 {OUT}：{len(rows)} 篇论文，其中 {len(bench)} 个 benchmark")
    for t, _, rs in sections:
        print(f"  {t}: {len(rs)}")
    noauth = [r["slug"] for r in rows if not r["authors"]]
    if noauth:
        print("缺作者，请在 awesome/meta.json 里补 authors：", ", ".join(noauth))
    if missing:
        print("未分类（未输出），请在 awesome/meta.json 里补 topic：", ", ".join(missing))


if __name__ == "__main__":
    main()
