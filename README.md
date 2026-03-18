# battery-agent

Battery Market Strategy Analysis Agent for comparing LG Energy Solution and CATL.

## Runtime Configuration

The CLI reads runtime settings from environment variables and also supports loading values from a local `.env` file. If the same key exists in both places, the OS environment variable wins.

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | None | OpenAI API key used for generation and analysis steps |
| `BATTERY_AGENT_EMBEDDING_MODEL` | No | `Qwen/Qwen3-Embedding-0.6B` | Embedding model identifier for local RAG indexing |
| `BATTERY_AGENT_CORPUS_DIR` | No | `corpus` | Directory containing normalized local corpus files |
| `BATTERY_AGENT_OUTPUT_DIR` | No | `artifacts` | Root directory for run outputs and logs |
| `BATTERY_AGENT_WEB_SEARCH` | No | `false` | Enables limited supplementary web search when set to `true` |
| `BATTERY_AGENT_WEB_SEARCH_MAX_RESULTS` | No | `5` | Maximum number of web search results kept after bias filtering |

Example `.env`:

```dotenv
OPENAI_API_KEY=your-api-key
BATTERY_AGENT_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
BATTERY_AGENT_CORPUS_DIR=corpus
BATTERY_AGENT_OUTPUT_DIR=artifacts
BATTERY_AGENT_WEB_SEARCH=false
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

## Development

Run tests with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run the CLI with:

```bash
PYTHONPATH=src python3 -m battery_agent.cli
```
