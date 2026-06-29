from ticket_router.classifier import classify_ticket
from ticket_router.models import Ticket
from ticket_router.taxonomy import load_taxonomy


def test_routes_security_breach_as_urgent() -> None:
    ticket = Ticket(
        id="SEC-1",
        title="Possible token leaked in production logs",
        body="A customer found a secret exposed and worries about a breach.",
    )

    decision = classify_ticket(ticket)

    assert decision.category == "security"
    assert decision.owner == "security"
    assert decision.severity == "P0"
    assert decision.sla_hours == 1
    assert decision.confidence >= 0.75


def test_routes_billing_payment_issue() -> None:
    ticket = Ticket(
        id="BILL-7",
        title="Invoice charge failed",
        body="Credit card payment failed for the annual subscription.",
    )

    decision = classify_ticket(ticket)

    assert decision.category == "billing"
    assert decision.owner == "billing-ops"
    assert decision.severity in {"P1", "P2"}
    assert "payment" in " ".join(decision.matched_signals)


def test_unknown_ticket_is_low_confidence_triage() -> None:
    ticket = Ticket(id="MISC-1", title="hello", body="just checking the mailbox")

    decision = classify_ticket(ticket)

    assert decision.category == "other"
    assert decision.owner == "triage"
    assert decision.confidence == 0.35


def test_label_boost_can_route_sparse_ticket() -> None:
    ticket = Ticket(
        id="DOC-2",
        title="unclear example",
        body="please improve this",
        labels=("docs",),
    )

    decision = classify_ticket(ticket)

    assert decision.category == "docs"
    assert decision.owner == "developer-experience"


def test_custom_taxonomy_adds_new_category(tmp_path) -> None:
    taxonomy_path = tmp_path / "taxonomy.json"
    taxonomy_path.write_text(
        """
        {
          "categories": [
            {
              "name": "compliance",
              "owner": "trust-and-safety",
              "default_severity": "P1",
              "keywords": [{"phrase": "gdpr", "weight": 5}, "data processing agreement"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    taxonomy = load_taxonomy(taxonomy_path)
    ticket = Ticket(
        id="LEGAL-3",
        title="GDPR DPA review",
        body="Need data processing agreement help.",
    )
    decision = classify_ticket(ticket, taxonomy)

    assert decision.category == "compliance"
    assert decision.owner == "trust-and-safety"
    assert decision.severity == "P1"
