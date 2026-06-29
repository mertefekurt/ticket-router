import json

from ticket_router.cli import main
from ticket_router.io import read_tickets


def test_reads_jsonl_input(tmp_path) -> None:
    path = tmp_path / "tickets.jsonl"
    path.write_text(
        '{"id":"A-1","title":"Login timeout","body":"SSO login hits timeout"}\n',
        encoding="utf-8",
    )

    tickets = read_tickets(path)

    assert len(tickets) == 1
    assert tickets[0].id == "A-1"
    assert tickets[0].labels == ()


def test_reads_csv_input_with_tags(tmp_path) -> None:
    path = tmp_path / "tickets.csv"
    path.write_text(
        "id,title,description,tags\n"
        "C-1,Docs typo,The API guide has an incorrect example,docs;api\n",
        encoding="utf-8",
    )

    tickets = read_tickets(path)

    assert tickets[0].title == "Docs typo"
    assert tickets[0].labels == ("docs", "api")


def test_cli_writes_jsonl_and_summary(tmp_path) -> None:
    input_path = tmp_path / "tickets.jsonl"
    out_path = tmp_path / "routed.jsonl"
    summary_path = tmp_path / "summary.md"
    input_path.write_text(
        '{"id":"P-1","title":"Checkout outage","body":"Payment failing for all users"}\n',
        encoding="utf-8",
    )

    exit_code = main(
        [
            "route",
            str(input_path),
            "--out",
            str(out_path),
            "--summary",
            str(summary_path),
        ]
    )

    assert exit_code == 0
    routed = json.loads(out_path.read_text(encoding="utf-8"))
    assert routed["ticket_id"] == "P-1"
    assert routed["severity"] == "P0"
    assert "Tickets routed: 1" in summary_path.read_text(encoding="utf-8")


def test_cli_confidence_gate_returns_two(tmp_path, capsys) -> None:
    input_path = tmp_path / "tickets.jsonl"
    input_path.write_text(
        '{"id":"LOW-1","title":"hello","body":"just saying hi"}\n',
        encoding="utf-8",
    )

    exit_code = main(["route", str(input_path), "--min-confidence", "0.8"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "below confidence threshold" in captured.err
    assert '"ticket_id": "LOW-1"' in captured.out

