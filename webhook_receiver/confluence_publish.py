"""Confluence Data Center / Cloud REST: 페이지 생성 (urllib)."""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
import html
from typing import Any

log = logging.getLogger("confluence_publish")


def _basic_auth_header() -> str:
    email = (
        os.environ.get("ATLASSIAN_EMAIL", "").strip()
        or os.environ.get("CONFLUENCE_EMAIL", "").strip()
    )
    token = (
        os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
        or os.environ.get("CONFLUENCE_API_TOKEN", "").strip()
    )
    if not email or not token:
        raise ValueError("ATLASSIAN_EMAIL+ATLASSIAN_API_TOKEN 또는 CONFLUENCE_* 필요")
    raw = f"{email}:{token}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _wiki_rest_root() -> str:
    """예: https://회사.atlassian.net/wiki → .../wiki/rest/api"""
    base = os.environ.get("CONFLUENCE_BASE_URL", "").strip().rstrip("/")
    if not base:
        raise ValueError("CONFLUENCE_BASE_URL 미설정 (예: https://xxx.atlassian.net/wiki)")
    if base.endswith("/wiki"):
        return base + "/rest/api"
    return base + "/wiki/rest/api"


def markdownish_to_storage(text: str) -> str:
    """요약본을 간단히 Confluence storage HTML 로 (이스케이프 + 단락)."""
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    parts: list[str] = []
    for b in blocks:
        # 제목 줄 ### → h3
        if b.startswith("### "):
            parts.append(f"<h3>{html.escape(b[4:].strip())}</h3>")
            continue
        if b.startswith("## "):
            parts.append(f"<h2>{html.escape(b[3:].strip())}</h2>")
            continue
        if b.startswith("- ") or b.startswith("* "):
            items = []
            for line in b.split("\n"):
                line = line.strip()
                if line.startswith(("- ", "* ")):
                    items.append(f"<li>{html.escape(line[2:].strip())}</li>")
            if items:
                parts.append("<ul>" + "".join(items) + "</ul>")
            else:
                parts.append(f"<p>{html.escape(b)}</p>")
            continue
        parts.append(f"<p>{html.escape(b).replace(chr(10), '<br/>')}</p>")
    return "\n".join(parts) if parts else f"<p>{html.escape(text)}</p>"


def create_page(*, title: str, body_markdown: str) -> dict[str, Any]:
    """
    CONFLUENCE_ENABLED=1
    CONFLUENCE_SPACE_KEY
    CONFLUENCE_PARENT_PAGE_ID — 선택, 있으면 하위 페이지
    """
    if os.environ.get("CONFLUENCE_ENABLED", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    ):
        raise ValueError("CONFLUENCE_ENABLED 가 켜져 있지 않습니다")

    space = os.environ.get("CONFLUENCE_SPACE_KEY", "").strip()
    if not space:
        raise ValueError("CONFLUENCE_SPACE_KEY 미설정")

    parent = os.environ.get("CONFLUENCE_PARENT_PAGE_ID", "").strip()

    api = _wiki_rest_root() + "/content"
    storage_html = markdownish_to_storage(body_markdown)

    payload: dict[str, Any] = {
        "type": "page",
        "title": title[:240],
        "space": {"key": space},
        "body": {
            "storage": {"value": storage_html, "representation": "storage"},
        },
    }
    if parent:
        payload["ancestors"] = [{"id": parent}]

    body_bytes = json.dumps(payload, ensure_ascii=False).encode()

    req = urllib.request.Request(
        api,
        data=body_bytes,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": _basic_auth_header(),
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")[:4000]
        log.error("Confluence API HTTP %s — %s", e.code, err)
        raise
