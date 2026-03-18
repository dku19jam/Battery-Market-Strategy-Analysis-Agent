# Battery Market Strategy Analysis Agent Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** LG에너지솔루션과 CATL의 포트폴리오 다각화 전략을 비교 분석하고, 한국어 Markdown/PDF 보고서를 자동 생성하는 CLI 서비스를 구현한다.

**Architecture:** 중앙 `Supervisor Agent` 없이 LG와 CATL의 수집-근거정리-분석 라인이 독립된 distributed lane으로 동작하고, 각 agent가 자신의 범위 안에서 `재시도`, `도구 사용`, `보완 요청`, `다음 단계 handoff`를 결정한다. 로컬 코퍼스 기반 RAG를 우선 사용하고 부족한 경우에만 제한적 웹 검색과 재시도 정책을 적용한다.

**Tech Stack:** Python CLI, OpenAI `gpt-4o-mini`, 오픈소스 임베딩 모델, 로컬 벡터 인덱스, Markdown to PDF 변환 도구, JSON/Markdown 아티팩트 저장

---

## Proposed File Structure

- Create: `README.md`
- Create: `pyproject.toml`
- Create: `src/battery_agent/__init__.py`
- Create: `src/battery_agent/cli.py`
- Create: `src/battery_agent/config.py`
- Create: `src/battery_agent/logging_utils.py`
- Create: `src/battery_agent/models/run_context.py`
- Create: `src/battery_agent/models/retrieval.py`
- Create: `src/battery_agent/models/evidence.py`
- Create: `src/battery_agent/models/analysis.py`
- Create: `src/battery_agent/models/report.py`
- Create: `src/battery_agent/pipeline/workflow_state.py`
- Create: `src/battery_agent/pipeline/handoffs.py`
- Create: `src/battery_agent/prompts/`
- Create: `src/battery_agent/storage/paths.py`
- Create: `src/battery_agent/storage/json_store.py`
- Create: `src/battery_agent/rag/corpus_loader.py`
- Create: `src/battery_agent/rag/chunker.py`
- Create: `src/battery_agent/rag/embedder.py`
- Create: `src/battery_agent/rag/vector_index.py`
- Create: `src/battery_agent/search/query_builder.py`
- Create: `src/battery_agent/search/local_retriever.py`
- Create: `src/battery_agent/search/web_search.py`
- Create: `src/battery_agent/agents/lg_retrieval.py`
- Create: `src/battery_agent/agents/lg_curation.py`
- Create: `src/battery_agent/agents/lg_analysis.py`
- Create: `src/battery_agent/agents/catl_retrieval.py`
- Create: `src/battery_agent/agents/catl_curation.py`
- Create: `src/battery_agent/agents/catl_analysis.py`
- Create: `src/battery_agent/agents/comparison.py`
- Create: `src/battery_agent/agents/references.py`
- Create: `src/battery_agent/agents/report_generation.py`
- Create: `src/battery_agent/reporting/markdown_renderer.py`
- Create: `src/battery_agent/reporting/pdf_renderer.py`
- Create: `src/battery_agent/pipeline/retry_policy.py`
- Create: `src/battery_agent/pipeline/orchestrator.py`
- Create: `tests/`
- Create: `output/` or `artifacts/` runtime directory structure

## Task Breakdown

### Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/battery_agent/__init__.py`
- Create: `src/battery_agent/cli.py`
- Create: `README.md`

- [ ] 프로젝트 이름, Python 버전, 의존성 후보를 확정한다.
- [ ] 패키지 기본 디렉터리를 생성한다.
- [ ] CLI 엔트리포인트를 등록한다.
- [ ] 기본 실행 명령 예시를 README 초안에 적는다.

### Task 2: Runtime Config

**Files:**
- Create: `src/battery_agent/config.py`
- Modify: `README.md`

- [ ] 환경변수 목록을 정의한다.
- [ ] 기본 비교 대상 기업을 상수로 고정한다.
- [ ] 기본 모델을 `gpt-4o-mini`로 설정한다.
- [ ] 설정 로딩 실패 시 에러 메시지 규칙을 정한다.

### Task 3: Artifact Directory Policy

**Files:**
- Create: `src/battery_agent/storage/paths.py`
- Create: `src/battery_agent/storage/json_store.py`

- [ ] 실행별 output 디렉터리 구조를 설계한다.
- [ ] 중간 산출물 파일명 규칙을 정의한다.
- [ ] JSON 저장 유틸을 구현한다.
- [ ] Markdown 저장 유틸을 구현한다.

### Task 4: Logging and Traceability

**Files:**
- Create: `src/battery_agent/logging_utils.py`
- Modify: `src/battery_agent/cli.py`

- [ ] 콘솔 로그 포맷을 정의한다.
- [ ] 파일 로그 포맷을 정의한다.
- [ ] 재시도 로그 전용 기록 함수를 추가한다.
- [ ] 실행 시작/종료 로그를 남기도록 CLI에 연결한다.

### Task 5: Domain Models

**Files:**
- Create: `src/battery_agent/models/run_context.py`
- Create: `src/battery_agent/models/retrieval.py`
- Create: `src/battery_agent/models/evidence.py`
- Create: `src/battery_agent/models/analysis.py`
- Create: `src/battery_agent/models/report.py`

- [ ] 실행 컨텍스트 모델을 정의한다.
- [ ] 검색 결과 모델을 정의한다.
- [ ] 근거 묶음 모델을 정의한다.
- [ ] 기업 분석 결과 모델을 정의한다.
- [ ] 비교 분석/보고서/참고문헌 모델을 정의한다.

### Task 6: Prompt Assets

**Files:**
- Create: `src/battery_agent/prompts/`

- [ ] workflow coordination 프롬프트 초안을 작성한다.
- [ ] Retrieval 프롬프트 템플릿을 작성한다.
- [ ] Evidence curation 프롬프트 템플릿을 작성한다.
- [ ] Company analysis 프롬프트 템플릿을 작성한다.
- [ ] Comparison/SWOT 프롬프트 템플릿을 작성한다.
- [ ] Report/reference generation 프롬프트 템플릿을 작성한다.

### Task 7: Corpus Input Contract

**Files:**
- Create: `src/battery_agent/rag/corpus_loader.py`
- Modify: `README.md`

- [ ] 로컬 코퍼스 입력 디렉터리 규칙을 정의한다.
- [ ] 지원 문서 포맷을 결정한다.
- [ ] 문서 메타데이터 스키마를 정의한다.
- [ ] 코퍼스 로딩 실패 정책을 문서화한다.

### Task 8: Chunking

**Files:**
- Create: `src/battery_agent/rag/chunker.py`

- [ ] 문서 chunk 단위를 정의한다.
- [ ] 페이지 수 제한 계산 규칙을 정의한다.
- [ ] chunk에 문서 ID와 페이지 정보를 부여한다.
- [ ] chunk 결과를 아티팩트로 저장하도록 연결한다.

### Task 9: Embedding Layer

**Files:**
- Create: `src/battery_agent/rag/embedder.py`

- [ ] 사용할 오픈소스 임베딩 모델을 결정한다.
- [ ] 임베딩 생성 인터페이스를 정의한다.
- [ ] 배치 임베딩 함수 시그니처를 정의한다.
- [ ] 임베딩 캐시 정책을 정한다.

### Task 10: Vector Index

**Files:**
- Create: `src/battery_agent/rag/vector_index.py`

- [ ] 벡터 저장소 구현체를 선택한다.
- [ ] 인덱스 생성 함수를 구현한다.
- [ ] 인덱스 로드 함수를 구현한다.
- [ ] 코퍼스 변경 시 재생성 기준을 정의한다.

### Task 11: Query Builder

**Files:**
- Create: `src/battery_agent/search/query_builder.py`

- [ ] LG 전용 검색 질의 템플릿을 만든다.
- [ ] CATL 전용 검색 질의 템플릿을 만든다.
- [ ] 전략 키워드 템플릿을 만든다.
- [ ] 시장 변화 키워드 템플릿을 만든다.
- [ ] 재시도용 질의 재작성 규칙을 만든다.

### Task 12: Local Retriever

**Files:**
- Create: `src/battery_agent/search/local_retriever.py`

- [ ] 기업명 필터 검색을 구현한다.
- [ ] 전략 키워드 검색을 구현한다.
- [ ] 검색 결과 점수 정렬을 구현한다.
- [ ] 검색 결과를 로그와 파일로 저장한다.

### Task 13: Limited Web Search

**Files:**
- Create: `src/battery_agent/search/web_search.py`
- Modify: `src/battery_agent/config.py`

- [ ] 웹 검색 사용 여부 플래그를 추가한다.
- [ ] 웹 검색 최대 횟수 제한을 추가한다.
- [ ] 웹 검색 결과 저장 포맷을 정의한다.
- [ ] 편향 완화 체크 규칙을 구현한다.

### Task 14: LG Retrieval Agent

**Files:**
- Create: `src/battery_agent/agents/lg_retrieval.py`

- [ ] LG용 질의를 생성한다.
- [ ] 로컬 코퍼스 검색을 실행한다.
- [ ] 근거 부족 여부를 판정한다.
- [ ] 필요한 경우 웹 검색을 보완 실행한다.
- [ ] LG 검색 결과를 전용 아티팩트로 저장한다.

### Task 15: CATL Retrieval Agent

**Files:**
- Create: `src/battery_agent/agents/catl_retrieval.py`

- [ ] CATL용 질의를 생성한다.
- [ ] 로컬 코퍼스 검색을 실행한다.
- [ ] 근거 부족 여부를 판정한다.
- [ ] 필요한 경우 웹 검색을 보완 실행한다.
- [ ] CATL 검색 결과를 전용 아티팩트로 저장한다.

### Task 16: LG Evidence Curation Agent

**Files:**
- Create: `src/battery_agent/agents/lg_curation.py`

- [ ] LG 검색 결과를 주제별로 분류한다.
- [ ] 중복 근거 제거 규칙을 구현한다.
- [ ] 신뢰도 우선순위 규칙을 구현한다.
- [ ] LG 분석용 근거 묶음을 생성한다.
- [ ] 근거 부족 항목을 표시한다.

### Task 17: CATL Evidence Curation Agent

**Files:**
- Create: `src/battery_agent/agents/catl_curation.py`

- [ ] CATL 검색 결과를 주제별로 분류한다.
- [ ] 중복 근거 제거 규칙을 구현한다.
- [ ] 신뢰도 우선순위 규칙을 구현한다.
- [ ] CATL 분석용 근거 묶음을 생성한다.
- [ ] 근거 부족 항목을 표시한다.

### Task 18: LG Analysis Agent

**Files:**
- Create: `src/battery_agent/agents/lg_analysis.py`

- [ ] LG 포트폴리오 다각화 전략 요약을 생성한다.
- [ ] LG 핵심 경쟁력 항목을 생성한다.
- [ ] LG 리스크 항목을 생성한다.
- [ ] 근거 인용 연결 정보를 유지한다.
- [ ] LG 분석 메모를 저장한다.

### Task 19: CATL Analysis Agent

**Files:**
- Create: `src/battery_agent/agents/catl_analysis.py`

- [ ] CATL 포트폴리오 다각화 전략 요약을 생성한다.
- [ ] CATL 핵심 경쟁력 항목을 생성한다.
- [ ] CATL 리스크 항목을 생성한다.
- [ ] 근거 인용 연결 정보를 유지한다.
- [ ] CATL 분석 메모를 저장한다.

### Task 20: Comparison Evaluation Agent

**Files:**
- Create: `src/battery_agent/agents/comparison.py`

- [ ] 두 기업 분석 결과를 공통 스키마로 정렬한다.
- [ ] 전략 차이점 비교 결과를 생성한다.
- [ ] 강점/약점 비교 결과를 생성한다.
- [ ] SWOT 초안을 생성한다.
- [ ] 종합 시사점을 생성한다.
- [ ] 특정 기업 분석이 약할 때 refinement 요청을 반환하는 규칙을 정의한다.
- [ ] comparison 결과의 next handoff를 `Reference Agent`로 연결한다.

### Task 21: Reference Agent

**Files:**
- Create: `src/battery_agent/agents/references.py`

- [ ] 실제 사용 근거만 추출하는 규칙을 구현한다.
- [ ] 자료 유형 판별 규칙을 구현한다.
- [ ] 기관 보고서 포맷터를 구현한다.
- [ ] 학술 논문 포맷터를 구현한다.
- [ ] 웹페이지 포맷터를 구현한다.
- [ ] reference 결과의 next handoff를 `Report Generation Agent`로 연결한다.

### Task 22: Report Outline Contract

**Files:**
- Create: `src/battery_agent/reporting/markdown_renderer.py`

- [ ] 필수 섹션 목록을 상수로 정의한다.
- [ ] `SUMMARY`를 첫 섹션으로 고정한다.
- [ ] `REFERENCE`를 마지막 섹션으로 고정한다.
- [ ] SUMMARY 길이 제한 규칙을 반영한다.

### Task 23: Report Generation Agent

**Files:**
- Create: `src/battery_agent/agents/report_generation.py`
- Modify: `src/battery_agent/reporting/markdown_renderer.py`

- [ ] 시장 배경 섹션을 생성한다.
- [ ] LG 전략 섹션을 생성한다.
- [ ] CATL 전략 섹션을 생성한다.
- [ ] 핵심 전략 비교 섹션을 생성한다.
- [ ] SWOT 섹션을 생성한다.
- [ ] 종합 시사점 섹션을 생성한다.
- [ ] 참고문헌 섹션을 조립한다.
- [ ] 정보 부족 시 부분 보고서로 종료하는 handoff 규칙을 정의한다.

### Task 24: Markdown Renderer

**Files:**
- Modify: `src/battery_agent/reporting/markdown_renderer.py`

- [ ] 보고서 템플릿을 Markdown 문자열로 구현한다.
- [ ] 섹션별 헤더 규칙을 고정한다.
- [ ] 인용/출처 표기 형식을 고정한다.
- [ ] 최종 Markdown 파일 저장을 연결한다.

### Task 25: PDF Renderer

**Files:**
- Create: `src/battery_agent/reporting/pdf_renderer.py`

- [ ] Markdown to PDF 변환 도구를 선택한다.
- [ ] PDF 변환 함수 인터페이스를 구현한다.
- [ ] 폰트/한글 렌더링 확인 로직을 추가한다.
- [ ] PDF 생성 실패 시 로그와 fallback 메시지를 남긴다.

### Task 26: Retry Policy

**Files:**
- Create: `src/battery_agent/pipeline/retry_policy.py`

- [ ] 단계별 최대 재시도 횟수를 정의한다.
- [ ] 로컬 재검색 재시도 규칙을 구현한다.
- [ ] 질의 재작성 재시도 규칙을 구현한다.
- [ ] 웹 검색 보완 재시도 규칙을 구현한다.
- [ ] 부분 보고서 전환 조건을 구현한다.

### Task 27: Workflow State and Handoff Contracts

**Files:**
- Create: `src/battery_agent/pipeline/workflow_state.py`
- Create: `src/battery_agent/pipeline/handoffs.py`

- [ ] shared workflow state 모델을 정의한다.
- [ ] LG lane state와 CATL lane state를 정의한다.
- [ ] agent별 handoff 결과 스키마를 정의한다.
- [ ] comparison/reference/report 진입 조건을 정의한다.
- [ ] 전체 성공/부분 성공/실패 판정 규칙을 정의한다.
- [ ] 다음 단계 선택 규칙을 handoff 모듈에 연결한다.

### Task 28: LG Lane Transition Rules

**Files:**
- Modify: `src/battery_agent/agents/lg_retrieval.py`
- Modify: `src/battery_agent/agents/lg_curation.py`
- Modify: `src/battery_agent/agents/lg_analysis.py`

- [ ] LG retrieval의 local retry와 next handoff 규칙을 정의한다.
- [ ] LG curation의 보완 요청과 next handoff 규칙을 정의한다.
- [ ] LG analysis의 보완 요청과 lane 완료 규칙을 정의한다.
- [ ] LG 재시도와 부분 분석 판정 규칙을 정의한다.
- [ ] LG used_sources 기록 규칙을 정의한다.

### Task 29: CATL Lane Transition Rules

**Files:**
- Modify: `src/battery_agent/agents/catl_retrieval.py`
- Modify: `src/battery_agent/agents/catl_curation.py`
- Modify: `src/battery_agent/agents/catl_analysis.py`

- [ ] CATL retrieval의 local retry와 next handoff 규칙을 정의한다.
- [ ] CATL curation의 보완 요청과 next handoff 규칙을 정의한다.
- [ ] CATL analysis의 보완 요청과 lane 완료 규칙을 정의한다.
- [ ] CATL 재시도와 부분 분석 판정 규칙을 정의한다.
- [ ] CATL used_sources 기록 규칙을 정의한다.

### Task 30: Orchestrator

**Files:**
- Create: `src/battery_agent/pipeline/orchestrator.py`
- Modify: `src/battery_agent/cli.py`

- [ ] distributed agent graph를 조립한다.
- [ ] 실행 컨텍스트를 주입한다.
- [ ] shared workflow state를 주입한다.
- [ ] handoff 결과에 따라 다음 agent를 호출하도록 연결한다.
- [ ] 산출물 저장 시점을 연결한다.
- [ ] 최종 Markdown/PDF 생성 흐름을 연결한다.

### Task 31: CLI UX

**Files:**
- Modify: `src/battery_agent/cli.py`

- [ ] 기본 주제 입력 옵션을 추가한다.
- [ ] 코퍼스 경로 입력 옵션을 추가한다.
- [ ] 출력 경로 입력 옵션을 추가한다.
- [ ] 웹 검색 활성화 옵션을 추가한다.
- [ ] 실행 결과 요약을 콘솔에 출력한다.

### Task 32: Artifact Schema Documentation

**Files:**
- Modify: `README.md`

- [ ] 저장되는 중간 산출물 목록을 문서화한다.
- [ ] 디렉터리 구조 예시를 문서화한다.
- [ ] 로그 파일 종류를 문서화한다.
- [ ] 부분 보고서 생성 조건을 문서화한다.

### Task 33: Reproducibility Controls

**Files:**
- Modify: `src/battery_agent/config.py`
- Modify: `src/battery_agent/pipeline/orchestrator.py`

- [ ] 실행 시 사용 모델 정보를 기록한다.
- [ ] 코퍼스 스냅샷 식별자를 기록한다.
- [ ] 검색 파라미터를 기록한다.
- [ ] 웹 검색 사용 여부를 기록한다.

### Task 34: Failure Messaging

**Files:**
- Modify: `src/battery_agent/agents/report_generation.py`
- Modify: `src/battery_agent/reporting/markdown_renderer.py`

- [ ] 근거 부족 섹션 문구를 정의한다.
- [ ] 단정 회피 문구를 정의한다.
- [ ] 전체 실패 조건 메시지를 정의한다.
- [ ] 부분 보고서 표기를 Markdown에 반영한다.

### Task 35: Unit Tests for Models and Utilities

**Files:**
- Create: `tests/test_config.py`
- Create: `tests/test_paths.py`
- Create: `tests/test_models.py`
- Create: `tests/test_reference_formatting.py`

- [ ] 설정 로딩 테스트를 작성한다.
- [ ] 아티팩트 경로 생성 테스트를 작성한다.
- [ ] 모델 직렬화 테스트를 작성한다.
- [ ] 참고문헌 포맷 테스트를 작성한다.

### Task 36: Retrieval and Curation Tests

**Files:**
- Create: `tests/test_local_retriever.py`
- Create: `tests/test_query_builder.py`
- Create: `tests/test_curation_agents.py`

- [ ] 기업별 질의 생성 테스트를 작성한다.
- [ ] 검색 결과 정렬 테스트를 작성한다.
- [ ] 중복 제거 테스트를 작성한다.
- [ ] 신뢰도 우선순위 테스트를 작성한다.

### Task 37: Analysis and Comparison Tests

**Files:**
- Create: `tests/test_analysis_agents.py`
- Create: `tests/test_comparison_agent.py`

- [ ] 기업 분석 결과 스키마 테스트를 작성한다.
- [ ] SWOT 출력 구조 테스트를 작성한다.
- [ ] 종합 시사점 출력 테스트를 작성한다.
- [ ] 근거 연결 유지 테스트를 작성한다.

### Task 38: Report Rendering Tests

**Files:**
- Create: `tests/test_markdown_renderer.py`
- Create: `tests/test_pdf_renderer.py`

- [ ] SUMMARY가 첫 섹션인지 테스트한다.
- [ ] REFERENCE가 마지막 섹션인지 테스트한다.
- [ ] SUMMARY 길이 제한 처리 테스트를 작성한다.
- [ ] PDF 생성 호출 테스트를 작성한다.

### Task 39: Orchestrator and Retry Tests

**Files:**
- Create: `tests/test_workflow_state.py`
- Create: `tests/test_handoffs.py`
- Create: `tests/test_retry_policy.py`
- Create: `tests/test_orchestrator.py`

- [ ] handoff 계약 테스트를 작성한다.
- [ ] LG lane 상태 전이 테스트를 작성한다.
- [ ] CATL lane 상태 전이 테스트를 작성한다.
- [ ] 재시도 순서 테스트를 작성한다.
- [ ] 부분 보고서 전환 테스트를 작성한다.
- [ ] 전체 실패 판정 테스트를 작성한다.

### Task 40: Sample Corpus and Fixture Setup

**Files:**
- Create: `tests/fixtures/`
- Modify: `README.md`

- [ ] 최소 샘플 코퍼스 구조를 만든다.
- [ ] 테스트용 문서 메타데이터를 만든다.
- [ ] LG/CATL 예시 근거 fixture를 만든다.
- [ ] 로컬 테스트 실행 방법을 README에 적는다.

### Task 41: End-to-End Dry Run

**Files:**
- Modify: `tests/`

- [ ] 샘플 코퍼스로 CLI 드라이런 테스트를 추가한다.
- [ ] Markdown 산출물 생성 여부를 검증한다.
- [ ] PDF 산출물 생성 여부를 검증한다.
- [ ] 중간 산출물 저장 여부를 검증한다.

### Task 42: Submission Readiness

**Files:**
- Modify: `README.md`

- [ ] Workflow 5요소 문서 링크를 정리한다.
- [ ] Agent 정의와 상태/그래프 설명을 정리한다.
- [ ] 보고서 목차 초안을 README 또는 문서에 반영한다.
- [ ] Github 저장소 제출 체크리스트를 정리한다.

## Recommended Execution Order

1. Task 1-5
2. Task 7-13
3. Task 14-20
4. Task 21-30
5. Task 31-34
6. Task 35-39
7. Task 40-42

## Sprint Breakdown

### Sprint 1: Foundation and Project Bootstrapping

**Goal:** 실행 가능한 프로젝트 골격과 공통 런타임 기반을 만든다.

**Included Tasks:**
- Task 1: Project Skeleton
- Task 2: Runtime Config
- Task 3: Artifact Directory Policy
- Task 4: Logging and Traceability
- Task 5: Domain Models

**Primary Outcome:**
- 패키지 구조, CLI 엔트리포인트, 설정 로딩, 공통 모델, 로그/아티팩트 저장 기반이 준비된다.

### Sprint 2: Corpus and Retrieval Infrastructure

**Goal:** 로컬 코퍼스 검색과 임베딩/인덱싱 기반을 구축한다.

**Included Tasks:**
- Task 7: Corpus Input Contract
- Task 8: Chunking
- Task 9: Embedding Layer
- Task 10: Vector Index
- Task 11: Query Builder
- Task 12: Local Retriever
- Task 13: Limited Web Search

**Primary Outcome:**
- 코퍼스 로딩부터 chunking, embedding, 인덱스, 질의 생성, 로컬/웹 검색까지 retrieval 기반이 준비된다.

### Sprint 3: Company Lanes and Comparative Analysis

**Goal:** LG/CATL 분석 라인과 비교 분석 핵심 로직을 구현한다.

**Included Tasks:**
- Task 14: LG Retrieval Agent
- Task 15: CATL Retrieval Agent
- Task 16: LG Evidence Curation Agent
- Task 17: CATL Evidence Curation Agent
- Task 18: LG Analysis Agent
- Task 19: CATL Analysis Agent
- Task 20: Comparison Evaluation Agent

**Primary Outcome:**
- 두 회사의 distributed lane과 comparison/refinement 흐름이 동작한다.

### Sprint 4: Reporting Pipeline and Distributed Workflow

**Goal:** handoff 기반 workflow와 최종 보고서 생성 경로를 완성한다.

**Included Tasks:**
- Task 21: Reference Agent
- Task 22: Report Outline Contract
- Task 23: Report Generation Agent
- Task 24: Markdown Renderer
- Task 25: PDF Renderer
- Task 26: Retry Policy
- Task 27: Workflow State and Handoff Contracts
- Task 28: LG Lane Transition Rules
- Task 29: CATL Lane Transition Rules
- Task 30: Orchestrator

**Primary Outcome:**
- agent handoff, retry, partial report, Markdown/PDF 산출까지 end-to-end workflow가 연결된다.

### Sprint 5: Productization and Operational Controls

**Goal:** 실제 사용 가능한 CLI와 운영 메타데이터를 정리한다.

**Included Tasks:**
- Task 31: CLI UX
- Task 32: Artifact Schema Documentation
- Task 33: Reproducibility Controls
- Task 34: Failure Messaging

**Primary Outcome:**
- 실행 UX, 문서화, 재현성 기록, 실패 메시지 정책이 정리된다.

### Sprint 6: Verification and Quality Gate

**Goal:** 기능별 테스트와 그래프 실행 검증을 구축한다.

**Included Tasks:**
- Task 35: Unit Tests for Models and Utilities
- Task 36: Retrieval and Curation Tests
- Task 37: Analysis and Comparison Tests
- Task 38: Report Rendering Tests
- Task 39: Orchestrator and Retry Tests

**Primary Outcome:**
- 핵심 모듈, distributed lane, handoff, retry, renderer까지 자동 검증 체계가 갖춰진다.

### Sprint 7: Fixtures, E2E, and Submission Readiness

**Goal:** 샘플 데이터 기반 검증과 제출물 정리를 완료한다.

**Included Tasks:**
- Task 40: Sample Corpus and Fixture Setup
- Task 41: End-to-End Dry Run
- Task 42: Submission Readiness

**Primary Outcome:**
- 샘플 코퍼스로 전체 드라이런이 가능하고, 제출에 필요한 문서/저장소 정리가 완료된다.

## Notes

- 이 문서는 `service-definition.md`만을 기준으로 작성했다.
- 현재 저장소에 구현 코드가 없어서 파일 경로는 제안안이다.
- 실제 개발 시 사용 라이브러리 선택에 따라 일부 파일은 합치거나 나눌 수 있다.
