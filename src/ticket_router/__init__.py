"""Support ticket routing for local automation workflows."""

from ticket_router.classifier import classify_many, classify_ticket
from ticket_router.models import RoutingDecision, Ticket

__all__ = ["RoutingDecision", "Ticket", "classify_many", "classify_ticket"]
__version__ = "0.1.0"

