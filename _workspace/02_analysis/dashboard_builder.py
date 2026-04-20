from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "02_analysis" / "analysis_report.json"
OUTPUT_PATH = ROOT / "02_analysis" / "dashboard.html"


def load_report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value))


def render_stat_card(label: str, value: object) -> str:
    return f"""
    <section class="stat-card">
      <div class="stat-label">{esc(label)}</div>
      <div class="stat-value">{esc(value)}</div>
    </section>
    """


def render_named_bars(items: list[dict], modifier: str = "") -> str:
    if not items:
        return '<div class="empty">데이터 없음</div>'

    max_count = max(item["count"] for item in items) or 1
    bars = []
    for item in items:
        width = round(item["count"] / max_count * 100, 1)
        bars.append(
            f"""
            <div class="bar-row {modifier}">
              <div class="bar-meta">
                <span>{esc(item["name"])}</span>
                <strong>{esc(item["count"])}</strong>
              </div>
              <div class="bar-track">
                <div class="bar-fill" style="width:{width}%"></div>
              </div>
            </div>
            """
        )
    return "\n".join(bars)


def render_articles(articles: list[dict]) -> str:
    if not articles:
        return '<div class="empty">기사 없음</div>'

    cards = []
    for article in articles:
        cards.append(
            f"""
            <article class="article-card">
              <div class="article-meta">
                <span>{esc(article.get("published_date"))}</span>
                <span>{esc(article.get("category"))}</span>
                <span>{esc(article.get("importance"))}</span>
              </div>
              <h3>{esc(article.get("title"))}</h3>
              <p>{esc(article.get("summary"))}</p>
              <div class="article-footer">
                <span>{esc(article.get("source"))}</span>
                <a href="{esc(article.get("url"))}" target="_blank" rel="noreferrer">원문</a>
              </div>
            </article>
            """
        )
    return "\n".join(cards)


def render_signal_cards(cards: list[dict]) -> str:
    if not cards:
        return '<div class="empty">신호 없음</div>'

    rendered = []
    for card in cards:
        evidence = "".join(f"<li>{esc(item)}</li>" for item in card.get("evidence", []))
        rendered.append(
            f"""
            <article class="signal-card">
              <div class="signal-header">
                <span class="eyebrow">{esc(card.get("title"))}</span>
                <strong>{esc(card.get("strength"))}</strong>
              </div>
              <h3>{esc(card.get("signal"))}</h3>
              <ul>{evidence}</ul>
            </article>
            """
        )
    return "\n".join(rendered)


def render_category_rows(category_breakdown: dict) -> str:
    items = [{"name": key, "count": value} for key, value in sorted(category_breakdown.items())]
    return render_named_bars(items, modifier="compact")


def build_html(report: dict) -> str:
    summary = report["summary"]
    trend_summary = "".join(f"<li>{esc(item)}</li>" for item in report["trend_summary"])
    quality_notes = "".join(f"<li>{esc(item)}</li>" for item in report["quality_notes"])

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Video AI Trend Dashboard</title>
  <style>
    :root {{
      --bg: #f4efe7;
      --panel: rgba(255,255,255,0.74);
      --ink: #1a2233;
      --muted: #5c6578;
      --line: rgba(26,34,51,0.12);
      --accent: #d75c37;
      --accent-2: #1f8f8b;
      --accent-3: #f1b23e;
      --shadow: 0 22px 60px rgba(24, 29, 40, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(215,92,55,0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(31,143,139,0.15), transparent 30%),
        linear-gradient(180deg, #f7f2ea 0%, #efe8dc 100%);
      font-family: "Segoe UI", "Apple SD Gothic Neo", sans-serif;
    }}
    a {{ color: inherit; }}
    .shell {{
      width: min(1200px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 56px;
    }}
    .hero {{
      display: grid;
      gap: 18px;
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: linear-gradient(135deg, rgba(255,255,255,0.78), rgba(255,248,239,0.72));
      backdrop-filter: blur(18px);
      box-shadow: var(--shadow);
    }}
    .hero h1 {{
      margin: 0;
      font-size: clamp(2rem, 5vw, 4.4rem);
      line-height: 0.95;
      letter-spacing: -0.04em;
    }}
    .hero p {{
      margin: 0;
      max-width: 760px;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.6;
    }}
    .hero-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .chip {{
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(26,34,51,0.06);
      border: 1px solid rgba(26,34,51,0.08);
      font-size: 0.92rem;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin-top: 18px;
    }}
    .stat-card, .panel, .signal-card, .article-card {{
      border: 1px solid var(--line);
      border-radius: 24px;
      background: var(--panel);
      backdrop-filter: blur(16px);
      box-shadow: var(--shadow);
    }}
    .stat-card {{
      padding: 18px 20px;
    }}
    .stat-label {{
      color: var(--muted);
      font-size: 0.9rem;
      margin-bottom: 8px;
    }}
    .stat-value {{
      font-size: clamp(1.6rem, 3vw, 2.4rem);
      font-weight: 700;
      letter-spacing: -0.04em;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 16px;
      margin-top: 18px;
    }}
    .panel {{
      padding: 22px;
    }}
    .panel h2 {{
      margin: 0 0 14px;
      font-size: 1.1rem;
    }}
    ul {{
      margin: 0;
      padding-left: 18px;
      line-height: 1.6;
    }}
    .signals {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-top: 18px;
    }}
    .signal-card {{
      padding: 20px;
    }}
    .signal-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      color: var(--muted);
    }}
    .signal-card h3 {{
      margin: 12px 0;
      font-size: 1.2rem;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.74rem;
    }}
    .bar-row {{
      margin-bottom: 12px;
    }}
    .bar-meta {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-size: 0.92rem;
      margin-bottom: 6px;
    }}
    .bar-track {{
      overflow: hidden;
      height: 10px;
      border-radius: 999px;
      background: rgba(26,34,51,0.08);
    }}
    .bar-fill {{
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--accent), var(--accent-2));
    }}
    .compact .bar-fill {{
      background: linear-gradient(90deg, var(--accent-2), var(--accent-3));
    }}
    .articles {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-top: 18px;
    }}
    .article-card {{
      padding: 18px;
    }}
    .article-card h3 {{
      margin: 12px 0 10px;
      font-size: 1.05rem;
      line-height: 1.35;
    }}
    .article-card p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
      min-height: 72px;
    }}
    .article-meta, .article-footer {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 8px 12px;
      font-size: 0.85rem;
      color: var(--muted);
    }}
    .section-title {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin-top: 28px;
      margin-bottom: 12px;
    }}
    .section-title h2 {{
      margin: 0;
      font-size: 1.3rem;
    }}
    .empty {{
      color: var(--muted);
    }}
    @media (max-width: 900px) {{
      .stats, .grid, .signals, .articles {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="hero-meta">
        <span class="chip">Generated {esc(report["generated_at"])}</span>
        <span class="chip">Date Range {esc(summary["date_range"]["start"])} to {esc(summary["date_range"]["end"])}</span>
        <span class="chip">Source {esc(report["source_file"])}</span>
      </div>
      <h1>Video AI Trend Dashboard</h1>
      <p>기사 수집 결과를 복원 로더로 정규화한 뒤 시장 재편, 플랫폼 통합, 멀티모달 확장, 편집 자동화 흐름을 한 화면에서 보도록 구성한 정적 대시보드입니다.</p>
    </section>

    <section class="stats">
      {render_stat_card("Articles", summary["article_count"])}
      {render_stat_card("High Importance", summary["high_importance_count"])}
      {render_stat_card("Fetch Failed", summary["fetch_failed_count"])}
      {render_stat_card("Categories", summary["category_count"])}
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Analyst Summary</h2>
        <ul>{trend_summary}</ul>
      </div>
      <div class="panel">
        <h2>Quality Notes</h2>
        <ul>{quality_notes}</ul>
      </div>
    </section>

    <div class="section-title">
      <h2>Signal Cards</h2>
      <span>{esc(len(report["signal_cards"]))} signals</span>
    </div>
    <section class="signals">
      {render_signal_cards(report["signal_cards"])}
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Top Companies</h2>
        {render_named_bars(report["top_companies"])}
      </div>
      <div class="panel">
        <h2>Top Technologies</h2>
        {render_named_bars(report["top_technologies"])}
      </div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Category Breakdown</h2>
        {render_category_rows(report["category_breakdown"])}
      </div>
      <div class="panel">
        <h2>Recent Watchlist</h2>
        <ul>
          {"".join(f"<li>{esc(item['published_date'])} | {esc(item['title'])}</li>" for item in report["recent_articles"][:6])}
        </ul>
      </div>
    </section>

    <div class="section-title">
      <h2>High Priority Articles</h2>
      <span>{esc(len(report["high_priority_articles"]))} items</span>
    </div>
    <section class="articles">
      {render_articles(report["high_priority_articles"])}
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    report = load_report()
    OUTPUT_PATH.write_text(build_html(report), encoding="utf-8")
    print(f"Wrote dashboard to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
