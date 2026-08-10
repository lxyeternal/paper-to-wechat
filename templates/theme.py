"""微信排版主题：所有样式内联。编号大标题风格，强调色按论文类型切换。

排版骨架对所有类型统一（保持视觉一致）；只有强调色（section 下划线、
看点卡片顶条、粗体、引用块边框）按论文类型走同色系深色，与封面点缀色呼应。
调用 set_kind(kind) 在渲染前设置；kind ∈ {survey,benchmark,method,empirical,system}。
"""

# 每类的排版强调色（白底上用深色版），与 render_cover 的浅色点缀色同色系
KIND_ACCENT = {
    "survey":    ("#0d9488", "#67e8b9"),  # 青绿：综述/SoK
    "benchmark": ("#0284c7", "#7dd3fc"),  # 天蓝：基准
    "method":    ("#7c3aed", "#c4b5fd"),  # 紫：技术/方法
    "empirical": ("#d97706", "#fcd34d"),  # 琥珀：实证/测量
    "system":    ("#e11d48", "#fda4af"),  # 玫红：系统/工具
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

P_STYLE = (f"margin:0 0 20px;font-size:15px;line-height:1.9;color:{TEXT};"
           "letter-spacing:.5px;text-align:justify;")


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


def document(inner_html: str) -> str:
    return (f'<section style="font-family:-apple-system,BlinkMacSystemFont,'
            f'&quot;PingFang SC&quot;,sans-serif;padding:4px 2px;">{inner_html}</section>')
