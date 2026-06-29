from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ticket_router import __version__
from ticket_router.classifier import classify_many
from ticket_router.io import decisions_to_jsonl, read_tickets, write_text
from ticket_router.report import build_markdown_summary
from ticket_router.taxonomy import load_taxonomy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ticket-router",
        description=(
            "Route support tickets to owners with severity, SLA, confidence, and rationale."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    route = subparsers.add_parser("route", help="classify tickets from JSONL or CSV")
    route.add_argument("input", type=Path, help="path to a .jsonl, .ndjson, or .csv ticket file")
    route.add_argument(
        "--format",
        choices=("auto", "jsonl", "csv"),
        default="auto",
        help="input format, inferred from extension by default",
    )
    route.add_argument("--taxonomy", type=Path, help="optional JSON taxonomy override")
    route.add_argument("--out", type=Path, help="write routed ticket JSONL to this path")
    route.add_argument("--summary", type=Path, help="write a Markdown summary report")
    route.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="exit with code 2 if any ticket routes below this confidence",
    )
    route.set_defaults(func=_route)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"ticket-router: error: {exc}", file=sys.stderr)
        return 1


def _route(args: argparse.Namespace) -> int:
    if not 0 <= args.min_confidence <= 1:
        raise ValueError("--min-confidence must be between 0 and 1")

    taxonomy = load_taxonomy(args.taxonomy)
    tickets = read_tickets(args.input, args.format)
    decisions = classify_many(tickets, taxonomy)

    write_text(args.out, decisions_to_jsonl(decisions))
    if args.summary:
        write_text(args.summary, build_markdown_summary(decisions))

    weak = [decision for decision in decisions if decision.confidence < args.min_confidence]
    if weak:
        ids = ", ".join(decision.ticket_id for decision in weak)
        print(
            f"ticket-router: {len(weak)} ticket(s) below confidence threshold: {ids}",
            file=sys.stderr,
        )
        return 2
    return 0
