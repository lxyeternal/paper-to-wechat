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
import urllib.parse
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


SEC = {"CCS", "S&P", "USENIX Security", "NDSS"}
SE = {"ICSE", "FSE", "ASE", "ISSTA", "TOSEM"}
PRE = {"arXiv", "Preprint"}


def badge(name, year):
    """会议+年份的彩色徽章：安全四大红色，软工蓝色，预印本灰色，其余紫色"""
    color = "d1242f" if name in SEC else "0969da" if name in SE else "8b949e" if name in PRE else "8250df"
    esc = lambda t: urllib.parse.quote(t.replace("-", "--").replace("_", "__"), safe="")
    # 会议名用彩色底，年份用深色底，一眼能分清是哪个会、哪一年
    return f"![{name} {year}](https://img.shields.io/badge/{esc(name)}-{year}-24292f?labelColor={color}&style=flat-square)"


def entry(r):
    """一条一篇：徽章 + 加粗题目（链到论文），第二行小字作者，有解读的加 Analysis"""
    name, year = split_venue(r["venue"])
    title = f"[{r['title']}]({r['link']})" if r["link"] else r["title"]
    if r["benchmark"] and not r["title"].startswith(r["benchmark"]["name"]):
        title = f"{r['benchmark']['name']}: {title}"  # 题目里没带名字的才补上
    tail = r["authors"]
    if r["slug"]:
        tail += f" &nbsp;·&nbsp; [Analysis]({ANALYSIS.format(slug=r['slug'])})"
    return f"- {badge(name, year)} **{title}**<br><sub>{tail}</sub>"


def block(rs):
    """节内按年份分小标题"""
    out, cur = [], None
    for r in rs:
        y = split_venue(r["venue"])[1]
        if y != cur:
            out.append(f"\n### {y}\n")
            cur = y
        out.append(entry(r))
    return "\n".join(out).strip()


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
    body = "\n\n".join(f"## {t}\n\n> {d}\n\n{block(rs)}\n\n<p align=\"right\"><a href=\"#contents\">back to top</a></p>" for t, d, rs in sections)
    years = sorted({split_venue(r["venue"])[1] for r in rows})
    nconf = sum(split_venue(r["venue"])[0] not in PRE for r in rows)
    toc = "\n".join(f"| [{t}](#{anchor(t)}) | {len(rs)} | {d} |" for t, d, rs in sections)
    readme = f"""<h1 align="center">Awesome Agent Security Research</h1>

<p align="center">A curated, daily-updated list of research papers on the security of AI agents.</p>

<p align="center">
<img src="https://img.shields.io/badge/papers-{len(rows)}-2da44e" alt="papers">
<img src="https://img.shields.io/badge/peer--reviewed-{nconf}-d1242f" alt="peer-reviewed">
<img src="https://img.shields.io/badge/benchmarks-{len(bench)}-8250df" alt="benchmarks">
<img src="https://img.shields.io/badge/years-{years[0]}--{years[-1]}-0969da" alt="years">
</p>

## How to read

Every entry starts with a badge that shows **where and when** the paper appeared, followed by the title (linked to the paper) and the authors. Within each topic, papers are grouped by year, newest first.

| Badge | Meaning |
|---|---|
| {badge("S&P", "2026")} | Security venues: S&P, USENIX Security, CCS, NDSS |
| {badge("ICSE", "2026")} | Software engineering venues: ICSE, FSE, ASE, ISSTA, TOSEM |
| {badge("ICLR Workshop", "2026")} | Other venues |
| {badge("arXiv", "2026")} | Preprints |

`Analysis` after the authors links to our write-up of the paper (in Chinese).

## Contents

| Topic | Papers | Scope |
|---|---|---|
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
