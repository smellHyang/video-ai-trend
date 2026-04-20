"""
GitLab Webhook 리시버 — 시크릿 검증 + MR 머지 시 GitLab API 로 diff·커밋 조회.

환경변수:
  GITLAB_WEBHOOK_SECRET — GitLab Webhooks Secret token 과 동일
  GITLAB_BASE_URL       — 예: https://git.cj.net
  GITLAB_PRIVATE_TOKEN  — API용 Personal/Project Access Token (read_api 등)
  GITLAB_FETCH_ON_MR_OPEN — "1" 이면 머지 안 된 MR 에도 API 호출 (디버그용, 기본 끔)
  머지 MR 조회 후: AI_ENABLED, OPENAI_* / CONFLUENCE_*, JIRA_* (자세한 것은 .env.example)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from flask import Flask, Response, jsonify, request

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from gitlab_api import (
    fetch_merge_request_changes,
    fetch_merge_request_commits,
    format_commits_for_log,
    summarize_diffs,
)
from publish_pipeline import run_post_merge_publish

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("gitlab_webhook")

app = Flask(__name__)

GITLAB_WEBHOOK_SECRET = os.environ.get("GITLAB_WEBHOOK_SECRET", "").strip()
MAX_BODY_LOG_CHARS = int(os.environ.get("WEBHOOK_LOG_BODY_MAX", "12000"))
MAX_DIFF_LOG_CHARS = int(os.environ.get("MAX_DIFF_LOG_CHARS", "50000"))
FETCH_ON_MR_OPEN = os.environ.get("GITLAB_FETCH_ON_MR_OPEN", "").strip() in (
    "1",
    "true",
    "yes",
)


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len] + f"\n... ({len(s) - max_len} chars truncated)"


def _verify_gitlab_token() -> bool:
    """X-Gitlab-Token 헤더가 설정된 시크릿과 일치하는지 검사."""
    if not GITLAB_WEBHOOK_SECRET:
        log.warning(
            "GITLAB_WEBHOOK_SECRET 미설정 — 어떤 요청이든 통과합니다. 운영 전 반드시 설정하세요."
        )
        return True
    token = request.headers.get("X-Gitlab-Token", "")
    if token != GITLAB_WEBHOOK_SECRET:
        log.warning("시크릿 불일치 또는 누락")
        return False
    return True


def _should_fetch_mr_api(payload: dict[str, Any]) -> bool:
    """Merge Request Hook 에서 GitLab API 를 부를지 (diff/커밋)."""
    oa = payload.get("object_attributes") or {}
    state = (oa.get("state") or "").lower()
    action = (oa.get("action") or "").lower()
    merged = state == "merged" or action == "merge"
    if merged:
        return True
    return FETCH_ON_MR_OPEN


def _process_merge_request_hook(payload: dict[str, Any]) -> dict[str, Any]:
    """머지된 MR 이면 changes + commits 조회 후 로그. 실패해도 예외는 상위에서 잡음."""
    out: dict[str, Any] = {"hook": "Merge Request Hook"}

    if not _should_fetch_mr_api(payload):
        oa = payload.get("object_attributes") or {}
        out["skip_api"] = True
        out["reason"] = (
            "not merged; set GITLAB_FETCH_ON_MR_OPEN=1 to fetch on any MR update"
        )
        out["state"] = oa.get("state")
        out["action"] = oa.get("action")
        return out

    project = payload.get("project") or {}
    oa = payload.get("object_attributes") or {}
    pid = project.get("id")
    iid = oa.get("iid")
    if pid is None or iid is None:
        out["skip_api"] = True
        out["reason"] = "missing project.id or object_attributes.iid"
        return out

    project_id = int(pid)
    mr_iid = int(iid)

    changes = fetch_merge_request_changes(project_id, mr_iid)
    commits = fetch_merge_request_commits(project_id, mr_iid)

    diff_text, diff_total_chars = summarize_diffs(changes)
    out["project_id"] = project_id
    out["mr_iid"] = mr_iid
    out["commits_count"] = len(commits)
    out["diff_files"] = len(changes.get("changes") or [])
    out["diff_total_chars"] = diff_total_chars

    log.info(
        "MR !%s (project %s) — 커밋 %s개, diff 파일 %s개, diff 총 약 %s자",
        mr_iid,
        project_id,
        len(commits),
        out["diff_files"],
        diff_total_chars,
    )
    log.info("커밋 목록:\n%s", format_commits_for_log(commits))
    log.info("Diff 요약 로그:\n%s", _truncate(diff_text, MAX_DIFF_LOG_CHARS))

    out["fetched"] = True

    pub = run_post_merge_publish(
        payload=payload,
        diff_text=diff_text,
        commits=commits,
    )
    out.update(pub)
    return out


def _handle_hook() -> tuple[Response, int]:
    if not _verify_gitlab_token():
        return jsonify({"ok": False, "error": "unauthorized"}), 403

    event = request.headers.get("X-Gitlab-Event", "")
    delivery = request.headers.get("X-Gitlab-Delivery", "")

    raw = request.get_data(as_text=True)
    payload: Any
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        log.warning("JSON 파싱 실패 — 원문 길이 %s", len(raw))
        payload = {"_parse_error": True, "_raw_preview": _truncate(raw, 500)}

    body_str = json.dumps(payload, ensure_ascii=False, indent=2)
    log.info(
        "GitLab webhook — event=%s delivery=%s body=\n%s",
        event,
        delivery,
        _truncate(body_str, MAX_BODY_LOG_CHARS),
    )

    extra: dict[str, Any] = {}
    if (
        event == "Merge Request Hook"
        and isinstance(payload, dict)
        and not payload.get("_parse_error")
    ):
        try:
            extra = _process_merge_request_hook(payload)
        except ValueError as e:
            log.warning("GitLab API 설정 부족 — %s", e)
            extra = {"api_skipped": str(e)}
        except Exception:
            log.exception("GitLab API 조회 중 오류")
            extra = {"api_error": "see logs"}

    resp_body = {"ok": True, "received_event": event, **extra}
    return jsonify(resp_body), 200


@app.get("/")
def health() -> tuple[Response, int]:
    return jsonify({"status": "ok", "service": "gitlab-webhook-receiver"}), 200


@app.post("/")
def hook_root() -> tuple[Response, int]:
    return _handle_hook()


@app.post("/gitlab-webhook")
def hook_path() -> tuple[Response, int]:
    return _handle_hook()


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8765"))
    log.info("Listening on http://%s:%s (POST / 또는 POST /gitlab-webhook)", host, port)
    app.run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
