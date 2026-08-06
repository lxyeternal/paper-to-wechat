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
