# Ticket Router

![Ticket Router cover](assets/readme-cover.svg)

## What I keep this for

Local-first support ticket triage CLI for owner, severity, SLA, and confidence routing.

It is a small repo, so the README focuses on the path from clone to first useful output.

## Clone and run

```bash
git clone https://github.com/mertefekurt/ticket-router.git
cd ticket-router
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
ticket-router examples/custom-taxonomy.json
```

## Checks before changing it

```bash
ruff check .
pytest
python -m ticket_router --help
```
