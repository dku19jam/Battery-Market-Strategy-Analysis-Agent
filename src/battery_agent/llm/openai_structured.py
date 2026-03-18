"""Structured JSON generation via the OpenAI Responses API."""

from __future__ import annotations

import json
from typing import Any


class StructuredOpenAIClient:
    def __init__(
        self,
        client: Any | None = None,
        api_key: str | None = None,
        max_retries: int = 1,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self.max_retries = max_retries

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self._api_key)
        return self._client

    def generate_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        schema: dict[str, object],
    ) -> dict[str, object]:
        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            response = self._get_client().responses.create(
                model=model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_prompt}],
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "schema": schema,
                        "strict": True,
                    }
                },
            )
            try:
                return json.loads(response.output_text)
            except (json.JSONDecodeError, TypeError) as exc:
                last_error = exc
        raise ValueError(f"Structured JSON generation failed for schema '{schema_name}'") from last_error
