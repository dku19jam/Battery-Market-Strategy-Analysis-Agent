"""Comparison evaluation agent."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from battery_agent.agents._prompt_builders import (
    comparison_schema,
    comparison_system_prompt,
    comparison_user_prompt,
)
from battery_agent.config import Settings
from battery_agent.llm.openai_structured import StructuredOpenAIClient
from battery_agent.models.analysis import CompanyAnalysisResult
from battery_agent.models.report import (
    CompanyMetric,
    ComparisonResult,
    NormalizedCompanyAnalysis,
    SWOTSection,
)
from battery_agent.storage.json_store import write_json


class StructuredLlmLike(Protocol):
    def generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: dict[str, object],
    ) -> dict[str, object]:
        ...


def run_comparison(
    lg_analysis: CompanyAnalysisResult,
    catl_analysis: CompanyAnalysisResult,
    llm_client: StructuredLlmLike | None = None,
    model: str | None = None,
    artifact_path: Path | None = None,
) -> ComparisonResult:
    settings = Settings.from_env() if llm_client is None or model is None else None
    client = llm_client or StructuredOpenAIClient(api_key=settings.openai_api_key)
    selected_model = model or settings.default_model
    normalized_companies = [
        NormalizedCompanyAnalysis(
            company=lg_analysis.company,
            strategy_summary=lg_analysis.strategy_summary,
            strengths=list(lg_analysis.strengths),
            risks=list(lg_analysis.risks),
            citations=list(lg_analysis.citations),
            metrics=[metric.to_dict() for metric in lg_analysis.metrics],
            partial=lg_analysis.partial,
        ),
        NormalizedCompanyAnalysis(
            company=catl_analysis.company,
            strategy_summary=catl_analysis.strategy_summary,
            strengths=list(catl_analysis.strengths),
            risks=list(catl_analysis.risks),
            citations=list(catl_analysis.citations),
            metrics=[metric.to_dict() for metric in catl_analysis.metrics],
            partial=catl_analysis.partial,
        ),
    ]
    payload = client.generate_json(
        model=selected_model,
        system_prompt=comparison_system_prompt(),
        user_prompt=comparison_user_prompt(lg_analysis, catl_analysis),
        schema_name="comparison_evaluation",
        schema=comparison_schema(),
    )
    refinement_requests: list[str] = list(payload.get("refinement_requests", []))
    if lg_analysis.partial:
        refinement_requests.append(lg_analysis.company)
    if catl_analysis.partial:
        refinement_requests.append(catl_analysis.company)
    refinement_requests = list(dict.fromkeys(refinement_requests))

    result = ComparisonResult(
        normalized_companies=normalized_companies,
        strategy_differences=[
            str(item).strip() for item in payload.get("strategy_differences", []) if str(item).strip()
        ]
        or [f"LG: {lg_analysis.strategy_summary}", f"CATL: {catl_analysis.strategy_summary}"],
        strengths_weaknesses=[
            str(item).strip() for item in payload.get("strengths_weaknesses", []) if str(item).strip()
        ]
        or [
            f"LG 강점: {', '.join(lg_analysis.strengths)}",
            f"CATL 강점: {', '.join(catl_analysis.strengths)}",
            f"LG 리스크: {', '.join(lg_analysis.risks)}",
            f"CATL 리스크: {', '.join(catl_analysis.risks)}",
        ],
        swot=_build_swot(payload, lg_analysis, catl_analysis),
        insights=[str(item).strip() for item in payload.get("insights", []) if str(item).strip()]
        or ["두 기업 모두 다각화 전략과 리스크 관리 역량 비교가 핵심이다."],
        company_metrics=_build_company_metrics(payload, lg_analysis, catl_analysis),
        refinement_requests=refinement_requests,
        next_action="reference" if not refinement_requests else "analysis_refinement",
    )
    if artifact_path is not None:
        write_json(artifact_path, result.to_dict())
    return result


def _build_swot(
    payload: dict[str, object],
    lg_analysis: CompanyAnalysisResult,
    catl_analysis: CompanyAnalysisResult,
) -> SWOTSection:
    swot_payload = payload.get("swot", {})
    if isinstance(swot_payload, dict):
        strengths = [str(item).strip() for item in swot_payload.get("strengths", []) if str(item).strip()]
        weaknesses = [str(item).strip() for item in swot_payload.get("weaknesses", []) if str(item).strip()]
        opportunities = [
            str(item).strip() for item in swot_payload.get("opportunities", []) if str(item).strip()
        ]
        threats = [str(item).strip() for item in swot_payload.get("threats", []) if str(item).strip()]
    else:
        strengths = []
        weaknesses = []
        opportunities = []
        threats = []

    if not strengths:
        strengths = [
            f"{lg_analysis.company}: {', '.join(lg_analysis.strengths[:2]) or '강점 근거 부족'}",
            f"{catl_analysis.company}: {', '.join(catl_analysis.strengths[:2]) or '강점 근거 부족'}",
        ]
    if not weaknesses:
        weaknesses = [
            f"{lg_analysis.company}: {', '.join(lg_analysis.risks[:2]) or '약점 근거 부족'}",
            f"{catl_analysis.company}: {', '.join(catl_analysis.risks[:2]) or '약점 근거 부족'}",
        ]
    if not opportunities:
        opportunities = ["ESS 확대와 지역별 공급망 재편은 양사 공통의 성장 기회다."]
    if not threats:
        threats = ["시장 수요 둔화와 가격 경쟁 심화는 양사 공통의 위협이다."]

    return SWOTSection(
        strengths=strengths,
        weaknesses=weaknesses,
        opportunities=opportunities,
        threats=threats,
    )


def _build_company_metrics(
    payload: dict[str, object],
    lg_analysis: CompanyAnalysisResult,
    catl_analysis: CompanyAnalysisResult,
) -> list[CompanyMetric]:
    metrics: list[CompanyMetric] = []
    for item in payload.get("company_metrics", []):
        if not isinstance(item, dict):
            continue
        company = str(item.get("company", "")).strip()
        metric = str(item.get("metric", "")).strip()
        value = str(item.get("value", "")).strip()
        source_hint = str(item.get("source_hint", "")).strip()
        if company and metric and value:
            metrics.append(
                CompanyMetric(
                    company=company,
                    metric=metric,
                    value=value,
                    source_hint=source_hint,
                )
            )

    if metrics:
        return metrics

    derived_metrics: list[CompanyMetric] = []
    for analysis in (lg_analysis, catl_analysis):
        for metric in analysis.metrics:
            derived_metrics.append(
                CompanyMetric(
                    company=analysis.company,
                    metric=metric.metric,
                    value=metric.value,
                    source_hint=metric.source_hint,
                )
            )
    return derived_metrics
