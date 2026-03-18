"""Distributed workflow orchestrator."""

from __future__ import annotations

from pathlib import Path

from battery_agent.agents.catl_analysis import run_catl_analysis
from battery_agent.agents.catl_curation import run_catl_curation
from battery_agent.agents.catl_retrieval import run_catl_retrieval
from battery_agent.agents.comparison import run_comparison
from battery_agent.agents.lg_analysis import run_lg_analysis
from battery_agent.agents.lg_curation import run_lg_curation
from battery_agent.agents.lg_retrieval import run_lg_retrieval
from battery_agent.agents.references import build_references
from battery_agent.agents.report_generation import build_report
from battery_agent.config import Settings
from battery_agent.llm.openai_structured import StructuredOpenAIClient
from battery_agent.logging_utils import build_run_logger
from battery_agent.models.run_context import RunContext
from battery_agent.models.report import ReportArtifact
from battery_agent.rag.chroma_store import ChromaVectorStore
from battery_agent.rag.chunker import chunk_documents, write_chunk_artifact
from battery_agent.rag.corpus_loader import load_corpus
from battery_agent.rag.embedder import HashingEmbedder
from battery_agent.rag.qwen_embedder import QwenEmbeddingClient
from battery_agent.rag.vector_index import (
    InMemoryVectorIndex,
    VectorRecord,
    compute_corpus_fingerprint,
    should_rebuild_index,
    write_index_metadata,
)
from battery_agent.reporting.pdf_renderer import render_pdf_report
from battery_agent.storage.json_store import write_json
from battery_agent.storage.paths import artifact_path_for, build_run_paths, ensure_run_directories
from battery_agent.search.chroma_retriever import ChromaRetriever
from battery_agent.search.local_retriever import LocalRetriever
from battery_agent.search.web_search import build_tavily_web_searcher
from battery_agent.pipeline.handoffs import final_workflow_status
from battery_agent.pipeline.workflow_state import LaneState, WorkflowState

MAX_EVIDENCE_RETRY = 1
MAX_REFINEMENT_RETRY = 1
REFINEMENT_RETRY_QUALITY_THRESHOLD = 2.5
MIN_ACCEPTABLE_EVIDENCE_ENTRIES = 2


def run_analysis_workflow(
    settings: Settings,
    topic: str,
    run_id: str,
    llm_client: StructuredOpenAIClient | object | None = None,
) -> WorkflowState:
    run_paths = build_run_paths(settings.output_root, run_id)
    ensure_run_directories(run_paths)
    logger = build_run_logger("battery-agent.workflow", artifact_path_for(run_paths, "logs", "run"))

    run_context = RunContext(run_id=run_id, topic=topic, output_dir=str(run_paths.root))
    corpus_fingerprint = compute_corpus_fingerprint(settings.local_corpus_dir)
    workflow_state = WorkflowState(
        run_context=run_context,
        model_name=settings.default_model,
        corpus_fingerprint=corpus_fingerprint,
        search_params={
            "web_search": settings.web_search_enabled,
            "web_search_max_calls": settings.web_search_max_calls,
            "web_search_max_results": settings.web_search_max_results,
            "web_search_max_per_source": settings.web_search_max_per_source,
        },
        lg_lane=LaneState(company="LG에너지솔루션"),
        catl_lane=LaneState(company="CATL"),
    )

    local_retriever = build_local_retriever(settings=settings, run_root=run_paths.root, logger=logger)
    structured_llm = llm_client or StructuredOpenAIClient(api_key=settings.openai_api_key)

    run_lane_pipeline(
        lane=workflow_state.lg_lane,
        topic=topic,
        settings=settings,
        run_paths=run_paths,
        local_retriever=local_retriever,
        structured_llm=structured_llm,
        retrieval_runner=run_lg_retrieval,
        curation_runner=run_lg_curation,
        analysis_runner=run_lg_analysis,
        retrieval_key="lg_retrieval",
        evidence_key="lg_curation",
        analysis_key="lg_analysis",
        logger=logger,
        allow_evidence_retry=True,
    )
    run_lane_pipeline(
        lane=workflow_state.catl_lane,
        topic=topic,
        settings=settings,
        run_paths=run_paths,
        local_retriever=local_retriever,
        structured_llm=structured_llm,
        retrieval_runner=run_catl_retrieval,
        curation_runner=run_catl_curation,
        analysis_runner=run_catl_analysis,
        retrieval_key="catl_retrieval",
        evidence_key="catl_curation",
        analysis_key="catl_analysis",
        logger=logger,
        allow_evidence_retry=True,
    )

    workflow_state.comparison_result = run_comparison(
        workflow_state.lg_lane.analysis_result,
        workflow_state.catl_lane.analysis_result,
        llm_client=structured_llm,
        model=settings.default_model,
        artifact_path=artifact_path_for(run_paths, "analysis", "comparison"),
    )
    reran_for_refinement = False
    if workflow_state.comparison_result.next_action == "analysis_refinement":
        reran_for_refinement = maybe_run_refinement_retries(
            state=workflow_state,
            settings=settings,
            topic=topic,
            run_paths=run_paths,
            local_retriever=local_retriever,
            structured_llm=structured_llm,
            logger=logger,
        )
        if reran_for_refinement:
            workflow_state.comparison_result = run_comparison(
                workflow_state.lg_lane.analysis_result,
                workflow_state.catl_lane.analysis_result,
                llm_client=structured_llm,
                model=settings.default_model,
                artifact_path=artifact_path_for(run_paths, "analysis", "comparison"),
            )
    workflow_state.reference_result = build_references(
        evidence_bundles=[workflow_state.lg_lane.evidence_bundle, workflow_state.catl_lane.evidence_bundle],
        analyses=[workflow_state.lg_lane.analysis_result, workflow_state.catl_lane.analysis_result],
        comparison=workflow_state.comparison_result,
        artifact_path=artifact_path_for(run_paths, "reports", "references"),
    )
    report_markdown_path = artifact_path_for(run_paths, "reports", "final_report", suffix="md")
    report_pdf_path = artifact_path_for(run_paths, "reports", "final_report", suffix="pdf")
    generated = build_report(
        topic=topic,
        lg_analysis=workflow_state.lg_lane.analysis_result,
        catl_analysis=workflow_state.catl_lane.analysis_result,
        comparison=workflow_state.comparison_result,
        references=workflow_state.reference_result,
        llm_client=structured_llm,
        model=settings.default_model,
        markdown_path=report_markdown_path,
    )
    pdf_result = render_pdf_report(report_markdown_path, report_pdf_path)
    workflow_state.report_artifact = ReportArtifact(
        title="Battery Market Strategy Analysis",
        markdown_path=str(report_markdown_path),
        pdf_path=str(report_pdf_path),
        partial=generated.partial or not pdf_result.success,
    )
    workflow_state.status = final_workflow_status(
        has_report=True,
        partial=workflow_state.report_artifact.partial,
    )
    write_json(artifact_path_for(run_paths, "metadata", "workflow_state"), _workflow_state_dict(workflow_state))
    logger.info("workflow completed status=%s", workflow_state.status)
    return workflow_state


def build_company_web_searchers(settings: Settings) -> tuple[object | None, object | None]:
    if not settings.web_search_enabled or not settings.tavily_api_key:
        return None, None

    lg_searcher = build_company_web_searcher(settings, "LG에너지솔루션")
    catl_searcher = build_company_web_searcher(settings, "CATL")
    return lg_searcher, catl_searcher


def build_company_web_searcher(settings: Settings, company: str) -> object | None:
    if not settings.web_search_enabled or not settings.tavily_api_key:
        return None
    lg_calls, catl_calls = allocate_web_search_calls(settings.web_search_max_calls)
    max_calls = lg_calls if company == "LG에너지솔루션" else catl_calls
    return build_tavily_web_searcher(
        api_key=settings.tavily_api_key,
        max_results=settings.web_search_max_results,
        max_per_source=settings.web_search_max_per_source,
        max_calls=max_calls,
    )


def allocate_web_search_calls(total_calls: int) -> tuple[int, int]:
    if total_calls <= 0:
        return 1, 1
    lg_calls = max(1, total_calls // 2)
    catl_calls = max(1, total_calls - lg_calls)
    return lg_calls, catl_calls


def lane_quality_score(
    analysis_result: object | None,
    evidence_bundle: object | None,
    retrieval_result: object | None,
) -> float:
    if analysis_result is None or evidence_bundle is None or retrieval_result is None:
        return 0.0

    score = 0.0
    citations = len(getattr(analysis_result, "citations", []))
    metrics = len(getattr(analysis_result, "metrics", []))
    topics = set(getattr(evidence_bundle, "topics", []))
    entries = len(getattr(evidence_bundle, "entries", []))
    used_web = bool(getattr(retrieval_result, "used_web_search", False))
    text_fragments = (
        list(getattr(analysis_result, "strengths", []))
        + list(getattr(analysis_result, "risks", []))
        + [str(getattr(analysis_result, "strategy_summary", ""))]
    )

    score += min(1.5, citations * 0.5)
    score += min(1.0, metrics * 0.5)
    score += 1.0 if "strategy" in topics else 0.0
    score += 0.6 if "risk" in topics else 0.0
    score += 0.5 if entries >= 6 else (0.2 if entries >= 2 else 0.0)
    score += 0.2 if used_web else 0.0

    if any("근거 부족" in fragment for fragment in text_fragments):
        score -= 0.8
    return score


def should_retry_refinement(quality_score: float, retries: int, max_retries: int) -> bool:
    return retries < max_retries and quality_score < REFINEMENT_RETRY_QUALITY_THRESHOLD


def should_retry_evidence(
    evidence_bundle: object | None,
    retrieval_result: object | None,
    retries: int,
    max_retries: int,
) -> bool:
    if retries >= max_retries or evidence_bundle is None or retrieval_result is None:
        return False
    entries = len(getattr(evidence_bundle, "entries", []))
    topics = set(getattr(evidence_bundle, "topics", []))
    missing_topics = set(getattr(evidence_bundle, "missing_topics", []))
    if entries < MIN_ACCEPTABLE_EVIDENCE_ENTRIES:
        return True
    if "strategy" not in topics:
        return True
    return "strategy" in missing_topics and entries < 4


def run_lane_pipeline(
    *,
    lane: LaneState,
    topic: str,
    settings: Settings,
    run_paths: object,
    local_retriever: object,
    structured_llm: object,
    retrieval_runner: object,
    curation_runner: object,
    analysis_runner: object,
    retrieval_key: str,
    evidence_key: str,
    analysis_key: str,
    logger: object | None,
    allow_evidence_retry: bool,
) -> None:
    evidence_retries = lane.retries.get("evidence", 0)
    while True:
        web_searcher = build_company_web_searcher(settings, lane.company)
        lane.retrieval_result = retrieval_runner(
            topic=topic,
            local_retriever=local_retriever,
            web_searcher=web_searcher,
            artifact_path=artifact_path_for(run_paths, "retrieval", retrieval_key),
        )
        lane.evidence_bundle = curation_runner(
            lane.retrieval_result,
            artifact_path=artifact_path_for(run_paths, "evidence", evidence_key),
        )
        lane.analysis_result = analysis_runner(
            lane.evidence_bundle,
            llm_client=structured_llm,
            model=settings.default_model,
            artifact_path=artifact_path_for(run_paths, "analysis", analysis_key),
        )
        lane.used_sources = list(lane.analysis_result.citations)
        lane.partial = lane.analysis_result.partial
        lane.status = "completed"
        if not allow_evidence_retry:
            break
        if not should_retry_evidence(
            lane.evidence_bundle,
            lane.retrieval_result,
            retries=evidence_retries,
            max_retries=MAX_EVIDENCE_RETRY,
        ):
            break
        evidence_retries += 1
        lane.retries["evidence"] = evidence_retries
        lane.last_action = "retry_evidence"
        if logger is not None:
            logger.info("retry evidence lane=%s attempt=%s", lane.company, evidence_retries)
    lane.retries["evidence"] = evidence_retries


def maybe_run_refinement_retries(
    *,
    state: WorkflowState,
    settings: Settings,
    topic: str,
    run_paths: object,
    local_retriever: object,
    structured_llm: object,
    logger: object | None,
) -> bool:
    requested = set(state.comparison_result.refinement_requests)
    reran = False
    lane_specs = [
        (
            state.lg_lane,
            run_lg_retrieval,
            run_lg_curation,
            run_lg_analysis,
            "lg_retrieval",
            "lg_curation",
            "lg_analysis",
        ),
        (
            state.catl_lane,
            run_catl_retrieval,
            run_catl_curation,
            run_catl_analysis,
            "catl_retrieval",
            "catl_curation",
            "catl_analysis",
        ),
    ]
    for lane, retrieval_runner, curation_runner, analysis_runner, retrieval_key, evidence_key, analysis_key in lane_specs:
        if lane.company not in requested:
            continue
        quality = lane_quality_score(lane.analysis_result, lane.evidence_bundle, lane.retrieval_result)
        retries = lane.retries.get("refinement", 0)
        if not should_retry_refinement(
            quality_score=quality,
            retries=retries,
            max_retries=MAX_REFINEMENT_RETRY,
        ):
            continue
        lane.retries["refinement"] = retries + 1
        lane.last_action = "retry_refinement"
        if logger is not None:
            logger.info(
                "retry refinement lane=%s attempt=%s quality=%.2f",
                lane.company,
                lane.retries["refinement"],
                quality,
            )
        run_lane_pipeline(
            lane=lane,
            topic=topic,
            settings=settings,
            run_paths=run_paths,
            local_retriever=local_retriever,
            structured_llm=structured_llm,
            retrieval_runner=retrieval_runner,
            curation_runner=curation_runner,
            analysis_runner=analysis_runner,
            retrieval_key=retrieval_key,
            evidence_key=evidence_key,
            analysis_key=analysis_key,
            logger=logger,
            allow_evidence_retry=False,
        )
        reran = True
    return reran


def build_local_retriever(
    settings: Settings,
    run_root: Path,
    logger: object | None,
) -> object:
    if _is_pdf_corpus_layout(settings.local_corpus_dir):
        chroma_retriever = open_chroma_retriever(settings=settings, logger=logger)
        if chroma_retriever is not None:
            return chroma_retriever
    return _build_in_memory_retriever(settings=settings, run_root=run_root, logger=logger)


def open_chroma_retriever(
    settings: Settings,
    logger: object | None,
) -> ChromaRetriever | None:
    try:
        store = ChromaVectorStore.open(
            chroma_dir=settings.chroma_dir,
            collection_name=settings.chroma_collection,
        )
    except RuntimeError:
        return None

    if not store.has_records():
        return None

    embedder = QwenEmbeddingClient(
        model_id=settings.embedding_model_id,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
    )
    return ChromaRetriever(
        store=store,
        embed_query=lambda query: embedder.embed_queries([query])[0],
        logger=logger,
    )


def _build_in_memory_retriever(
    settings: Settings,
    run_root: Path,
    logger: object | None,
) -> LocalRetriever:
    documents = load_corpus(settings.local_corpus_dir)
    chunks = chunk_documents(documents)
    metadata_dir = run_root / "metadata"
    write_chunk_artifact(metadata_dir / "chunks.json", chunks)

    embedder = HashingEmbedder(cache_dir=metadata_dir / "embedding_cache")
    index_path = metadata_dir / "vector_index.json"
    metadata_path = metadata_dir / "vector_index_meta.json"
    corpus_fingerprint = compute_corpus_fingerprint(settings.local_corpus_dir)
    if should_rebuild_index(index_path, metadata_path, corpus_fingerprint):
        index = InMemoryVectorIndex()
        embeddings = embedder.embed([chunk.text for chunk in chunks])
        records = [
            VectorRecord(
                record_id=chunk.chunk_id,
                document_id=chunk.document_id,
                text=chunk.text,
                embedding=embedding,
                metadata={
                    "company": chunk.company,
                    "topics": chunk.topics,
                    "source_type": chunk.source_type,
                    "source": chunk.source,
                    "title": chunk.title,
                    "url": chunk.url,
                },
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]
        index.add(records)
        index.dump(index_path)
        write_index_metadata(metadata_path, corpus_fingerprint)
    else:
        index = InMemoryVectorIndex.load(index_path)

    return LocalRetriever(
        index=index,
        embed_query=lambda query: embedder.embed([query])[0],
        logger=logger,
    )


def _is_pdf_corpus_layout(corpus_dir: Path) -> bool:
    if not corpus_dir.exists():
        return False
    return any(company_dir.glob("*.pdf") for company_dir in corpus_dir.iterdir() if company_dir.is_dir())


def _workflow_state_dict(state: WorkflowState) -> dict[str, object]:
    return {
        "run_context": state.run_context.to_dict(),
        "model_name": state.model_name,
        "corpus_fingerprint": state.corpus_fingerprint,
        "search_params": state.search_params,
        "lg_lane": {
            "company": state.lg_lane.company,
            "status": state.lg_lane.status,
            "used_sources": state.lg_lane.used_sources,
            "partial": state.lg_lane.partial,
            "retries": state.lg_lane.retries,
            "last_action": state.lg_lane.last_action,
        },
        "catl_lane": {
            "company": state.catl_lane.company,
            "status": state.catl_lane.status,
            "used_sources": state.catl_lane.used_sources,
            "partial": state.catl_lane.partial,
            "retries": state.catl_lane.retries,
            "last_action": state.catl_lane.last_action,
        },
        "status": state.status,
    }
