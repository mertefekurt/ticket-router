from __future__ import annotations

import math
import re
from dataclasses import dataclass

from ticket_router.models import CategoryRule, RoutingDecision, SeverityRule, Taxonomy, Ticket
from ticket_router.taxonomy import default_taxonomy

_BOUNDARY_CACHE: dict[str, re.Pattern[str]] = {}
_SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
_DEFAULT_SLA = {"P0": 1, "P1": 4, "P2": 24, "P3": 72, "P4": 168}


@dataclass(frozen=True)
class _Score:
    name: str
    score: float
    owner: str
    default_severity: str
    signals: tuple[str, ...]


@dataclass(frozen=True)
class _SeverityScore:
    severity: str
    sla_hours: int
    score: float
    signals: tuple[str, ...]


def classify_many(tickets: list[Ticket], taxonomy: Taxonomy | None = None) -> list[RoutingDecision]:
    active_taxonomy = taxonomy or default_taxonomy()
    return [classify_ticket(ticket, active_taxonomy) for ticket in tickets]


def classify_ticket(ticket: Ticket, taxonomy: Taxonomy | None = None) -> RoutingDecision:
    active_taxonomy = taxonomy or default_taxonomy()
    category_scores = [
        _score_category(ticket, category) for category in active_taxonomy.categories
    ]
    category_scores.sort(key=lambda item: item.score, reverse=True)

    best = category_scores[0] if category_scores else _unknown_score()
    second_score = category_scores[1].score if len(category_scores) > 1 else 0.0
    if best.score <= 0:
        best = _unknown_score()
        second_score = 0.0

    severity = _score_severity(ticket, active_taxonomy.severity_rules, best.default_severity)
    confidence = _confidence(best.score, second_score, severity.score)
    all_signals = tuple(dict.fromkeys(best.signals + severity.signals))
    rationale = _rationale(best, severity, all_signals)

    return RoutingDecision(
        ticket_id=ticket.id,
        category=best.name,
        owner=best.owner,
        severity=severity.severity,
        sla_hours=severity.sla_hours,
        confidence=confidence,
        rationale=rationale,
        matched_signals=all_signals,
    )


def _score_category(ticket: Ticket, category: CategoryRule) -> _Score:
    text = _normalize(ticket.search_text)
    score = 0.0
    signals: list[str] = []

    for signal in category.keywords:
        if _contains_signal(text, signal.phrase):
            score += signal.weight
            signals.append(f"{signal.phrase}:{signal.weight:g}")

    if category.name.lower() in ticket.labels:
        score += 2.0
        signals.append(f"label:{category.name}")

    return _Score(
        name=category.name,
        score=score,
        owner=category.owner,
        default_severity=category.default_severity,
        signals=tuple(signals),
    )


def _score_severity(
    ticket: Ticket,
    severity_rules: tuple[SeverityRule, ...],
    fallback: str,
) -> _SeverityScore:
    text = _normalize(ticket.search_text)
    scored: list[_SeverityScore] = []

    for rule in severity_rules:
        score = 0.0
        signals: list[str] = []
        for signal in rule.keywords:
            if _contains_signal(text, signal.phrase):
                score += signal.weight
                signals.append(f"{rule.severity}:{signal.phrase}:{signal.weight:g}")
        scored.append(
            _SeverityScore(
                severity=rule.severity,
                sla_hours=rule.sla_hours,
                score=score,
                signals=tuple(signals),
            )
        )

    scored = [item for item in scored if item.score > 0]
    if scored:
        scored.sort(key=lambda item: (-item.score, _SEVERITY_RANK.get(item.severity, 99)))
        return scored[0]

    normalized = fallback.upper()
    return _SeverityScore(
        severity=normalized,
        sla_hours=_DEFAULT_SLA.get(normalized, 72),
        score=0.0,
        signals=(f"default_severity:{normalized}",),
    )


def _contains_signal(normalized_text: str, phrase: str) -> bool:
    normalized_phrase = _normalize(phrase)
    if not normalized_phrase:
        return False
    if " " in normalized_phrase:
        return normalized_phrase in normalized_text

    pattern = _BOUNDARY_CACHE.get(normalized_phrase)
    if pattern is None:
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])")
        _BOUNDARY_CACHE[normalized_phrase] = pattern
    return bool(pattern.search(normalized_text))


def _normalize(text: str) -> str:
    lowered = text.casefold()
    return re.sub(r"\s+", " ", lowered).strip()


def _confidence(category_score: float, second_score: float, severity_score: float) -> float:
    if category_score <= 0:
        return 0.35
    margin = max(category_score - second_score, 0.0)
    raw = 0.46 + math.tanh(category_score / 6) * 0.28 + math.tanh(margin / 4) * 0.16
    if severity_score > 0:
        raw += 0.06
    return round(min(max(raw, 0.35), 0.96), 2)


def _rationale(
    category: _Score,
    severity: _SeverityScore,
    signals: tuple[str, ...],
) -> str:
    if category.name == "other":
        return "No strong routing signals were found; send to triage for human review."

    signal_text = ", ".join(signals[:5]) if signals else "default routing"
    return (
        f"Routed to {category.owner} as {category.name}; "
        f"severity {severity.severity} uses SLA {severity.sla_hours}h. "
        f"Top signals: {signal_text}."
    )


def _unknown_score() -> _Score:
    return _Score(
        name="other",
        score=0.0,
        owner="triage",
        default_severity="P3",
        signals=(),
    )

