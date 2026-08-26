"""Development tests for the heartbeat's event-store ingress surface.

Plan: docs/superpowers/plans/2026-08-26-heartbeat.md
Validating tests are authored separately by Codex per repo norm; these are
the implementer's TDD tests.
"""
from hamutay.events import build_parser


def test_run_next_defaults_to_64000_max_tokens():
    args = build_parser().parse_args(["run-next", "--log-path", "x.jsonl"])
    assert args.max_tokens == 64000


def test_run_all_defaults_to_64000_max_tokens():
    args = build_parser().parse_args(["run-all", "--log-path", "x.jsonl"])
    assert args.max_tokens == 64000
