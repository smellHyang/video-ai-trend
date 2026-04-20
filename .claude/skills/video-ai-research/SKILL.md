---
name: video-ai-research
description: 영상 AI 분야의 최신 기사, 논문, 뉴스를 웹에서 수집하는 스킬. 비디오 생성, 비디오 이해, 영상 편집 AI, 멀티모달, Sora/Runway/Pika 등 관련 키워드로 WebSearch + WebFetch를 활용해 원문을 수집하고 구조화된 JSON으로 저장한다. "영상 AI 수집", "video AI 리서치", "최신 동향 수집" 요청 시 반드시 이 스킬을 사용할 것.
---

# 영상 AI 리서치 스킬

researcher 에이전트가 사용하는 웹 수집 스킬이다. 단순 헤드라인이 아니라 본문까지 읽고 핵심을 추출한다.

## 수집 전략

### 검색 쿼리 세트 (순서대로 실행)

**영문 쿼리:**
1. `"video generation AI" 2025` — 비디오 생성 최신 동향
2. `"text-to-video" model release 2025` — 새 모델 출시
3. `"video understanding" AI model 2025` — 비디오 이해/분석
4. `Sora OR Runway OR Pika OR Kling OR Veo latest news` — 주요 제품 소식
5. `"AI video editing" tool 2025` — AI 편집 도구
6. `multimodal video AI research paper 2025` — 연구 논문
7. `"real-time video AI" OR "video streaming AI" 2025` — 실시간/스트리밍

**한국어 쿼리:**
8. `영상 AI 최신 2025` — 한국 미디어 커버리지
9. `동영상 생성 AI 뉴스` — 국내 뉴스

### 소스 우선순위

| 우선순위 | 소스 | 이유 |
|---------|------|------|
| 1순위 | OpenAI/Google/Meta/Runway 공식 블로그 | 1차 정보, 가장 신뢰성 높음 |
| 2순위 | arXiv, Papers With Code | 기술적 깊이 |
| 3순위 | TechCrunch, VentureBeat, The Verge | 업계 영향력 분석 |
| 4순위 | HackerNews, Reddit r/artificial | 커뮤니티 반응 |

## 수집 프로세스

1. 각 쿼리로 WebSearch 실행
2. 상위 3~5개 결과 URL 추출
3. WebFetch로 본문 읽기 (접근 불가 시 → 다음 결과로 대체)
4. 중복 제거: 동일 사건을 다룬 기사는 가장 상세한 것 1개만 유지
5. 날짜 확인: 7일 이내 우선, 이전 중요 기사는 `importance: "high"`로 포함
6. `analysis/` 디렉토리 생성 후 `articles.json` 저장

## 출력 스키마

`analysis/articles.json`에 저장:

```json
[
  {
    "id": "article-001",
    "title": "기사 제목",
    "source": "출처명 (TechCrunch, arXiv 등)",
    "url": "원본 URL",
    "published_date": "YYYY-MM-DD",
    "category": "generation|understanding|editing|multimodal|industry|research",
    "summary": "200자 이내 핵심 요약 (한국어)",
    "key_points": ["핵심 포인트 1", "핵심 포인트 2"],
    "companies_mentioned": ["OpenAI", "Google"],
    "technologies_mentioned": ["Sora", "diffusion model"],
    "importance": "high|medium|low",
    "fetch_failed": false
  }
]
```

## 에러 처리

- **WebFetch 실패**: `fetch_failed: true` 플래그 추가, 메타 정보만으로 항목 생성
- **접근 제한 페이지**: 캐시된 버전 또는 다른 소스의 동일 내용으로 대체
- **수집 수 부족(<15개)**: analyst에게 SendMessage로 보고, 추가 키워드 요청

## 완료 알림

수집 완료 후 analyst에게 SendMessage:
```
수집 완료: {N}개 기사 → analysis/articles.json
카테고리 분포: {generation: N, understanding: N, ...}
주목할 발견: {특이사항 1줄}
```
