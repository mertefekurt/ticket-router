from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ticket_router.models import CategoryRule, SeverityRule, Taxonomy, WeightedSignal


def default_taxonomy() -> Taxonomy:
    return Taxonomy(
        categories=(
            CategoryRule(
                name="security",
                owner="security",
                default_severity="P1",
                keywords=_signals(
                    [
                        ("security", 2.0),
                        ("vulnerability", 3.0),
                        ("xss", 3.0),
                        ("csrf", 3.0),
                        ("sql injection", 4.0),
                        ("breach", 4.0),
                        ("token leaked", 4.0),
                        ("secret exposed", 4.0),
                        ("exploit", 4.0),
                        ("cve", 3.0),
                    ]
                ),
            ),
            CategoryRule(
                name="incident",
                owner="platform-oncall",
                default_severity="P1",
                keywords=_signals(
                    [
                        ("outage", 4.0),
                        ("down", 3.0),
                        ("unavailable", 3.0),
                        ("production", 2.0),
                        ("500", 2.5),
                        ("error rate", 3.0),
                        ("all users", 3.5),
                        ("degraded", 2.5),
                        ("incident", 3.0),
                    ]
                ),
            ),
            CategoryRule(
                name="auth",
                owner="identity",
                keywords=_signals(
                    [
                        ("login", 2.5),
                        ("sign in", 2.5),
                        ("oauth", 3.0),
                        ("sso", 3.0),
                        ("password", 2.0),
                        ("mfa", 2.5),
                        ("permission", 2.0),
                        ("403", 2.5),
                        ("401", 2.5),
                    ]
                ),
            ),
            CategoryRule(
                name="billing",
                owner="billing-ops",
                keywords=_signals(
                    [
                        ("invoice", 3.0),
                        ("charge", 2.5),
                        ("billing", 3.0),
                        ("refund", 2.5),
                        ("payment", 3.0),
                        ("subscription", 2.5),
                        ("credit card", 2.5),
                    ]
                ),
            ),
            CategoryRule(
                name="data",
                owner="data-platform",
                keywords=_signals(
                    [
                        ("export", 2.0),
                        ("import", 2.0),
                        ("missing data", 3.0),
                        ("duplicate", 2.0),
                        ("schema", 2.5),
                        ("csv", 2.0),
                        ("sync", 2.5),
                        ("migration", 2.0),
                    ]
                ),
            ),
            CategoryRule(
                name="performance",
                owner="performance",
                keywords=_signals(
                    [
                        ("slow", 2.5),
                        ("latency", 3.0),
                        ("timeout", 3.0),
                        ("performance", 2.5),
                        ("takes minutes", 3.0),
                        ("lag", 2.0),
                        ("p95", 3.0),
                    ]
                ),
            ),
            CategoryRule(
                name="devops",
                owner="devops",
                keywords=_signals(
                    [
                        ("deploy", 2.5),
                        ("ci", 2.0),
                        ("build", 2.0),
                        ("container", 2.0),
                        ("kubernetes", 3.0),
                        ("terraform", 3.0),
                        ("webhook", 2.0),
                        ("environment variable", 2.0),
                    ]
                ),
            ),
            CategoryRule(
                name="feature",
                owner="product",
                default_severity="P3",
                keywords=_signals(
                    [
                        ("feature request", 4.0),
                        ("would like", 2.5),
                        ("can you add", 3.0),
                        ("enhancement", 3.0),
                        ("support for", 2.5),
                        ("roadmap", 2.0),
                    ]
                ),
            ),
            CategoryRule(
                name="docs",
                owner="developer-experience",
                default_severity="P3",
                keywords=_signals(
                    [
                        ("documentation", 3.0),
                        ("docs", 2.5),
                        ("tutorial", 2.5),
                        ("example", 2.0),
                        ("guide", 2.0),
                        ("readme", 2.0),
                    ]
                ),
            ),
        ),
        severity_rules=(
            SeverityRule(
                severity="P0",
                sla_hours=1,
                keywords=_signals(
                    [
                        ("breach", 5.0),
                        ("data loss", 5.0),
                        ("production down", 5.0),
                        ("outage", 4.0),
                        ("all users", 4.0),
                        ("cannot access", 3.0),
                        ("unavailable", 3.0),
                    ]
                ),
            ),
            SeverityRule(
                severity="P1",
                sla_hours=4,
                keywords=_signals(
                    [
                        ("blocked", 3.0),
                        ("cannot login", 3.0),
                        ("payment failing", 3.0),
                        ("major customer", 3.0),
                        ("regression", 2.5),
                        ("high priority", 2.5),
                    ]
                ),
            ),
            SeverityRule(
                severity="P2",
                sla_hours=24,
                keywords=_signals(
                    [
                        ("bug", 2.0),
                        ("error", 2.0),
                        ("timeout", 2.5),
                        ("slow", 2.0),
                        ("failed", 2.0),
                        ("incorrect", 2.0),
                    ]
                ),
            ),
            SeverityRule(
                severity="P3",
                sla_hours=72,
                keywords=_signals(
                    [
                        ("question", 2.0),
                        ("feature request", 3.0),
                        ("documentation", 2.5),
                        ("how do i", 2.0),
                        ("nice to have", 2.0),
                    ]
                ),
            ),
        ),
    )


def load_taxonomy(path: Path | None) -> Taxonomy:
    base = default_taxonomy()
    if path is None:
        return base

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("taxonomy must be a JSON object")

    categories = {category.name: category for category in base.categories}
    for item in raw.get("categories", []):
        category = _category_from_json(item)
        categories[category.name] = category

    custom_severity = tuple(_severity_from_json(item) for item in raw.get("severity_rules", []))
    if not custom_severity and "severity" in raw:
        custom_severity = tuple(_severity_from_json(item) for item in raw["severity"])

    return Taxonomy(
        categories=tuple(categories.values()),
        severity_rules=custom_severity + base.severity_rules,
    )


def _signals(items: list[str | tuple[str, float] | dict[str, Any]]) -> tuple[WeightedSignal, ...]:
    signals: list[WeightedSignal] = []
    for item in items:
        if isinstance(item, str):
            signals.append(WeightedSignal(phrase=item, weight=1.0))
        elif isinstance(item, tuple):
            phrase, weight = item
            signals.append(WeightedSignal(phrase=phrase, weight=float(weight)))
        elif isinstance(item, dict):
            phrase = item.get("phrase") or item.get("keyword")
            if not phrase:
                raise ValueError("signal object requires a phrase")
            signals.append(
                WeightedSignal(phrase=str(phrase), weight=float(item.get("weight", 1.0)))
            )
        else:
            raise ValueError(f"unsupported signal entry: {item!r}")
    return tuple(signals)


def _category_from_json(item: Any) -> CategoryRule:
    if not isinstance(item, dict):
        raise ValueError("category entries must be objects")
    try:
        name = str(item["name"]).strip()
        owner = str(item["owner"]).strip()
    except KeyError as exc:
        raise ValueError("category entries require name and owner") from exc
    if not name or not owner:
        raise ValueError("category name and owner cannot be empty")
    return CategoryRule(
        name=name,
        owner=owner,
        default_severity=str(item.get("default_severity", "P2")),
        keywords=_signals(list(item.get("keywords", []))),
    )


def _severity_from_json(item: Any) -> SeverityRule:
    if not isinstance(item, dict):
        raise ValueError("severity entries must be objects")
    try:
        severity = str(item["severity"]).strip().upper()
        sla_hours = int(item["sla_hours"])
    except KeyError as exc:
        raise ValueError("severity entries require severity and sla_hours") from exc
    return SeverityRule(
        severity=severity,
        sla_hours=sla_hours,
        keywords=_signals(list(item.get("keywords", []))),
    )
