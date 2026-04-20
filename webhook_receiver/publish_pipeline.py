"""머지 MR: AI 요약 → Confluence·Jira (환경변수로 켜짐)."""

from __future__ import annotations

import logging
import os
from typing import Any

from ai_summarize import summarize_merge_request
from confluence_publish import create_page
from jira_publish import create_issue

log = logging.getLogger("publish_pipeline")


def run_post_merge_publish(
    *,
    payload: dict[str, Any],
    diff_text: str,
    commits: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    diff/커밋 기반 요약 후 Confluence/Jira 반영.
    각 단계는 독립적으로 실패해도 나머지 시도 (결과만 out에 기록).
    """
    out: dict[str, Any] = {}

    project = payload.get("project") or {}
    oa = payload.get("object_attributes") or {}

    mr_title = (oa.get("title") or "MR").strip()
    source_branch = (oa.get("source_branch") or "").strip()
    target_branch = (oa.get("target_branch") or "").strip()
    mr_iid = oa.get("iid")
    web_url = (oa.get("url") or "").strip()
    proj_name = (project.get("path_with_namespace") or project.get("name") or "").strip()

    commit_lines = "\n".join(
        f"- {(c.get('title') or c.get('message', '')).split(chr(10), 1)[0]}"
        for c in commits
    )

    # --- AI ---
    summary_md: str | None = None
    try:
        summary_md = summarize_merge_request(
            mr_title=mr_title,
            source_branch=source_branch,
            target_branch=target_branch,
            commit_lines=commit_lines,
            diff_text=diff_text,
        )
        out["ai"] = "ok"
    except ValueError as e:
        log.info("AI 단계 스킵: %s", e)
        out["ai"] = f"skipped: {e}"
    except Exception:
        log.exception("AI 요약 실패")
        out["ai"] = "error"

    if not summary_md:
        out["confluence"] = "skipped (no summary)"
        out["jira"] = "skipped (no summary)"
        return out

    header = (
        f"프로젝트: {proj_name}\n"
        f"MR: !{mr_iid}\n"
        f"브랜치: {source_branch} → {target_branch}\n"
        + (f"링크: {web_url}\n" if web_url else "")
        + "\n"
    )
    page_title = f"[MR !{mr_iid}] {mr_title}"[:240]

    # --- Confluence ---
    try:
        cf = create_page(title=page_title, body_markdown=header + summary_md)
        out["confluence"] = "ok"
        out["confluence_id"] = cf.get("id")
        out["confluence_link"] = _confluence_browse_url(cf)
    except ValueError as e:
        log.info("Confluence 스킵: %s", e)
        out["confluence"] = f"skipped: {e}"
    except Exception:
        log.exception("Confluence 생성 실패")
        out["confluence"] = "error"

    # --- Jira ---
    try:
        ji = create_issue(
            summary=page_title[:250],
            description_text=header + summary_md,
        )
        out["jira"] = "ok"
        out["jira_key"] = ji.get("key")
        out["jira_link"] = (ji.get("self") or "").strip()
    except ValueError as e:
        log.info("Jira 스킵: %s", e)
        out["jira"] = f"skipped: {e}"
    except Exception:
        log.exception("Jira 이슈 생성 실패")
        out["jira"] = "error"

    return out


def _confluence_browse_url(cf: dict[str, Any]) -> str | None:
    """브라우저에서 열 수 있는 페이지 URL (Cloud 기준)."""
    links = cf.get("_links") or {}
    webui = links.get("webui") or ""
    if webui.startswith("http"):
        return webui
    base = os.environ.get("CONFLUENCE_BASE_URL", "").strip().rstrip("/")
    if base and webui.startswith("/"):
        return base + webui
    return links.get("self")
