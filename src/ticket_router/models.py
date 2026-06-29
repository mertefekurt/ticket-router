from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _split_labels(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        parts = re.split(r"[;,]", value)
    elif isinstance(value, (list, tuple, set)):
        parts = [_coerce_text(item) for item in value]
    else:
        parts = [_coerce_text(value)]
    return tuple(part.strip().lower() for part in parts if part and part.strip())


@dataclass(frozen=True)
class Ticket:
    id: str
    title: str
    body: str
    labels: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, row: dict[str, Any], fallback_id: str) -> Ticket:
        lowered = {str(key).lower(): value for key, value in row.items()}

        def first(*keys: str) -> str:
            for key in keys:
                value = _coerce_text(lowered.get(key))
                if value:
                    return value
            return ""

        ticket_id = first("id", "ticket_id", "key", "number") or fallback_id
        title = first("title", "subject", "summary")
        body = first("body", "description", "text", "message", "content")
        labels = _split_labels(lowered.get("labels") or lowered.get("tags"))
        consumed = {
            "id",
            "ticket_id",
            "key",
            "number",
            "title",
            "subject",
            "summary",
            "body",
            "description",
            "text",
            "message",
            "content",
            "labels",
            "tags",
        }
        metadata = {
            str(key): _coerce_text(value)
            for key, value in row.items()
            if str(key).lower() not in consumed and _coerce_text(value)
        }
        return cls(id=ticket_id, title=title, body=body, labels=labels, metadata=metadata)

    @property
    def search_text(self) -> str:
        return " ".join(
            part
            for part in [
                self.title,
                self.body,
                " ".join(self.labels),
                " ".join(self.metadata.values()),
            ]
            if part
        )


@dataclass(frozen=True)
class WeightedSignal:
    phrase: str
    weight: float = 1.0


@dataclass(frozen=True)
class CategoryRule:
    name: str
    owner: str
    keywords: tuple[WeightedSignal, ...]
    default_severity: str = "P2"


@dataclass(frozen=True)
class SeverityRule:
    severity: str
    sla_hours: int
    keywords: tuple[WeightedSignal, ...]


@dataclass(frozen=True)
class Taxonomy:
    categories: tuple[CategoryRule, ...]
    severity_rules: tuple[SeverityRule, ...]


@dataclass(frozen=True)
class RoutingDecision:
    ticket_id: str
    category: str
    owner: str
    severity: str
    sla_hours: int
    confidence: float
    rationale: str
    matched_signals: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "category": self.category,
            "owner": self.owner,
            "severity": self.severity,
            "sla_hours": self.sla_hours,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "matched_signals": list(self.matched_signals),
        }

