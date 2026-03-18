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


def build_company_queries(company: str, topic: str) -> list[str]:
    queries = [f"{company} {topic}"]
    queries.extend(f"{company} {keyword}" for keyword in STRATEGY_KEYWORDS)
    queries.extend(f"{company} {keyword}" for keyword in MARKET_KEYWORDS)
    return queries


def rewrite_query(base_query: str, focus_keyword: str) -> str:
    return f"{base_query} {focus_keyword}".strip()
