"""hamutay.billing — reconcile a session log against OpenRouter's own books.

Why: the record now carries in-band cost and generation ids
(tests/test_openrouter_cost.py), but the *authoritative* billing record
lives on OpenRouter's side, behind GET /api/v1/generation?id=..., and the
account balance behind GET /api/v1/credits. Tony (2026-08-29): "we could
build the actual tool needed: calling OpenRouter itself to extract the
billing information." Implementer's TDD tests.

Shapes below are copied from live responses on 2026-08-29, not from memory:
  /credits    -> {"data": {"total_credits": 835, "total_usage": 775.944651377}}
  /generation -> {"data": {"id": "gen-...", "usage": 3.4e-05, "model": ...,
                  "native_tokens_prompt": 14, "native_tokens_completion": 4,
                  "native_tokens_cached": 0, "latency": 442,
                  "generation_time": 457, "created_at": "...",
                  "provider_responses": [{"provider_name": "Amazon Bedrock", ...}]}}
  a generation is eventually consistent: 404 for seconds after the call.

Every fetched generation is persisted to an append-only sidecar next to the
log (tools that don't capture data are a perversion). The log itself is
never rewritten.
"""
import json

import pytest

from hamutay.billing import OpenRouterBilling, reconcile_log


class _FakeHTTP:
    """Scripted GET: url -> (status, body). Records every URL asked for."""

    def __init__(self, routes):
        self.routes = dict(routes)
        self.calls = []

    def __call__(self, url, headers):
        self.calls.append(url)
        assert headers["Authorization"] == "Bearer k"
        if url in self.routes:
            return self.routes[url]
        return 404, {"error": {"message": "not found", "code": 404}}


def _gen(gid, usage, prompt=100, completion=10, cached=0, provider="Amazon Bedrock"):
    return 200, {"data": {
        "id": gid, "usage": usage, "model": "anthropic/claude-4.5-haiku-20251001",
        "native_tokens_prompt": prompt, "native_tokens_completion": completion,
        "native_tokens_cached": cached, "native_tokens_reasoning": 0,
        "latency": 442, "generation_time": 457,
        "created_at": "2026-08-29T17:34:43.565Z", "finish_reason": "stop",
        "provider_responses": [{"provider_name": provider, "status": 200}],
    }}


GEN_URL = "https://openrouter.ai/api/v1/generation?id="


def _record(cycle, usage):
    return {"cycle": cycle, "record_id": f"rec-{cycle}",
            "timestamp": f"2026-08-29T17:0{cycle}:00+00:00", "usage": usage}


def _write_log(path, records):
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


# --- credits ----------------------------------------------------------------


def test_credits_reports_total_usage_and_remaining():
    http = _FakeHTTP({"https://openrouter.ai/api/v1/credits":
                      (200, {"data": {"total_credits": 835, "total_usage": 775.944651377}})})
    billing = OpenRouterBilling(api_key="k", http=http)
    credits = billing.credits()
    assert credits["total_credits"] == 835
    assert credits["total_usage"] == pytest.approx(775.944651377)
    assert credits["remaining"] == pytest.approx(59.055348623)


# --- one generation ---------------------------------------------------------


def test_generation_returns_authoritative_record():
    http = _FakeHTTP({GEN_URL + "gen-1": _gen("gen-1", 0.0123, cached=50)})
    billing = OpenRouterBilling(api_key="k", http=http)
    gen = billing.generation("gen-1")
    assert gen["id"] == "gen-1"
    assert gen["usage"] == pytest.approx(0.0123)
    assert gen["native_tokens_cached"] == 50


def test_generation_not_visible_yet_is_none_not_an_error():
    billing = OpenRouterBilling(api_key="k", http=_FakeHTTP({}))
    assert billing.generation("gen-later") is None


def test_generation_non_404_error_raises():
    http = _FakeHTTP({GEN_URL + "gen-1": (401, {"error": {"message": "bad key", "code": 401}})})
    billing = OpenRouterBilling(api_key="k", http=http)
    with pytest.raises(RuntimeError, match="401"):
        billing.generation("gen-1")


# --- reconcile a log --------------------------------------------------------


def test_reconcile_fetches_each_generation_and_reports_per_cycle(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_log(log, [
        _record(1, {"input_tokens": 100, "output_tokens": 10, "cost_usd": 0.03,
                    "cost_turns_unreported": 0, "generation_ids": ["gen-1", "gen-2"]}),
    ])
    http = _FakeHTTP({GEN_URL + "gen-1": _gen("gen-1", 0.01),
                      GEN_URL + "gen-2": _gen("gen-2", 0.02)})
    rows = reconcile_log(str(log), OpenRouterBilling(api_key="k", http=http))
    assert len(rows) == 1
    row = rows[0]
    assert row["cycle"] == 1
    assert row["recorded_cost_usd"] == pytest.approx(0.03)
    assert row["authoritative_cost_usd"] == pytest.approx(0.03)
    assert row["generations_total"] == 2
    assert row["generations_fetched"] == 2
    assert row["generations_pending"] == 0


def test_reconcile_persists_generations_to_sidecar_and_never_refetches(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_log(log, [
        _record(1, {"cost_usd": 0.01, "cost_turns_unreported": 0,
                    "generation_ids": ["gen-1"]}),
    ])
    http = _FakeHTTP({GEN_URL + "gen-1": _gen("gen-1", 0.01, cached=7)})
    billing = OpenRouterBilling(api_key="k", http=http)
    reconcile_log(str(log), billing)
    sidecar = tmp_path / "session.jsonl.billing.jsonl"
    entries = [json.loads(line) for line in sidecar.read_text().splitlines() if line.strip()]
    assert len(entries) == 1
    assert entries[0]["generation_id"] == "gen-1"
    assert entries[0]["cycle"] == 1
    assert entries[0]["record_id"] == "rec-1"
    assert entries[0]["usage_usd"] == pytest.approx(0.01)
    assert entries[0]["native_tokens_cached"] == 7
    assert entries[0]["provider"] == "Amazon Bedrock"
    assert "fetched_at" in entries[0]
    assert entries[0]["raw"]["id"] == "gen-1"

    # second run: nothing new to fetch; the sidecar is the cache
    http.calls.clear()
    rows = reconcile_log(str(log), billing)
    assert http.calls == []
    assert rows[0]["authoritative_cost_usd"] == pytest.approx(0.01)
    assert len(sidecar.read_text().splitlines()) == 1


def test_reconcile_leaves_not_yet_visible_generations_pending_for_next_run(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_log(log, [
        _record(1, {"cost_usd": 0.03, "cost_turns_unreported": 0,
                    "generation_ids": ["gen-1", "gen-late"]}),
    ])
    http = _FakeHTTP({GEN_URL + "gen-1": _gen("gen-1", 0.01)})
    billing = OpenRouterBilling(api_key="k", http=http)
    rows = reconcile_log(str(log), billing)
    assert rows[0]["generations_fetched"] == 1
    assert rows[0]["generations_pending"] == 1
    assert rows[0]["authoritative_cost_usd"] is None  # incomplete: not a number
    assert rows[0]["authoritative_cost_usd_partial"] == pytest.approx(0.01)

    # it appears; the next run picks it up and the row completes
    http.routes[GEN_URL + "gen-late"] = _gen("gen-late", 0.02)
    rows = reconcile_log(str(log), billing)
    assert rows[0]["generations_pending"] == 0
    assert rows[0]["authoritative_cost_usd"] == pytest.approx(0.03)


def test_reconcile_marks_records_without_generation_ids_unreconcilable(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_log(log, [
        _record(1, {"input_tokens": 509498, "output_tokens": 23892,
                    "cache_read_input_tokens": 381514,
                    "cache_creation_input_tokens": 127974, "stop_reason": "end_turn"}),
    ])
    http = _FakeHTTP({})
    rows = reconcile_log(str(log), OpenRouterBilling(api_key="k", http=http))
    assert rows[0]["cycle"] == 1
    assert rows[0]["unreconcilable"] is True
    assert rows[0]["recorded_cost_usd"] is None
    assert rows[0]["authoritative_cost_usd"] is None
    assert rows[0]["input_tokens"] == 509498
    assert http.calls == []


def test_reconcile_totals_are_over_reconciled_rows_only(tmp_path):
    from hamutay.billing import summarize

    rows = [
        {"cycle": 1, "unreconcilable": False, "recorded_cost_usd": 0.03,
         "authoritative_cost_usd": 0.03, "generations_pending": 0,
         "generations_total": 2, "generations_fetched": 2},
        {"cycle": 2, "unreconcilable": True, "recorded_cost_usd": None,
         "authoritative_cost_usd": None, "generations_pending": 0,
         "generations_total": 0, "generations_fetched": 0},
        {"cycle": 3, "unreconcilable": False, "recorded_cost_usd": 0.05,
         "authoritative_cost_usd": None, "authoritative_cost_usd_partial": 0.02,
         "generations_pending": 1, "generations_total": 2, "generations_fetched": 1},
    ]
    s = summarize(rows)
    assert s["cycles"] == 3
    assert s["cycles_unreconcilable"] == 1
    assert s["cycles_pending"] == 1
    assert s["recorded_cost_usd"] == pytest.approx(0.08)
    assert s["authoritative_cost_usd_complete"] == pytest.approx(0.03)
    assert s["authoritative_cost_usd_partial"] == pytest.approx(0.02)


# --- CLI --------------------------------------------------------------------


def test_cli_reconcile_prints_a_table_and_totals(tmp_path, capsys, monkeypatch):  # noqa: ARG001
    from hamutay.billing import main

    log = tmp_path / "session.jsonl"
    _write_log(log, [
        _record(1, {"cost_usd": 0.03, "cost_turns_unreported": 0,
                    "generation_ids": ["gen-1"]}),
    ])
    http = _FakeHTTP({GEN_URL + "gen-1": _gen("gen-1", 0.03)})
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    main(["reconcile", "--log-path", str(log)], http=http)
    out = capsys.readouterr().out
    assert "cycle" in out
    assert "0.0300" in out
    assert "recorded" in out and "authoritative" in out


def test_cli_credits_prints_remaining(capsys, monkeypatch):
    from hamutay.billing import main

    http = _FakeHTTP({"https://openrouter.ai/api/v1/credits":
                      (200, {"data": {"total_credits": 835, "total_usage": 775.944651377}})})
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    main(["credits"], http=http)
    out = capsys.readouterr().out
    assert "59.06" in out
    assert "775.94" in out


def test_cli_requires_api_key(monkeypatch):
    from hamutay.billing import main

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="OPENROUTER_API_KEY"):
        main(["credits"], http=_FakeHTTP({}))
