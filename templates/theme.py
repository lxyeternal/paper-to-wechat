"""微信排版主题：所有样式内联。编号大标题风格，品牌色深青绿系。"""

ACCENT = "#0d9488"        # 品牌主色（深青绿）
ACCENT_LIGHT = "#67e8b9"
NUM_COLOR = "#e2e8f0"     # 大编号浅灰
LABEL_COLOR = "#94a3b8"   # 英文小标浅灰
TEXT = "#3f3f3f"
CAPTION = "#888888"

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
