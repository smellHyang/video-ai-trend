"""Jira Cloud REST v3: 이슈 생성 (urllib, 설명은 ADF)."""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger("jira_publish")


def _basic_auth_header() -> str:
    email = (
        os.environ.get("ATLASSIAN_EMAIL", "").strip()
        or os.environ.get("JIRA_EMAIL", "").strip()
    )
    token = (
        os.environ.get("ATLASSIAN_API_TOKEN", "").strip()
        or os.environ.get("JIRA_API_TOKEN", "").strip()
    )
    if not email or not token:
        raise ValueError("ATLASSIAN_EMAIL+ATLASSIAN_API_TOKEN 또는 JIRA_* 필요")
    raw = f"{email}:{token}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def _jira_root() -> str:
    base = os.environ.get("JIRA_BASE_URL", "").strip().rstrip("/")
    if not base:
        raise ValueError("JIRA_BASE_URL 미설정 (예: https://xxx.atlassian.net)")
    return base


def plain_text_to_adf(text: str) -> dict[str, Any]:
    """줄바꿈 보존: 문단 단위 paragraph + 줄마다 hardBreak."""
    blocks = text.split("\n\n")
    content: list[dict[str, Any]] = []
    for block in blocks:
        if not block.strip():
            continue
        lines = block.split("\n")
        line_content: list[dict[str, Any]] = []
        for i, line in enumerate(lines):
            line_content.append({"type": "text", "text": line})
            if i < len(lines) - 1:
                line_content.append({"type": "hardBreak"})
        content.append({"type": "paragraph", "content": line_content})
    if not content:
        content = [
            {"type": "paragraph", "content": [{"type": "text", "text": "(empty)"}]}
        ]
    return {"type": "doc", "version": 1, "content": content}


def create_issue(*, summary: str, description_text: str) -> dict[str, Any]:
    """
    JIRA_ENABLED=1
    JIRA_PROJECT_KEY — 예: DEV
    JIRA_ISSUE_TYPE — 기본 Task (이름 그대로 Jira에 있는 타입)
    """
    if os.environ.get("JIRA_ENABLED", "").strip().lower() not in ("1", "true", "yes"):
        raise ValueError("JIRA_ENABLED 가 켜져 있지 않습니다")

    project = os.environ.get("JIRA_PROJECT_KEY", "").strip()
    if not project:
        raise ValueError("JIRA_PROJECT_KEY 미설정")

    issue_type = os.environ.get("JIRA_ISSUE_TYPE", "Task").strip()

    fields: dict[str, Any] = {
        "project": {"key": project},
        "summary": summary[:250],
        "issuetype": {"name": issue_type},
        "description": plain_text_to_adf(description_text),
    }

    payload = {"fields": fields}
    api = _jira_root() + "/rest/api/3/issue"
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
        log.error("Jira API HTTP %s — %s", e.code, err)
        raise
