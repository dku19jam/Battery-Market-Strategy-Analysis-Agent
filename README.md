# battery-agent

Battery Market Strategy Analysis Agent for comparing LG Energy Solution and CATL.

## Runtime Configuration

The CLI reads runtime settings from environment variables and also supports loading values from a local `.env` file. If the same key exists in both places, the OS environment variable wins.

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | None | OpenAI API key used for generation and analysis steps |
| `TAVILY_API_KEY` | No | None | Tavily API key used when limited web search is enabled |
| `BATTERY_AGENT_EMBEDDING_MODEL` | No | `Qwen/Qwen3-Embedding-0.6B` | Embedding model identifier for local RAG indexing |
| `BATTERY_AGENT_EMBEDDING_DEVICE` | No | `auto` | Embedding device selection. On MacBook this resolves to `mps` first, then `cpu` |
| `BATTERY_AGENT_EMBEDDING_BATCH_SIZE` | No | `4` | Batch size for Qwen embedding inference |
| `BATTERY_AGENT_CORPUS_DIR` | No | `corpus` | Directory containing normalized local corpus files |
| `BATTERY_AGENT_OUTPUT_DIR` | No | `artifacts` | Root directory for run outputs and logs |
| `BATTERY_AGENT_CHROMA_DIR` | No | `data/chroma` | Persistent Chroma directory for embedded local corpus chunks |
| `BATTERY_AGENT_CHROMA_COLLECTION` | No | `battery-agent` | Chroma collection name used for ingest and retrieval |
| `BATTERY_AGENT_WEB_SEARCH` | No | `false` | Enables limited supplementary web search when set to `true` |
| `BATTERY_AGENT_WEB_SEARCH_MAX_CALLS` | No | `3` | Maximum number of web search calls allowed per searcher instance |
| `BATTERY_AGENT_WEB_SEARCH_MAX_RESULTS` | No | `5` | Maximum number of Tavily search results kept after source-cap filtering |

Example `.env`:

```dotenv
OPENAI_API_KEY=your-api-key
TAVILY_API_KEY=your-tavily-api-key
BATTERY_AGENT_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
BATTERY_AGENT_EMBEDDING_DEVICE=auto
BATTERY_AGENT_EMBEDDING_BATCH_SIZE=4
BATTERY_AGENT_CORPUS_DIR=corpus
BATTERY_AGENT_OUTPUT_DIR=artifacts
BATTERY_AGENT_CHROMA_DIR=data/chroma
BATTERY_AGENT_CHROMA_COLLECTION=battery-agent
BATTERY_AGENT_WEB_SEARCH=false
BATTERY_AGENT_WEB_SEARCH_MAX_CALLS=3
BATTERY_AGENT_WEB_SEARCH_MAX_RESULTS=5
```

## Defaults

| Setting | Value |
|---|---|
| Default companies | `LG에너지솔루션`, `CATL` |
| Default model | `gpt-4o-mini` |
| Default topic | `배터리 시장 전략 비교` |

## Local Corpus Contract

Set `BATTERY_AGENT_CORPUS_DIR` to a directory that contains normalized local corpus files. The loader currently accepts `.json` and `.jsonl` files only.

Each corpus record must contain the following fields:

| Field | Required | Description |
|---|---|---|
| `document_id` | Yes | Stable identifier used across chunking and retrieval artifacts |
| `company` | Yes | Company namespace, for example `LG에너지솔루션` or `CATL` |
| `title` | Yes | Human-readable document title |
| `text` | Yes | Normalized plain-text document body |
| `source_type` | Yes | Source category such as `report`, `web`, or `memo` |
| `page_count` | No | Integer page count used for chunking limits; defaults to `1` |
| `topics` | No | List of topic labels used for retrieval metadata |
| `metadata` | No | Additional JSON object for downstream processing |

Loading failure policy:

- Missing corpus directory raises `FileNotFoundError`.
- Records missing required fields raise `ValueError`.
- Unsupported file extensions are ignored.
- Invalid records should be fixed in the corpus source before indexing proceeds.

## PDF Ingest to Chroma

For the preferred local RAG path, place PDFs under company-named subdirectories:

```text
corpus/
  LG에너지솔루션/
    lg-report-1.pdf
    lg-report-2.pdf
  CATL/
    catl-report-1.pdf
```

Then ingest the PDF corpus into Chroma:

```bash
PYTHONPATH=src .venv/bin/python -m battery_agent.cli ingest-pdfs
```

You can override paths per run:

```bash
PYTHONPATH=src .venv/bin/python -m battery_agent.cli ingest-pdfs --corpus-dir corpus --chroma-dir data/chroma
```

Behavior:

- company metadata is derived from the folder name
- each PDF is converted to text with `pypdf`
- chunks are embedded with `Qwen/Qwen3-Embedding-0.6B`
- embeddings are persisted into the configured Chroma collection

On Apple Silicon MacBooks, set `BATTERY_AGENT_EMBEDDING_DEVICE=auto` or `mps`.

## Web Search

Limited web search uses Tavily. To enable it:

1. Install project dependencies so `tavily-python` is available.
2. Set `BATTERY_AGENT_WEB_SEARCH=true`.
3. Set `TAVILY_API_KEY` in your environment or `.env` file.

When enabled, Tavily results are normalized into the internal `WebSearchResult` format and then filtered by `max_per_source` to reduce source concentration.

## Run Artifacts

Each run uses a per-run artifact root. The current stable directories are:

- `logs/`
- `metadata/`
- `retrieval/`
- `evidence/`
- `analysis/`
- `reports/`

Saved intermediate artifacts include:

- chunk snapshots and vector index metadata
- per-company retrieval results
- per-company curation bundles
- per-company analysis results
- comparison result
- reference list
- final Markdown/PDF report

Log files include:

- `logs/run.log`

Partial reports are generated when one or more company lanes remain partial, when comparison requests refinement, or when references are incomplete but a bounded summary can still be rendered.

## Local Test Fixtures

Sample corpus fixtures are available under [tests/fixtures/sample_corpus/docs.jsonl](/Users/cjm/battery-agent/tests/fixtures/sample_corpus/docs.jsonl).

Run the full test suite locally with:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Run a dry-run style CLI execution against the sample corpus by pointing `BATTERY_AGENT_CORPUS_DIR` to `tests/fixtures/sample_corpus`.

## Design Docs

- Distributed architecture: [2026-03-17-distributed-agent-architecture-design.md](/Users/cjm/battery-agent/docs/superpowers/specs/2026-03-17-distributed-agent-architecture-design.md)
- Submission report draft: [2026-03-17-agent-system-report-draft.md](/Users/cjm/battery-agent/docs/superpowers/specs/2026-03-17-agent-system-report-draft.md)
- Implementation plan: [2026-03-17-battery-market-strategy-analysis-agent.md](/Users/cjm/battery-agent/docs/superpowers/plans/2026-03-17-battery-market-strategy-analysis-agent.md)

## Agent and Workflow Summary

Workflow 5 elements:

- Goal: compare LG에너지솔루션 and CATL portfolio diversification strategy and produce Korean Markdown/PDF output
- Criteria: evidence-backed comparison, bounded web search, reproducible artifacts, partial-report fallback
- Task: retrieval, curation, analysis, comparison, reference generation, report rendering
- Control Strategy: distributed lanes with handoff-based transitions and retry limits
- Structure: LG lane, CATL lane, comparison, reference, report, PDF rendering

Agent graph summary:

- `LG Retrieval -> LG Curation -> LG Analysis`
- `CATL Retrieval -> CATL Curation -> CATL Analysis`
- `Comparison -> Reference -> Report Generation -> PDF`

## Report Outline

- `SUMMARY`
- `MARKET_BACKGROUND`
- `LG_STRATEGY`
- `CATL_STRATEGY`
- `STRATEGY_COMPARISON`
- `SWOT`
- `INSIGHTS`
- `REFERENCE`

## Submission Checklist

- Architecture design document included
- Implementation plan included
- Sample fixture and test instructions included
- End-to-end dry-run test included
- Markdown/PDF generation path implemented
- Artifact and log structure documented

## Analysis and Comparison

Company analysis and cross-company comparison use the official OpenAI Python SDK with structured JSON output. The analysis agents build dynamic prompts from curated topic buckets and validate citations against the provided evidence set before producing artifacts.

## Development

Run tests with:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Run the CLI with:

```bash
PYTHONPATH=src .venv/bin/python -m battery_agent.cli
```

Install or refresh dependencies with:

```bash
uv pip install --python .venv/bin/python -e .
```
