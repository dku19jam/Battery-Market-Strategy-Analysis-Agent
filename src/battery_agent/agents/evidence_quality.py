from urllib.parse import urlparse

from battery_agent.models.evidence import EvidenceItem

SOURCE_TYPE_PRIORITY = {
    "report": 3,
    "memo": 3,
    "paper": 2,
    "web": 1,
    "local": 1,
    "pdf": 2,
}

PREFERRED_WEB_DOMAINS = {
    "catl.com",
    "fitchratings.com",
    "www.fitchratings.com",
    "iea.org",
    "www.iea.org",
    "koreasecurities.com",
    "www.reuters.com",
    "reuters.com",
    "sec.or.kr",
    "dart.fss.or.kr",
    "samsungpop.com",
    "www.samsungpop.com",
    "imeritz.com",
    "home.imeritz.com",
    "lgensol.com",
    "www.lgensol.com",
    "sne.com",
    "sneresearch.com",
    "fitchratings.com",
}

LOW_TRUST_WEB_DOMAINS = {
    "blog.naver.com",
    "tistory.com",
    "www.tistory.com",
    "youtube.com",
    "www.youtube.com",
    "ffighting.net",
    "www.ffighting.net",
}

REFERENCE_QUALITY_THRESHOLD = 1.9


def is_quality_reference(candidate: EvidenceItem, *, min_score: float = REFERENCE_QUALITY_THRESHOLD) -> bool:
    return evidence_quality(candidate) >= min_score


def evidence_quality(item: EvidenceItem) -> float:
    source_type = (item.source_type or "").lower()
    base = SOURCE_TYPE_PRIORITY.get(source_type, 1.0)
    if source_type == "web":
        base = 1.0 + _web_domain_bonus(item.url or item.source)
    quality = base
    if item.snippet:
        quality += min(0.5, len(item.snippet.strip()) / 1200.0)
    return quality


def evidence_sort_key(item: EvidenceItem) -> tuple[float, float]:
    return (evidence_quality(item), item.score)


def _web_domain_bonus(value: str) -> float:
    domain = _extract_domain(value)
    if not domain:
        return 0.0
    if domain in PREFERRED_WEB_DOMAINS:
        return 0.9
    if domain in LOW_TRUST_WEB_DOMAINS:
        return 0.05
    if "blog." in domain:
        return 0.1
    return 0.35


def _extract_domain(value: str) -> str:
    parsed = urlparse(value)
    candidate = parsed.netloc or value
    if candidate.startswith("www."):
        candidate = candidate[4:]
    return candidate.lower()
