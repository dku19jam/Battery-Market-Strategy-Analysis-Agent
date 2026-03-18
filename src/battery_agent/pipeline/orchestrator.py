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
        },
        lg_lane=LaneState(company="LG에너지솔루션"),
        catl_lane=LaneState(company="CATL"),
    )

    local_retriever = build_local_retriever(settings=settings, run_root=run_paths.root, logger=logger)
    web_searcher = None
    if settings.web_search_enabled and settings.tavily_api_key:
        web_searcher = build_tavily_web_searcher(
            api_key=settings.tavily_api_key,
            max_results=settings.web_search_max_results,
            max_calls=settings.web_search_max_calls,
        )
    structured_llm = llm_client or StructuredOpenAIClient(api_key=settings.openai_api_key)

    workflow_state.lg_lane.retrieval_result = run_lg_retrieval(
        topic=topic,
        local_retriever=local_retriever,
        web_searcher=web_searcher,
        artifact_path=artifact_path_for(run_paths, "retrieval", "lg_retrieval"),
    )
    workflow_state.lg_lane.evidence_bundle = run_lg_curation(
        workflow_state.lg_lane.retrieval_result,
        artifact_path=artifact_path_for(run_paths, "evidence", "lg_curation"),
    )
    workflow_state.lg_lane.analysis_result = run_lg_analysis(
        workflow_state.lg_lane.evidence_bundle,
        llm_client=structured_llm,
        model=settings.default_model,
        artifact_path=artifact_path_for(run_paths, "analysis", "lg_analysis"),
    )
    workflow_state.lg_lane.used_sources = list(workflow_state.lg_lane.analysis_result.citations)
    workflow_state.lg_lane.partial = workflow_state.lg_lane.analysis_result.partial
    workflow_state.lg_lane.status = "completed"

    workflow_state.catl_lane.retrieval_result = run_catl_retrieval(
        topic=topic,
        local_retriever=local_retriever,
        web_searcher=web_searcher,
        artifact_path=artifact_path_for(run_paths, "retrieval", "catl_retrieval"),
    )
    workflow_state.catl_lane.evidence_bundle = run_catl_curation(
        workflow_state.catl_lane.retrieval_result,
        artifact_path=artifact_path_for(run_paths, "evidence", "catl_curation"),
    )
    workflow_state.catl_lane.analysis_result = run_catl_analysis(
        workflow_state.catl_lane.evidence_bundle,
        llm_client=structured_llm,
        model=settings.default_model,
        artifact_path=artifact_path_for(run_paths, "analysis", "catl_analysis"),
    )
    workflow_state.catl_lane.used_sources = list(workflow_state.catl_lane.analysis_result.citations)
    workflow_state.catl_lane.partial = workflow_state.catl_lane.analysis_result.partial
    workflow_state.catl_lane.status = "completed"

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
    generated = build_report(
        topic=topic,
        lg_analysis=workflow_state.lg_lane.analysis_result,
        catl_analysis=workflow_state.catl_lane.analysis_result,
        comparison=workflow_state.comparison_result,
        references=workflow_state.reference_result,
        llm_client=structured_llm,
        model=settings.default_model,
        markdown_path=artifact_path_for(run_paths, "reports", "final_report", suffix="md"),
    )
    pdf_result = render_pdf_report(
        generated.markdown,
        artifact_path_for(run_paths, "reports", "final_report", suffix="pdf"),
    )
    workflow_state.report_artifact = ReportArtifact(
        title="Battery Market Strategy Analysis",
        markdown_path=str(artifact_path_for(run_paths, "reports", "final_report", suffix="md")),
        pdf_path=str(artifact_path_for(run_paths, "reports", "final_report", suffix="pdf")),
        partial=generated.partial or not pdf_result.success,
    )
    workflow_state.status = final_workflow_status(
        has_report=True,
        partial=workflow_state.report_artifact.partial,
    )
    write_json(artifact_path_for(run_paths, "metadata", "workflow_state"), _workflow_state_dict(workflow_state))
    logger.info("workflow completed status=%s", workflow_state.status)
    return workflow_state


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
                metadata={"company": chunk.company, "topics": chunk.topics},
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
        },
        "catl_lane": {
            "company": state.catl_lane.company,
            "status": state.catl_lane.status,
            "used_sources": state.catl_lane.used_sources,
            "partial": state.catl_lane.partial,
        },
        "status": state.status,
    }
