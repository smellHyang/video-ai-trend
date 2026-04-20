"""OpenAI 호환 Chat Completions API 로 MR 요약 (urllib만 사용)."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger("ai_summarize")


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len] + f"\n\n... (truncated, was {len(s)} chars)"


def summarize_merge_request(
    *,
    mr_title: str,
    source_branch: str,
    target_branch: str,
    commit_lines: str,
    diff_text: str,
) -> str:
    """
    환경변수:
      AI_ENABLED=1
      OPENAI_API_KEY
      OPENAI_BASE_URL — 기본 https://api.openai.com/v1
      OPENAI_MODEL — 기본 gpt-4o-mini
      AI_MAX_INPUT_CHARS — diff+커밋 합산 자르기 (기본 100000)
    """
    if os.environ.get("AI_ENABLED", "").strip().lower() not in ("1", "true", "yes"):
        raise ValueError("AI_ENABLED 가 켜져 있지 않습니다")

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY 미설정")

    base_url = os.environ.get("OPENAI_API_URL", "").strip() or os.environ.get(
        "OPENAI_BASE_URL", "https://api.openai.com/v1"
    ).strip().rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
    max_in = int(os.environ.get("AI_MAX_INPUT_CHARS", "100000"))

    commits_part = _truncate(commit_lines.strip(), max_in // 4)
    diff_part = _truncate(diff_text.strip(), max_in - len(commits_part))

    system = (
        "당신은 소프트웨어 배포·코드 리뷰 요약 전문가다. "
        "입력된 머지 리퀘스트 제목, 브랜치, 커밋 메시지, diff 일부를 바탕으로 "
        "한국어로 간결하게 정리한다."
    )
    user = f"""다음 GitLab Merge Request 가 대상 브랜치에 머지되었다. 배포 공지·이슈 트래커용으로 쓸 수 있게 요약해줘.

## MR 제목
{mr_title}

## 브랜치
- source: {source_branch}
- target: {target_branch}

## 커밋 메시지 (일부)
{commits_part}

## 코드 diff (일부, 잘릴 수 있음)
```
{diff_part}
```

출력 형식 (마크다운):

### 한줄 요약
(한 문장)

### 주요 변경
- 불릿 3~7개

### 영향 범위
(서비스/모듈/사용자 영향을 짧게)

### 주의·리스크
- 있으면 불릿, 없으면 "특이사항 없음"

### 롤백 시 확인
- 체크리스트 2~5개
"""

    url = f"{base_url}/chat/completions"
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.3,
        },
        ensure_ascii=False,
    ).encode()

    req = urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")[:2000]
        log.error("OpenAI API HTTP %s — %s", e.code, err_body)
        raise

    choice0 = (data.get("choices") or [{}])[0]
    msg = choice0.get("message") or {}
    content = msg.get("content")
    if not content:
        log.error("Unexpected API response: %s", data)
        raise RuntimeError("AI 응답에 content 없음")

    return str(content).strip()
