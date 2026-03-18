import unittest


class StructuredOpenAIClientTest(unittest.TestCase):
    def test_generate_json_retries_once_on_invalid_json(self) -> None:
        class FakeResponse:
            def __init__(self, output_text: str) -> None:
                self.output_text = output_text

        class FakeResponsesApi:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []
                self._responses = [
                    FakeResponse("not-json"),
                    FakeResponse('{"strategy_summary":"ok","strengths":[],"risks":[],"citations":[],"analysis_notes":"done"}'),
                ]

            def create(self, **kwargs: object) -> FakeResponse:
                self.calls.append(kwargs)
                return self._responses.pop(0)

        class FakeOpenAIClient:
            def __init__(self) -> None:
                self.responses = FakeResponsesApi()

        from battery_agent.llm.openai_structured import StructuredOpenAIClient

        fake_client = FakeOpenAIClient()
        client = StructuredOpenAIClient(client=fake_client)

        payload = client.generate_json(
            model="gpt-4o-mini",
            system_prompt="system",
            user_prompt="user",
            schema_name="company_analysis",
            schema={
                "type": "object",
                "properties": {
                    "strategy_summary": {"type": "string"},
                    "strengths": {"type": "array", "items": {"type": "string"}},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "citations": {"type": "array", "items": {"type": "string"}},
                    "analysis_notes": {"type": "string"},
                },
                "required": ["strategy_summary", "strengths", "risks", "citations", "analysis_notes"],
                "additionalProperties": False,
            },
        )

        self.assertEqual(payload["strategy_summary"], "ok")
        self.assertEqual(len(fake_client.responses.calls), 2)
