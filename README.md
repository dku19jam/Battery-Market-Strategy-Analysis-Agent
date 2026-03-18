# battery-agent

Battery Market Strategy Analysis Agent for comparing LG Energy Solution and CATL.

## Runtime Configuration

The CLI reads runtime settings from environment variables and also supports loading values from a local `.env` file. If the same key exists in both places, the OS environment variable wins.

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | None | OpenAI API key used for generation and analysis steps |
| `BATTERY_AGENT_OUTPUT_DIR` | No | `artifacts` | Root directory for run outputs and logs |
| `BATTERY_AGENT_WEB_SEARCH` | No | `false` | Enables limited supplementary web search when set to `true` |

Example `.env`:

```dotenv
OPENAI_API_KEY=your-api-key
BATTERY_AGENT_OUTPUT_DIR=artifacts
BATTERY_AGENT_WEB_SEARCH=false
```

## Defaults

| Setting | Value |
|---|---|
| Default companies | `LG에너지솔루션`, `CATL` |
| Default model | `gpt-4o-mini` |
| Default topic | `배터리 시장 전략 비교` |

## Development

Run tests with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Run the CLI with:

```bash
PYTHONPATH=src python3 -m battery_agent.cli
```
