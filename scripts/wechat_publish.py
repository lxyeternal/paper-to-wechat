#!/usr/bin/env python3
"""上传配图 + 封面，创建/更新公众号草稿。幂等：状态存 <paper_dir>/publish.json。

用法: python3 scripts/wechat_publish.py papers/<slug>
凭据: 仓库根 .env（WECHAT_APPID / WECHAT_APPSECRET），绝不打印。
"""
import argparse
import json
import re
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_article import parse_front_matter

API = "https://api.weixin.qq.com/cgi-bin"
ROOT = Path(__file__).resolve().parent.parent


class WeChatError(RuntimeError):
    pass


def _check(data: dict) -> dict:
    code = data.get("errcode", 0)
    if code:
        msg = f"微信 API 错误 {code}: {data.get('errmsg')}"
        if code == 40164:
            msg += ("\n→ IP 不在白名单。请到 公众号后台→设置与开发→开发接口管理→"
                    "API IP白名单 更新（curl -s https://ifconfig.me 查当前 IP）")
        raise WeChatError(msg)
    return data


def get_token() -> str:
    env = dotenv_values(ROOT / ".env")
    appid, secret = env.get("WECHAT_APPID"), env.get("WECHAT_APPSECRET")
    if not appid or not secret:
        raise WeChatError("缺少 .env 中的 WECHAT_APPID / WECHAT_APPSECRET")
    data = _check(requests.get(f"{API}/token", params={
        "grant_type": "client_credential", "appid": appid, "secret": secret},
        timeout=30).json())
    return data["access_token"]


_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".gif": "image/gif", ".bmp": "image/bmp"}


def _mime(path: Path) -> str:
    return _MIME.get(path.suffix.lower(), "image/png")


def upload_content_image(token: str, path: Path) -> str:
    """正文图 → media/uploadimg，返回 mmbiz URL（不占素材库额度）。"""
    with open(path, "rb") as f:
        data = _check(requests.post(
            f"{API}/media/uploadimg?access_token={token}",
            files={"media": (path.name, f, _mime(path))}, timeout=60).json())
    return data["url"]


def upload_thumb(token: str, path: Path) -> str:
    """封面 → material/add_material(type=image)，返回 media_id。"""
    with open(path, "rb") as f:
        data = _check(requests.post(
            f"{API}/material/add_material?access_token={token}&type=image",
            files={"media": (path.name, f, _mime(path))}, timeout=60).json())
    return data["media_id"]


def publish(paper_dir: str) -> None:
    paper = Path(paper_dir)
    meta, _ = parse_front_matter((paper / "article.md").read_text(encoding="utf-8"))
    html = (paper / "article.html").read_text(encoding="utf-8")
    state_file = paper / "publish.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {"images": {}}

    token = get_token()

    # 1. 上传正文图片（跳过已上传），替换 HTML 中的本地路径
    for src in re.findall(r'<img src="([^"]+)"', html):
        if src.startswith("http"):
            continue
        if src not in state["images"]:
            state["images"][src] = upload_content_image(token, paper / src)
            state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))
            print("上传配图:", src)
        html = html.replace(f'src="{src}"', f'src="{state["images"][src]}"')

    # 2. 封面
    if not state.get("thumb_media_id"):
        state["thumb_media_id"] = upload_thumb(token, paper / "assets/cover.png")
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        print("上传封面 media_id:", state["thumb_media_id"])

    # 3. 草稿
    article = {
        "title": meta["title"][:64],
        "author": meta.get("author", ""),
        "digest": meta.get("digest", "")[:120],
        "content": html,
        "thumb_media_id": state["thumb_media_id"],
        "need_open_comment": 1,
        "only_fans_can_comment": 0,
    }
    if state.get("draft_media_id"):
        payload = {"media_id": state["draft_media_id"], "index": 0, "articles": article}
        try:
            _check(requests.post(f"{API}/draft/update?access_token={token}",
                                 data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                 timeout=60).json())
        except WeChatError as e:
            if "40007" not in str(e):
                raise
            # 草稿被"发表"后就从草稿箱消费掉了，media_id 随之失效。
            # 已发表文章不能改封面/正文，这里明确提示而不是抛 traceback。
            raise SystemExit(
                "这篇的草稿已不存在（多半已经发表过了）。已发表文章无法通过接口改封面或正文。\n"
                "如果确实要重新发一篇新草稿，先删掉 publish.json 里的 draft_media_id 再跑，"
                "注意这会在草稿箱里多出一条。")
        print("草稿已更新:", state["draft_media_id"])
    else:
        payload = {"articles": [article]}
        data = _check(requests.post(f"{API}/draft/add?access_token={token}",
                                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                    timeout=60).json())
        state["draft_media_id"] = data["media_id"]
        print("草稿已创建:", state["draft_media_id"])
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    print("完成。请到 公众号后台→内容管理→草稿箱 查看。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_dir")
    publish(ap.parse_args().paper_dir)
