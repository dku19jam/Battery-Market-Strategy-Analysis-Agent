"""Query building utilities."""

from __future__ import annotations


STRATEGY_KEYWORDS = (
    "portfolio diversification",
    "core competitiveness",
    "risk",
)

MARKET_KEYWORDS = (
    "battery market",
    "EV chasm",
    "supply chain",
)


WEB_SEARCH_QUERY_KEYWORDS = (
    "재무 건전성",
    "배터리 공급망",
    "신규 투자",
    "R&D",
    "ESG",
    "정책 지원",
)


def build_company_queries(company: str, topic: str) -> list[str]:
    queries = [f"{company} {topic}"]
    queries.extend(f"{company} {keyword}" for keyword in STRATEGY_KEYWORDS)
    queries.extend(f"{company} {keyword}" for keyword in MARKET_KEYWORDS)
    return queries


def build_web_search_queries(company: str, topic: str) -> list[str]:
    """Build web queries to increase coverage and source diversity."""
    queries = [f"{company} {topic}"]
    queries.extend(f"{company} {keyword}" for keyword in STRATEGY_KEYWORDS)
    queries.extend(f"{company} {keyword}" for keyword in WEB_SEARCH_QUERY_KEYWORDS)
    queries.extend(f"{company} {keyword}" for keyword in MARKET_KEYWORDS)
    return queries


def rewrite_query(base_query: str, focus_keyword: str) -> str:
    return f"{base_query} {focus_keyword}".strip()
