import sys
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from render_cover import render_cover


def test_render_cover(tmp_path):
    out = tmp_path / "cover.png"
    render_cover("恶意 Agent Skill 基准测试", "MalSkillBench: A Runtime-Verified Benchmark",
                 "arXiv 2026", str(out))
    assert out.exists()
    pix = fitz.Pixmap(str(out))
    assert (pix.width, pix.height) == (1800, 766)


def test_render_cover_kind_no_placeholder(tmp_path):
    # 传 kind 后模板占位符必须全部被替换，不残留 {{...}}
    out = tmp_path / "cover.png"
    render_cover("技术方法论文", "A Method Paper", "ICSE 2026", str(out), kind="method")
    assert out.exists()
    from render_cover import TEMPLATE, KIND_STYLE
    assert KIND_STYLE["method"][1] == "方法解读"
