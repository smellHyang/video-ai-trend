---
name: trend-analysis
description: 수집된 영상 AI 기사 데이터를 분석하여 트렌드, 패턴, 인사이트를 추출하는 스킬. 개별 기사를 클러스터로 묶고, 핵심 플레이어를 순위화하며, "왜 중요한가"와 "어디로 향하는가"를 분석한다. "트렌드 분석", "영상 AI 동향 분석", "기사 분석" 요청 시 반드시 이 스킬을 사용할 것.
---

# 영상 AI 트렌드 분석 스킬

analyst 에이전트가 사용한다. `_workspace/01_research/articles.json`을 읽고 구조화된 분석 보고서를 생성한다.

## 분석 프레임워크

### 1. 트렌드 클러스터링

비슷한 주제의 기사를 묶어 **트렌드 군집**을 만든다:
- 클러스터명: 사용자가 이해할 수 있는 명확한 이름 (예: "오픈소스 비디오 모델 급증")
- 클러스터당 최소 2개 기사 — 단독 기사는 "기타" 클러스터로
- 클러스터 중요도: 포함 기사 수 × 평균 importance 점수로 산정

### 2. 핵심 플레이어 분석

**순위화 기준:**
- 언급 빈도 (기사에서 몇 번 등장했는가)
- 기사 중요도 (high 기사에 등장했는가)
- 행위 유형 (새 모델 출시 > 파트너십 > 코멘트)

### 3. 중요도 평가 3축

| 축 | 기준 |
|----|------|
| 기술 혁신성 | 새로운 접근법인가? 기존 한계를 극복했는가? |
| 시장 영향력 | 실제 제품/서비스에 영향이 있는가? |
| 미디어 반응 | 여러 미디어에서 다뤘는가? 커뮤니티 반응이 강한가? |

## 분석 프로세스

1. `analysis/articles.json` 읽기
2. 기사 수 확인 → 10개 미만이면 researcher에게 추가 수집 요청
3. 카테고리별 분류 및 클러스터링
4. 시간 축 구성: 날짜별로 가장 중요한 이벤트 1줄 요약
5. 회사/기술명 집계 및 순위화
6. editor_picks 선정: importance=high 기사 중 가장 파급력 큰 5개
7. `analysis/report.json` 저장 (디렉토리는 이미 존재)

## 출력 스키마

`analysis/report.json`:

```json
{
  "generated_at": "2025-04-09T12:00:00Z",
  "period": { "from": "2025-04-02", "to": "2025-04-09" },
  "summary": "이번 주 영상 AI 동향 3줄 요약 (한국어)",
  "trends": [
    {
      "name": "트렌드명",
      "description": "왜 중요한지 2~3문장 설명",
      "article_count": 5,
      "importance": "high|medium|low",
      "article_ids": ["article-001", "article-002"]
    }
  ],
  "top_companies": [
    {
      "name": "회사명",
      "mention_count": 10,
      "key_news": "이번 주 주요 뉴스 한 줄 (한국어)"
    }
  ],
  "top_technologies": [
    {
      "name": "기술명 (영문)",
      "mention_count": 7,
      "context": "어떤 맥락으로 등장했는지 한 줄"
    }
  ],
  "timeline": [
    { "date": "YYYY-MM-DD", "headline": "하루 주요 사건 한 줄 (한국어)" }
  ],
  "editor_picks": ["article-001", "article-002"],
  "total_articles": 30,
  "notes": "카테고리 편중 등 특이사항"
}
```

## 에러 처리

- **기사 10개 미만**: researcher에게 SendMessage로 추가 수집 요청 후 대기
- **카테고리 편중**: `notes` 필드에 기록, 분석은 계속 진행

## 완료 알림

분석 완료 후 dashboard-builder에게 SendMessage:
```
분석 완료: 트렌드 {N}개, editor_picks {N}개
강조 요청: {특별히 시각적으로 부각해야 할 사항}
```
