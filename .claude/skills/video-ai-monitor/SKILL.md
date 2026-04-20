---
name: video-ai-monitor
description: 영상 AI 트렌드 모니터링 대시보드를 처음부터 끝까지 자동으로 생성하는 오케스트레이터 스킬. researcher → analyst → dashboard-builder 3개 에이전트를 에이전트 팀으로 조율하여 최신 영상 AI 뉴스를 수집하고 분석해서 HTML 대시보드를 만든다. "대시보드 만들어줘", "영상 AI 모니터링", "video AI dashboard", "다시 실행", "업데이트", "대시보드 재생성", "수정해줘", "이어서 해줘" 요청 시 반드시 이 스킬을 사용할 것.
---

# 영상 AI 모니터링 대시보드 오케스트레이터

## 실행 모드
**에이전트 팀** — researcher, analyst, dashboard-builder가 TeamCreate로 팀을 구성하고, TaskCreate + SendMessage로 자체 조율한다.

## Phase 0: 컨텍스트 확인

실행 전 기존 산출물 존재 여부를 확인한다:

- `_workspace/` 미존재 → **초기 실행** (Phase 1부터)
- `_workspace/` 존재 + 새 실행 요청 → 기존 `_workspace/`를 `_workspace_prev/`로 이동 후 **새 실행**
- `_workspace/` 존재 + 특정 단계 수정 요청 → **부분 재실행** (해당 에이전트만 재호출)

## Phase 1: 팀 구성 및 작업 분배

```
TeamCreate(
  team_name: "video-ai-monitor-team",
  members: ["researcher", "analyst", "dashboard-builder"]
)
```

TaskCreate로 작업 등록:
- Task 1: 영상 AI 기사 수집 (담당: researcher)
- Task 2: 트렌드 분석 보고서 생성 (담당: analyst, 의존: Task 1)
- Task 3: HTML 대시보드 생성 (담당: dashboard-builder, 의존: Task 2)

## Phase 2: researcher 호출

researcher 에이전트에게 다음을 지시한다:

```
video-ai-research 스킬을 사용하여 영상 AI 최신 기사를 수집하라.
- 수집 기간: 최근 7일
- 최소 수집 수: 20개
- 집중 키워드: video generation, text-to-video, Sora, Runway, Pika, Kling, Veo, video understanding
- 출력: analysis/articles.json
수집 완료 후 analyst에게 SendMessage로 완료 알림을 보내라.
```

## Phase 3: analyst 호출

analyst 에이전트에게 다음을 지시한다 (researcher 완료 후):

```
trend-analysis 스킬을 사용하여 수집된 기사를 분석하라.
- 입력: analysis/articles.json
- 트렌드 클러스터: 최소 3개, 최대 7개
- editor_picks: 최대 5개
- 출력: analysis/report.json
분석 완료 후 dashboard-builder에게 SendMessage로 완료 알림을 보내라.
```

## Phase 4: dashboard-builder 호출

dashboard-builder 에이전트에게 다음을 지시한다 (analyst 완료 후):

```
dashboard-build 스킬을 사용하여 HTML 대시보드를 생성하라.
- 입력 1: analysis/report.json
- 입력 2: analysis/articles.json
- 출력: dashboard/index.html
- 다크 테마, 반응형, Chart.js 기반 차트 포함
대시보드 완성 후 오케스트레이터에게 SendMessage로 완료 알림을 보내라.
```

## Phase 5: 결과 확인 및 보고

1. `dashboard/index.html` 존재 확인
2. 사용자에게 결과 요약 보고:
   - 수집된 기사 수
   - 발견된 주요 트렌드
   - 대시보드 파일 경로
3. 팀 정리

## 데이터 전달 프로토콜

| 전달 방식 | 용도 |
|---------|------|
| 파일 기반 (`_workspace/`) | 에이전트 간 대용량 데이터 전달 |
| SendMessage | 단계 완료 알림, 추가 요청 |
| TaskUpdate | 진행 상황 추적 |

**파일 경로 컨벤션:**
- `analysis/articles.json` — researcher 출력
- `analysis/report.json` — analyst 출력
- `dashboard/index.html` — dashboard-builder 최종 출력

## 에러 핸들링

| 에러 상황 | 처리 방식 |
|---------|---------|
| researcher 수집 15개 미만 | 1회 재시도 (쿼리 확장), 재실패 시 수집된 것으로 진행 |
| analyst 분석 실패 | 1회 재시도, 재실패 시 보고서에 "분석 실패" 명시 |
| dashboard-builder 실패 | 1회 재시도, 재실패 시 _workspace 파일 경로 사용자에게 안내 |
| 상충 데이터 | 삭제하지 않고 출처 병기 |

## 테스트 시나리오

### 정상 흐름
1. "영상 AI 대시보드 만들어줘" → video-ai-monitor 트리거
2. researcher가 20개+ 기사 수집 → `analysis/articles.json` 생성
3. analyst가 트렌드 분석 → `analysis/report.json` 생성
4. dashboard-builder가 `dashboard/index.html` 생성
5. 사용자에게 완료 보고

### 에러 흐름
1. researcher가 10개만 수집 → analyst에게 SendMessage → researcher 재수집 요청 → 합쳐서 진행
2. 특정 URL 접근 불가 → `fetch_failed: true` 플래그 후 다음 기사로 진행
