import json
import sys
from pathlib import Path

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from extract_figures import render_pages, crop, header


@pytest.fixture
def sample_pdf(tmp_path):
    """两页合成 PDF：首页含标题/作者/Abstract，第二页含一个矩形图形。"""
    p = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((100, 80), "A Great Paper Title", fontsize=18)
    page.insert_text((100, 110), "Alice, Bob - Some University", fontsize=11)
    page.insert_text((72, 200), "Abstract", fontsize=12)
    page.insert_text((72, 220), "This paper ...", fontsize=10)
    page2 = doc.new_page(width=612, height=792)
    page2.draw_rect(fitz.Rect(100, 100, 400, 300), color=(0, 0, 1), width=2)
    doc.save(p)
    return p


def test_render_pages(sample_pdf, tmp_path):
    out = tmp_path / "pages"
    n = render_pages(str(sample_pdf), str(out))
    assert n == 2
    assert (out / "page-01.png").exists()
    assert (out / "page-02.png").exists()


def test_crop_by_spec(sample_pdf, tmp_path):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps(
        [{"page": 2, "bbox": [90, 90, 410, 310], "out": "assets/fig/fig1.png", "dpi": 220}]))
    outs = crop(str(sample_pdf), str(tmp_path), str(spec))
    f = tmp_path / "assets/fig/fig1.png"
    assert f.exists() and outs == [str(f)]
    pix = fitz.Pixmap(str(f))
    assert pix.width > 900  # 320pt * 220dpi/72 ≈ 977px


def test_header_stops_above_abstract(sample_pdf, tmp_path):
    out = tmp_path / "header.png"
    header(str(sample_pdf), str(out))
    assert out.exists()
    pix = fitz.Pixmap(str(out))
    # 裁剪高度应小于 Abstract 的 y(200pt) 对应像素，且包含标题区
    assert pix.height < 200 / 72 * 220 + 10
    assert pix.height > 110 / 72 * 220
