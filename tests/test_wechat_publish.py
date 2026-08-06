import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import wechat_publish as wp


class FakeResp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def make_paper(tmp_path):
    paper = tmp_path / "paper"
    (paper / "assets/fig").mkdir(parents=True)
    (paper / "assets/fig/fig1.png").write_bytes(b"png1")
    (paper / "assets/cover.png").write_bytes(b"cover")
    (paper / "article.md").write_text(
        "---\ntitle: 标题\ndigest: 摘要\nauthor: 供应链安全前沿\n---\n\n正文",
        encoding="utf-8")
    (paper / "article.html").write_text(
        '<section><img src="assets/fig/fig1.png" /></section>', encoding="utf-8")
    return paper


def test_publish_creates_draft(tmp_path, monkeypatch):
    paper = make_paper(tmp_path)
    calls = []

    def fake_post(url, **kw):
        calls.append(url)
        if "uploadimg" in url:
            return FakeResp({"url": "https://mmbiz.qpic.cn/fig1"})
        if "add_material" in url:
            return FakeResp({"media_id": "THUMB1"})
        if "draft/add" in url:
            payload = json.loads(kw["data"].decode("utf-8"))
            assert payload["articles"][0]["title"] == "标题"
            assert "mmbiz.qpic.cn" in payload["articles"][0]["content"]
            return FakeResp({"media_id": "DRAFT1"})
        raise AssertionError(url)

    monkeypatch.setattr(wp.requests, "post", fake_post)
    monkeypatch.setattr(wp, "get_token", lambda: "TOKEN")
    wp.publish(str(paper))
    state = json.loads((paper / "publish.json").read_text())
    assert state["draft_media_id"] == "DRAFT1"
    assert state["images"]["assets/fig/fig1.png"] == "https://mmbiz.qpic.cn/fig1"


def test_publish_idempotent_updates_existing_draft(tmp_path, monkeypatch):
    paper = make_paper(tmp_path)
    (paper / "publish.json").write_text(json.dumps({
        "images": {"assets/fig/fig1.png": "https://mmbiz.qpic.cn/fig1"},
        "thumb_media_id": "THUMB1", "draft_media_id": "DRAFT1"}))
    calls = []

    def fake_post(url, **kw):
        calls.append(url)
        assert "uploadimg" not in url and "add_material" not in url  # 不重复上传
        assert "draft/update" in url
        payload = json.loads(kw["data"].decode("utf-8"))
        assert payload["media_id"] == "DRAFT1" and payload["index"] == 0
        return FakeResp({"errcode": 0, "errmsg": "ok"})

    monkeypatch.setattr(wp.requests, "post", fake_post)
    monkeypatch.setattr(wp, "get_token", lambda: "TOKEN")
    wp.publish(str(paper))
    assert calls and all("draft/update" in c for c in calls)
