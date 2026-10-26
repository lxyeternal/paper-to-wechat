"""微信排版主题：所有样式内联。编号大标题风格，强调色按论文类型切换。

排版骨架对所有类型统一（保持视觉一致）；只有强调色（section 下划线、
看点卡片顶条、粗体、引用块边框）按论文类型走同色系深色，与封面点缀色呼应。
调用 set_kind(kind) 在渲染前设置；kind ∈ {survey,benchmark,method,empirical,system,talk,roundup}。
"""

# 每类的排版强调色（白底上用深色版），与 render_cover 的浅色点缀色同色系
KIND_ACCENT = {
    "survey":    ("#0d9488", "#67e8b9"),  # 青绿：综述/SoK
    "benchmark": ("#0284c7", "#7dd3fc"),  # 天蓝：基准
    "method":    ("#7c3aed", "#c4b5fd"),  # 紫：技术/方法
    "empirical": ("#d97706", "#fcd34d"),  # 琥珀：实证/测量
    "system":    ("#e11d48", "#fda4af"),  # 玫红：系统/工具
    "talk":      ("#4f46e5", "#a5b4fc"),  # 靛蓝：会议报告/主题演讲
    "roundup":   ("#ea580c", "#fdba74"),  # 橙：会议论文盘点
}

ACCENT = "#0d9488"        # 品牌主色（默认青绿，set_kind 会改写）
ACCENT_LIGHT = "#67e8b9"
NUM_COLOR = "#e2e8f0"     # 大编号浅灰
LABEL_COLOR = "#94a3b8"   # 英文小标浅灰
TEXT = "#3f3f3f"
CAPTION = "#888888"


def set_kind(kind: str) -> None:
    """按论文类型切换排版强调色；未知类型回落到 survey（青绿）。"""
    global ACCENT, ACCENT_LIGHT
    ACCENT, ACCENT_LIGHT = KIND_ACCENT.get(kind or "survey", KIND_ACCENT["survey"])

P_STYLE = (f"margin:0 0 18px;font-size:15px;line-height:1.9;color:{TEXT};"
           "letter-spacing:.3px;text-align:left;")


def section_header(num: int, label: str, title_zh: str) -> str:
    return (
        '<section style="margin:36px 0 20px;">'
        f'<p style="margin:0;font-size:44px;font-weight:800;color:{NUM_COLOR};'
        f'line-height:1;">{num:02d}</p>'
        f'<p style="margin:2px 0 0;font-size:11px;letter-spacing:3px;'
        f'color:{LABEL_COLOR};">{label}</p>'
        f'<p style="margin:6px 0 0;font-size:20px;font-weight:700;color:#222;">'
        f'{title_zh}</p>'
        f'<section style="width:36px;height:3px;background:{ACCENT};margin-top:8px;">'
        '</section></section>'
    )


def paragraph(inner_html: str) -> str:
    return f'<p style="{P_STYLE}">{inner_html}</p>'


def image_block(src: str, caption: str) -> str:
    cap = (f'<p style="margin:8px 0 0;font-size:12px;color:{CAPTION};'
           f'text-align:center;line-height:1.6;">— {caption}</p>') if caption else ""
    return ('<section style="margin:20px 0;text-align:center;">'
            f'<img src="{src}" style="max-width:100%;border-radius:4px;" />{cap}</section>')


def quote_block(inner_html: str) -> str:
    """核心洞察 / 定理 / 关键定义的高亮块（左边框强调色，浅底）。

    对技术论文尤其有用：把"一句话灵魂"单独拎出来。Markdown 用 `> ` 触发。
    """
    return ('<section style="margin:22px 0;padding:14px 20px;background:#f7f9fb;'
            f'border-left:4px solid {ACCENT};border-radius:0 4px 4px 0;">'
            f'<p style="margin:0;font-size:15px;line-height:1.85;color:#333;'
            f'font-weight:500;">{inner_html}</p></section>')


def paper_card(idx: int, title_html: str, meta_html: str, body_html: str) -> str:
    """论文清单里的一张卡片：序号 + 标题 + 作者与单位 + 中文导读。

    盘点类文章一屏里挤十几条，不分块就会糊成一片，读者认不出"哪一条是哪一条"。
    卡片和 quote_block 共用一套视觉语言（浅底 + 左侧强调色），只是多了序号和作者行。

    meta 行用 `|` 分成两段：前半是作者名，后半是单位，都保持英文原文。
    作者用浅灰、单位用强调色，两行下面压一条分隔线，把元信息和导读切开。
    """
    meta = ""
    if meta_html:
        authors, _, affils = meta_html.partition("|")
        rows = (f'<p style="margin:9px 0 0;font-size:13px;color:#6b7785;'
                f'line-height:1.65;">{authors.strip()}</p>') if authors.strip() else ""
        if affils.strip():
            rows += (f'<p style="margin:3px 0 0;font-size:13px;color:{ACCENT};'
                     f'font-weight:600;line-height:1.65;">{affils.strip()}</p>')
        meta = (f'<section style="padding-bottom:9px;border-bottom:1px solid #e3e8ee;">'
                f'{rows}</section>')
    body = (f'<p style="margin:11px 0 0;font-size:14px;line-height:1.85;color:{TEXT};'
            f'letter-spacing:.3px;text-align:justify;">{body_html}</p>') if body_html else ""
    return (
        f'<section style="margin:18px 0;background:#f7f9fb;border-left:4px solid {ACCENT};'
        'border-radius:0 6px 6px 0;padding:14px 18px;">'
        f'<p style="margin:0;font-size:11px;letter-spacing:2px;color:{LABEL_COLOR};">'
        f'{idx:02d}</p>'
        f'<p style="margin:4px 0 0;font-size:15px;font-weight:700;color:#1f2937;'
        f'line-height:1.55;">{title_html}</p>{meta}{body}</section>'
    )


def highlights_cards(items: list[str]) -> str:
    cards = ""
    for i, text in enumerate(items, 1):
        cards += (
            '<section style="flex:1;background:#f7f9fb;border-top:3px solid '
            f'{ACCENT};border-radius:4px;padding:12px 10px;margin:0 4px;">'
            f'<p style="margin:0;font-size:12px;color:{LABEL_COLOR};">{i:02d}</p>'
            f'<p style="margin:6px 0 0;font-size:13px;font-weight:600;color:#333;'
            f'line-height:1.5;">{text}</p></section>'
        )
    return ('<section style="margin:8px 0 28px;">'
            f'<p style="margin:0 0 12px;font-size:12px;color:{LABEL_COLOR};'
            'letter-spacing:2px;">本文看点</p>'
            f'<section style="display:flex;">{cards}</section></section>')


def subhead(text_html: str) -> str:
    """小节内的轻量小标题（Markdown `#### `）：一个强调色小方块 + 15px 粗体。

    长小节靠它切成 2 到 4 段，读者扫一眼就知道这一段讲哪个时期或哪条线。
    """
    return ('<section style="margin:26px 0 12px;display:flex;align-items:center;">'
            f'<section style="width:8px;height:8px;background:{ACCENT};border-radius:2px;'
            'margin-right:9px;flex-shrink:0;"></section>'
            f'<p style="margin:0;font-size:15.5px;font-weight:700;color:#1f2937;">{text_html}</p></section>')


def timeline_block(items: list[tuple[str, str, str]]) -> str:
    """代表作时间线（Markdown `@timeline` 块，每行 `- 年份 | 英文标题 | 一句中文`）。

    趋势类文章一段里要点七八篇论文，全塞进正文加粗就是一堵墙。时间线把"哪一年、哪一篇、
    讲了什么"拆成三层：年份胶囊、标题、灰色小字，一行一篇，可以跳着看。
    """
    rows = ""
    for year, title, note in items:
        note_html = (f'<p style="margin:3px 0 0;font-size:13px;line-height:1.7;color:#6b7785;">{note}</p>'
                     if note else "")
        rows += ('<section style="display:flex;align-items:flex-start;padding:9px 0;'
                 'border-bottom:1px solid #eef1f5;">'
                 f'<section style="flex-shrink:0;width:46px;margin-top:2px;padding:2px 0;border-radius:999px;'
                 f'background:{ACCENT}1a;color:{ACCENT};font-size:11.5px;font-weight:700;text-align:center;'
                 f'letter-spacing:.3px;">{year}</section>'
                 '<section style="flex:1;margin-left:12px;">'
                 f'<p style="margin:0;font-size:14px;line-height:1.6;color:#1f2937;font-weight:600;">{title}</p>'
                 f'{note_html}</section></section>')
    return f'<section style="margin:6px 0 22px;">{rows}</section>'


def stats_strip(items: list[tuple[str, str]]) -> str:
    """一排数据块（Markdown `@stats` 块，每行 `- 数值 | 说明`），放在小节开头当"一眼结论"。"""
    tiles = ""
    for value, label in items:
        tiles += ('<section style="flex:1;background:#f7f9fb;border-radius:6px;padding:12px 10px;margin:0 4px;">'
                  f'<p style="margin:0;font-size:19px;font-weight:800;color:{ACCENT};line-height:1.2;'
                  f'letter-spacing:-.2px;">{value}</p>'
                  f'<p style="margin:5px 0 0;font-size:12px;color:#6b7785;line-height:1.5;">{label}</p></section>')
    return f'<section style="display:flex;margin:4px 0 20px;">{tiles}</section>'


def table_block(rows: list[list[str]]) -> str:
    """紧凑表格（Markdown `@table` 块，每行 `- a | b | c`，第一行是表头）。

    "各会前三方向 / 各方向头部单位"这类多维对比用表格比一段话清楚；公众号能渲染带内联样式的 table。
    第一列加粗当行标题，数字列靠左，字号 13 到 13.5px，避免手机上换行。
    """
    if not rows:
        return ""
    head, body = rows[0], rows[1:]
    th = "".join(f'<th style="padding:8px 8px;font-size:12.5px;font-weight:700;color:#5b6472;text-align:left;'
                 f'border-bottom:2px solid {ACCENT};background:#f7f9fb;white-space:nowrap;">{h}</th>' for h in head)
    trs = ""
    for i, r in enumerate(body):
        tds = ""
        for j, c in enumerate(r):
            w = "font-weight:700;color:#1f2937;" if j == 0 else "color:#374151;"
            tds += f'<td style="padding:8px 8px;font-size:13px;line-height:1.6;vertical-align:top;{w}border-bottom:1px solid #eef1f5;">{c}</td>'
        trs += f'<tr>{tds}</tr>'
    return ('<section style="margin:6px 0 20px;overflow-x:auto;"><table style="border-collapse:collapse;width:100%;">'
            f'<thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></section>')


def bullet_list(items: list[str]) -> str:
    """普通项目符号列表（连续的 `- ` 行）：强调色圆点 + 悬挂缩进，比一段话里塞分号清楚。"""
    rows = ""
    for it in items:
        rows += ('<section style="display:flex;align-items:flex-start;margin:0 0 8px;">'
                 f'<section style="flex-shrink:0;width:6px;height:6px;border-radius:50%;background:{ACCENT};'
                 'margin:11px 10px 0 2px;"></section>'
                 f'<p style="margin:0;font-size:15px;line-height:1.85;color:{TEXT};">{it}</p></section>')
    return f'<section style="margin:0 0 18px;">{rows}</section>'


def document(inner_html: str) -> str:
    return (f'<section style="font-family:-apple-system,BlinkMacSystemFont,'
            f'&quot;PingFang SC&quot;,sans-serif;padding:4px 2px;">{inner_html}</section>')
