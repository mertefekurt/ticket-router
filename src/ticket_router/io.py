from __future__ import annotations

import csv
import json
from pathlib import Path

from ticket_router.models import RoutingDecision, Ticket


def read_tickets(path: Path, input_format: str = "auto") -> list[Ticket]:
    resolved_format = _resolve_format(path, input_format)
    if resolved_format == "jsonl":
        return _read_jsonl(path)
    if resolved_format == "csv":
        return _read_csv(path)
    raise ValueError(f"unsupported input format: {resolved_format}")


def decisions_to_jsonl(decisions: list[RoutingDecision]) -> str:
    lines = [json.dumps(decision.to_dict(), sort_keys=True) for decision in decisions]
    return "\n".join(lines) + ("\n" if lines else "")


def write_text(path: Path | None, content: str) -> None:
    if path is None:
        print(content, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _resolve_format(path: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".jsonl", ".ndjson"}:
        return "jsonl"
    raise ValueError("could not infer input format; pass --format jsonl or --format csv")


def _read_jsonl(path: Path) -> list[Ticket]:
    tickets: list[Ticket] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON on line {line_number}: {exc.msg}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"line {line_number} must contain a JSON object")
        tickets.append(Ticket.from_mapping(raw, fallback_id=str(line_number)))
    return tickets


def _read_csv(path: Path) -> list[Ticket]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV input requires a header row")
        return [
            Ticket.from_mapping(dict(row), fallback_id=str(index))
            for index, row in enumerate(reader, start=1)
        ]

