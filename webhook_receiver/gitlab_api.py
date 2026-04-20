"""GitLab HTTP API (v4) — MR 변경·커밋 조회. urllib 표준 라이브러리만 사용."""

from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger("gitlab_api")

# 사내 SSL 이슈 시에만 "0" (보안 주의)
_SSL_VERIFY = os.environ.get("GITLAB_SSL_VERIFY", "1").strip().lower() not in (
    "0",
    "false",
    "no",
)


def _base_url() -> str:
    u = os.environ.get("GITLAB_BASE_URL", "").strip().rstrip("/")
    if not u:
        raise ValueError("GITLAB_BASE_URL 미설정 (예: https://git.cj.net)")
    return u


def _private_token() -> str:
    t = os.environ.get("GITLAB_PRIVATE_TOKEN", "").strip() or os.environ.get(
        "GITLAB_TOKEN", ""
    ).strip()
    if not t:
        raise ValueError(
            "GITLAB_PRIVATE_TOKEN (또는 GITLAB_TOKEN) 미설정 — API 호출 불가"
        )
    return t


def _request_json(method: str, api_path: str, timeout: int = 120) -> Any:
    """api_path 는 /projects/... 처럼 /api/v4 제외."""
    url = f"{_base_url()}/api/v4{api_path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("PRIVATE-TOKEN", _private_token())
    req.add_header("Accept", "application/json")

    open_kw: dict = {"timeout": timeout}
    if not _SSL_VERIFY:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        open_kw["context"] = ctx
        log.warning("GITLAB_SSL_VERIFY=0 — SSL 검증 비활성화됨")

    try:
        with urllib.request.urlopen(req, **open_kw) as resp:
            raw = resp.read().decode()
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:2000]
        log.error("GitLab API HTTP %s %s — %s", e.code, url, body)
        raise
    except urllib.error.URLError as e:
        log.error("GitLab API URL 오류 %s — %s", url, e)
        raise


def fetch_merge_request_changes(project_id: int, mr_iid: int) -> dict[str, Any]:
    """GET projects/:id/merge_requests/:iid/changes — diff 포함."""
    path = f"/projects/{project_id}/merge_requests/{mr_iid}/changes"
    data = _request_json("GET", path)
    if not isinstance(data, dict):
        return {}
    return data


def fetch_merge_request_commits(project_id: int, mr_iid: int) -> list[dict[str, Any]]:
    """GET projects/:id/merge_requests/:iid/commits"""
    path = f"/projects/{project_id}/merge_requests/{mr_iid}/commits"
    data = _request_json("GET", path)
    if not isinstance(data, list):
        return []
    return data


def format_commits_for_log(commits: list[dict[str, Any]], max_items: int = 50) -> str:
    lines = []
    for c in commits[:max_items]:
        title = (c.get("title") or c.get("message", "")).split("\n", 1)[0].strip()
        short = c.get("short_id") or (c.get("id") or "")[:8]
        lines.append(f"  - [{short}] {title}")
    if len(commits) > max_items:
        lines.append(f"  ... 외 {len(commits) - max_items}개 커밋 생략")
    return "\n".join(lines) if lines else "  (커밋 없음)"


def summarize_diffs(
    changes: dict[str, Any], max_chars_per_file: int = 8000
) -> tuple[str, int]:
    """changes 응답에서 diff 문자열 합산(요약 로그용). 반환: (잘린 전체 텍스트, 원본 총 글자 수 근사)"""
    lst = changes.get("changes") or []
    total = 0
    parts: list[str] = []
    for ch in lst:
        if not isinstance(ch, dict):
            continue
        diff = ch.get("diff") or ""
        total += len(diff)
        path = ch.get("new_path") or ch.get("old_path") or "?"
        chunk = (
            diff
            if len(diff) <= max_chars_per_file
            else diff[:max_chars_per_file] + "\n... (truncated)"
        )
        parts.append(f"--- {path} ---\n{chunk}")
    combined = "\n\n".join(parts)
    return combined, total
