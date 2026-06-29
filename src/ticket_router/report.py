from __future__ import annotations

from collections import Counter

from ticket_router.models import RoutingDecision


def build_markdown_summary(decisions: list[RoutingDecision]) -> str:
    category_counts = Counter(decision.category for decision in decisions)
    severity_counts = Counter(decision.severity for decision in decisions)
    low_confidence = [decision for decision in decisions if decision.confidence < 0.6]

    lines = [
        "# Ticket routing summary",
        "",
        f"Tickets routed: {len(decisions)}",
        "",
        "## Categories",
        "",
        *_counter_lines(category_counts),
        "",
        "## Severity",
        "",
        *_counter_lines(severity_counts),
        "",
        "## Low-confidence tickets",
        "",
    ]

    if low_confidence:
        lines.extend(
            f"- `{decision.ticket_id}` -> {decision.category} "
            f"({decision.confidence:.2f}, owner: {decision.owner})"
            for decision in low_confidence
        )
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def _counter_lines(counter: Counter[str]) -> list[str]:
    if not counter:
        return ["- none"]
    return [f"- {name}: {count}" for name, count in sorted(counter.items())]

