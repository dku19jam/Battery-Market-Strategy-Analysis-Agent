"""Retry policy for distributed workflow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_local_retries: int = 2
    max_query_rewrites: int = 1
    max_web_retries: int = 1

    def should_retry(self, stage: str, attempt: int) -> bool:
        limits = {
            "local": self.max_local_retries,
            "rewrite": self.max_query_rewrites,
            "web": self.max_web_retries,
        }
        return attempt < limits.get(stage, 0)

    def should_emit_partial_report(self, missing_core_inputs: bool) -> bool:
        return missing_core_inputs
