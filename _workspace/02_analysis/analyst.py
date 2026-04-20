from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_PATH = ROOT / "01_research" / "articles.json"
OUTPUT_PATH = ROOT / "02_analysis" / "analysis_report.json"

KNOWN_KEYS = {
    "id",
    "title",
    "source",
    "url",
    "published_date",
    "category",
    "summary",
    "key_points",
    "companies_mentioned",
    "technologies_mentioned",
    "importance",
    "fetch_failed",
}


@dataclass
class Article:
    id: str
    title: str
    source: str
    url: str
    published_date: str
    category: str
    summary: str
    key_points: list[str]
    companies_mentioned: list[str]
    technologies_mentioned: list[str]
    importance: str
    fetch_failed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "published_date": self.published_date,
            "category": self.category,
            "summary": self.summary,
            "key_points": self.key_points,
            "companies_mentioned": self.companies_mentioned,
            "technologies_mentioned": self.technologies_mentioned,
            "importance": self.importance,
            "fetch_failed": self.fetch_failed,
        }


def read_articles() -> list[Article]:
    raw = RESEARCH_PATH.read_text(encoding="utf-8", errors="replace")
    blocks = extract_object_blocks(raw)
    articles: list[Article] = []
    for block in blocks:
        fields = parse_block(block)
        if not fields.get("id"):
            continue
        articles.append(
            Article(
                id=parse_scalar(fields.get("id", "")),
                title=parse_scalar(fields.get("title", "")),
                source=parse_scalar(fields.get("source", "")),
                url=parse_scalar(fields.get("url", "")),
                published_date=parse_scalar(fields.get("published_date", "")),
                category=parse_scalar(fields.get("category", "unknown")),
                summary=parse_scalar(fields.get("summary", "")),
                key_points=parse_array(fields.get("key_points", "")),
                companies_mentioned=parse_array(fields.get("companies_mentioned", "")),
                technologies_mentioned=parse_array(fields.get("technologies_mentioned", "")),
                importance=parse_scalar(fields.get("importance", "unknown")),
                fetch_failed=parse_bool(fields.get("fetch_failed", "false")),
            )
        )
    return articles


def extract_object_blocks(raw: str) -> list[str]:
    lines = raw.splitlines()
    blocks: list[str] = []
    current: list[str] = []
    inside = False

    for line in lines:
        stripped = line.strip()
        if stripped == "{":
            inside = True
            current = [line]
            continue
        if inside:
            current.append(line)
            if stripped in {"}", "},"}:
                blocks.append("\n".join(current))
                current = []
                inside = False

    if current:
        blocks.append("\n".join(current))
    return blocks


def parse_block(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_key: str | None = None
    buffer: list[str] = []

    for line in block.splitlines():
        key_match = re.match(r'^\s*"([A-Za-z_]+)"\s*:\s*(.*)$', line)
        if key_match and key_match.group(1) in KNOWN_KEYS:
            if current_key is not None:
                fields[current_key] = cleanup_value("\n".join(buffer))
            current_key = key_match.group(1)
            buffer = [key_match.group(2)]
            continue

        if current_key is not None:
            buffer.append(line)

    if current_key is not None:
        fields[current_key] = cleanup_value("\n".join(buffer))

    return fields


def cleanup_value(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r",$", "", text)
    return text.strip()


def parse_scalar(raw: str) -> str:
    text = normalize_space(raw).rstrip(",")
    if text.startswith('"'):
        text = text[1:]
    if text.endswith('"'):
        text = text[:-1]
    return normalize_space(text)


def parse_array(raw: str) -> list[str]:
    if not raw:
        return []

    quoted = re.findall(r'"([^"]+)"', raw, flags=re.DOTALL)
    if quoted:
        return [normalize_space(item) for item in quoted if normalize_space(item)]

    body = raw.strip().strip("[]")
    parts = [normalize_space(part.strip(" ,")) for part in body.split(",")]
    return [part for part in parts if part]


def parse_bool(raw: str) -> bool:
    return raw.strip().lower().startswith("true")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().strip('"')


def safe_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def top_items(counter: Counter[str], limit: int = 10) -> list[dict[str, Any]]:
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def build_trend_summary(articles: list[Article]) -> list[str]:
    categories = Counter(article.category for article in articles)
    companies = Counter(
        company
        for article in articles
        for company in article.companies_mentioned
    )
    tech = Counter(
        item
        for article in articles
        for item in article.technologies_mentioned
    )
    failed = sum(1 for article in articles if article.fetch_failed)
    valid_dates = [safe_date(article.published_date) for article in articles]
    valid_dates = [item for item in valid_dates if item is not None]
    latest = max(valid_dates, default=None)

    lines = [
        f"가장 많이 나온 주제는 {categories.most_common(1)[0][0]}이며 전체 {len(articles)}건 중 {categories.most_common(1)[0][1]}건입니다."
        if categories
        else "카테고리 집계가 없습니다.",
        f"가장 자주 언급된 기업은 {companies.most_common(1)[0][0]}({companies.most_common(1)[0][1]}회)입니다."
        if companies
        else "기업 언급 집계가 없습니다.",
        f"가장 자주 언급된 기술은 {tech.most_common(1)[0][0]}({tech.most_common(1)[0][1]}회)입니다."
        if tech
        else "기술 언급 집계가 없습니다.",
        f"수집 데이터 중 fetch 실패 플래그는 {failed}건이며, 최신 기사 날짜는 {latest.isoformat()}입니다."
        if latest
        else f"수집 데이터 중 fetch 실패 플래그는 {failed}건입니다.",
    ]

    narratives: list[str] = []
    if companies["Google"] >= 4:
        narratives.append("Google 생태계 확장과 제품 통합이 최근 영상 AI 시장의 핵심 축으로 보입니다.")
    if companies["OpenAI"] >= 3 or tech["Sora"] >= 3:
        narratives.append("Sora 축소 또는 종료 이후 대체 모델 경쟁 구도가 시장 재편 신호로 반복 등장합니다.")
    if categories["multimodal"] + categories["understanding"] >= 5:
        narratives.append("생성뿐 아니라 이해·멀티모달 처리까지 확장되는 흐름이 뚜렷합니다.")
    if categories["editing"] >= 3:
        narratives.append("편집 자동화와 후반작업 효율화도 별도 세그먼트로 성장 중입니다.")

    return lines + narratives


def build_signal_cards(articles: list[Article]) -> list[dict[str, Any]]:
    categories = Counter(article.category for article in articles)
    importance = Counter(article.importance for article in articles)
    companies = Counter(
        company
        for article in articles
        for company in article.companies_mentioned
    )
    tech = Counter(
        item
        for article in articles
        for item in article.technologies_mentioned
    )

    return [
        {
            "title": "시장 재편",
            "signal": "Sora 공백과 대체재 부상",
            "evidence": [
                "OpenAI/Sora 관련 언급 빈도",
                "Kling, Runway, Google 계열 모델 동시 부상",
            ],
            "strength": companies["OpenAI"] + tech["Sora"],
        },
        {
            "title": "플랫폼화",
            "signal": "Google의 제품 통합 가속",
            "evidence": [
                "Google, Workspace, YouTube, Gemini 연계 기사 다수",
                "Veo 3.1, Google Vids, Flow 등 연결성 강조",
            ],
            "strength": companies["Google"],
        },
        {
            "title": "멀티모달 확장",
            "signal": "생성에서 이해/분석까지 확대",
            "evidence": [
                "multimodal + understanding 카테고리 증가",
                "긴 영상 분석, 통합 워크스페이스, 대화형 분석 사례",
            ],
            "strength": categories["multimodal"] + categories["understanding"],
        },
        {
            "title": "데이터 품질",
            "signal": "원문 품질 보정 필요",
            "evidence": [
                f"fetch_failed={sum(1 for a in articles if a.fetch_failed)}",
                "문자 인코딩 또는 일부 필드 파손 감지",
            ],
            "strength": importance["high"],
        },
    ]


def build_report(articles: list[Article]) -> dict[str, Any]:
    published_dates = [safe_date(article.published_date) for article in articles]
    valid_dates = [item for item in published_dates if item is not None]
    category_counts = Counter(article.category for article in articles)
    importance_counts = Counter(article.importance for article in articles)
    company_counts = Counter(
        company
        for article in articles
        for company in article.companies_mentioned
    )
    technology_counts = Counter(
        item
        for article in articles
        for item in article.technologies_mentioned
    )

    recent_articles = sorted(
        articles,
        key=lambda article: article.published_date,
        reverse=True,
    )[:8]

    high_priority = [
        article.as_dict()
        for article in articles
        if article.importance == "high"
    ][:10]

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": str(RESEARCH_PATH.relative_to(ROOT)),
        "summary": {
            "article_count": len(articles),
            "high_importance_count": importance_counts.get("high", 0),
            "fetch_failed_count": sum(1 for article in articles if article.fetch_failed),
            "category_count": len(category_counts),
            "date_range": {
                "start": min(valid_dates).isoformat() if valid_dates else None,
                "end": max(valid_dates).isoformat() if valid_dates else None,
            },
        },
        "trend_summary": build_trend_summary(articles),
        "category_breakdown": dict(category_counts),
        "importance_breakdown": dict(importance_counts),
        "top_companies": top_items(company_counts, limit=12),
        "top_technologies": top_items(technology_counts, limit=12),
        "signal_cards": build_signal_cards(articles),
        "recent_articles": [article.as_dict() for article in recent_articles],
        "high_priority_articles": high_priority,
        "quality_notes": [
            "원본 기사 파일에서 문자 인코딩 깨짐이 관찰됩니다.",
            "일부 문자열 따옴표 누락으로 엄격 JSON 파싱이 불가능해 복원 로더를 사용했습니다.",
            "배열형 필드는 따옴표 기반으로 복구했기 때문에 일부 항목이 축약되었을 수 있습니다.",
        ],
    }


def main() -> None:
    articles = read_articles()
    report = build_report(articles)
    OUTPUT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(articles)} articles to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
