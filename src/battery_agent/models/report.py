"""Report artifact model."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ReportArtifact:
    title: str
    markdown_path: str
    pdf_path: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "ReportArtifact":
        return cls(**data)
