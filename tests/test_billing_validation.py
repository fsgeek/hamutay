"""Independent contract and adversarial tests for :mod:`hamutay.billing`."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from hamutay.billing import OpenRouterBilling, main, reconcile_log, summarize


class RecordingHTTP:
    def __init__(self, responses=None):
        self.responses = dict(responses or {})
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url, headers):
        self.calls.append((url, headers))
        return self.responses.get(url, (404, {"error": "not visible"}))


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def record(cycle: int, generation_ids, **usage_overrides) -> dict:
    usage = {
        "generation_ids": generation_ids,
        "input_tokens": 11,
        "output_tokens": 7,
        "cache_read_input_tokens": 3,
        "cost_usd": 0.25,
        **usage_overrides,
    }
    return {
        "cycle": cycle,
        "record_id": f"record-{cycle}",
        "timestamp": f"2026-08-29T12:00:0{cycle}+00:00",
        "usage": usage,
    }


def generation(generation_id: str, usage=0.25) -> dict:
    return {
        "id": generation_id,
        "usage": usage,
        "model": "vendor/model",
        "native_tokens_prompt": 11,
        "native_tokens_completion": 7,
        "native_tokens_cached": 3,
        "native_tokens_reasoning": 2,
        "provider_responses": [{"provider_name": "provider"}],
    }


def sidecar_entry(generation_id: str, usage_usd, *, cycle: int = 1) -> dict:
    return {
        "generation_id": generation_id,
        "cycle": cycle,
        "record_id": f"record-{cycle}",
        "fetched_at": "2026-08-29T12:00:00+00:00",
        "usage_usd": usage_usd,
        "model": "vendor/model",
        "provider": "provider",
        "native_tokens_prompt": 11,
        "native_tokens_completion": 7,
        "native_tokens_cached": 3,
        "native_tokens_reasoning": 2,
        "raw": generation(generation_id, usage_usd),
    }


def test_credits_non_200_raises_runtime_error():
    http = RecordingHTTP({
        "https://router.invalid/api/credits": (503, {"error": "maintenance"}),
    })
    billing = OpenRouterBilling("secret", http=http, base_url="https://router.invalid/api/")

    with pytest.raises(RuntimeError, match="503"):
        billing.credits()


@pytest.mark.parametrize("data", [None, [], "generation"])
def test_generation_200_requires_data_dict(data):
    http = RecordingHTTP({
        "https://router.invalid/generation?id=gen-1": (200, {"data": data}),
    })
    billing = OpenRouterBilling("secret", http=http, base_url="https://router.invalid")

    with pytest.raises(RuntimeError, match="no data"):
        billing.generation("gen-1")


def test_generation_id_is_url_encoded_as_one_query_value():
    requested_id = "gen/space ?&=unicode-λ"

    def successful_get(url, headers):
        assert headers == {"Authorization": "Bearer secret"}
        assert parse_qs(urlsplit(url).query) == {"id": [requested_id]}
        return 200, {"data": generation(requested_id)}

    billing = OpenRouterBilling("secret", http=successful_get)
    assert billing.generation(requested_id)["id"] == requested_id


def test_null_usage_record_is_unreconcilable_without_network_access(tmp_path):
    log = tmp_path / "session.jsonl"
    write_jsonl(log, [{
        "cycle": 1,
        "record_id": "record-1",
        "timestamp": "2026-08-29T12:00:01+00:00",
        "usage": None,
    }])
    http = RecordingHTTP()

    rows = reconcile_log(str(log), OpenRouterBilling("secret", http=http))

    assert rows == [{
        "cycle": 1,
        "record_id": "record-1",
        "timestamp": "2026-08-29T12:00:01+00:00",
        "input_tokens": None,
        "output_tokens": None,
        "cache_read_input_tokens": None,
        "recorded_cost_usd": None,
        "cost_turns_unreported": None,
        "generations_total": 0,
        "generations_fetched": 0,
        "generations_pending": 0,
        "authoritative_cost_usd": None,
        "unreconcilable": True,
    }]
    assert http.calls == []


@pytest.mark.parametrize(
    "generation_ids",
    [[123], ["gen-ok", None], [True]],
    ids=["integer", "mixed-none", "boolean"],
)
def test_non_string_generation_ids_are_rejected_before_fetch(tmp_path, generation_ids):
    log = tmp_path / "session.jsonl"
    write_jsonl(log, [record(1, generation_ids)])
    http = RecordingHTTP()

    with pytest.raises(ValueError, match="generation_ids"):
        reconcile_log(str(log), OpenRouterBilling("secret", http=http))

    assert http.calls == []


def test_blank_sidecar_lines_are_ignored(tmp_path):
    log = tmp_path / "session.jsonl"
    write_jsonl(log, [record(1, ["gen-1"])])
    sidecar = Path(str(log) + ".billing.jsonl")
    sidecar.write_text("\n  \n" + json.dumps(sidecar_entry("gen-1", 0.25)) + "\n\n")
    http = RecordingHTTP()

    rows = reconcile_log(str(log), OpenRouterBilling("secret", http=http))

    assert rows[0]["authoritative_cost_usd"] == pytest.approx(0.25)
    assert http.calls == []


def test_malformed_sidecar_line_is_not_silently_ignored(tmp_path):
    log = tmp_path / "session.jsonl"
    write_jsonl(log, [record(1, ["gen-1"])])
    Path(str(log) + ".billing.jsonl").write_text('{"generation_id": "gen-1"\n')

    with pytest.raises(json.JSONDecodeError):
        reconcile_log(str(log), OpenRouterBilling("secret", http=RecordingHTTP()))


def test_duplicate_generation_ids_in_sidecar_are_rejected_as_ambiguous(tmp_path):
    log = tmp_path / "session.jsonl"
    write_jsonl(log, [record(1, ["gen-1"])])
    sidecar = Path(str(log) + ".billing.jsonl")
    sidecar.write_text(
        json.dumps(sidecar_entry("gen-1", 0.10))
        + "\n"
        + json.dumps(sidecar_entry("gen-1", 0.90))
        + "\n"
    )

    with pytest.raises(RuntimeError, match="duplicate.*gen-1"):
        reconcile_log(str(log), OpenRouterBilling("secret", http=RecordingHTTP()))


@pytest.mark.parametrize("usage_usd", [None, "0.25", True], ids=["null", "string", "bool"])
def test_sidecar_rejects_non_numeric_usage_usd(tmp_path, usage_usd):
    log = tmp_path / "session.jsonl"
    write_jsonl(log, [record(1, ["gen-1"])])
    Path(str(log) + ".billing.jsonl").write_text(
        json.dumps(sidecar_entry("gen-1", usage_usd)) + "\n"
    )

    with pytest.raises(RuntimeError, match="usage_usd"):
        reconcile_log(str(log), OpenRouterBilling("secret", http=RecordingHTTP()))


def test_fetched_generation_without_usage_is_not_cached_or_reported_complete(tmp_path):
    log = tmp_path / "session.jsonl"
    write_jsonl(log, [record(1, ["gen-1"])])
    incomplete_generation = generation("gen-1")
    incomplete_generation.pop("usage")
    http = RecordingHTTP({
        "https://openrouter.ai/api/v1/generation?id=gen-1": (
            200,
            {"data": incomplete_generation},
        ),
    })

    with pytest.raises(RuntimeError, match="usage"):
        reconcile_log(str(log), OpenRouterBilling("secret", http=http))

    assert not Path(str(log) + ".billing.jsonl").exists()


def test_same_generation_in_two_records_is_fetched_and_charged_once(tmp_path):
    log = tmp_path / "session.jsonl"
    write_jsonl(log, [record(1, ["gen-shared"]), record(2, ["gen-shared"])])
    url = "https://openrouter.ai/api/v1/generation?id=gen-shared"
    http = RecordingHTTP({url: (200, {"data": generation("gen-shared", 0.25)})})

    rows = reconcile_log(str(log), OpenRouterBilling("secret", http=http))

    assert [call[0] for call in http.calls] == [url]
    assert summarize(rows)["authoritative_cost_usd_complete"] == pytest.approx(0.25)


def test_404_is_not_cached_and_is_retried_on_later_run(tmp_path):
    log = tmp_path / "session.jsonl"
    write_jsonl(log, [record(1, ["gen-later"])])
    url = "https://openrouter.ai/api/v1/generation?id=gen-later"
    http = RecordingHTTP()
    billing = OpenRouterBilling("secret", http=http)

    first_rows = reconcile_log(str(log), billing)
    assert first_rows[0]["generations_pending"] == 1
    assert not Path(str(log) + ".billing.jsonl").exists()

    http.responses[url] = (200, {"data": generation("gen-later", 0.25)})
    second_rows = reconcile_log(str(log), billing)
    assert [call[0] for call in http.calls] == [url, url]
    assert second_rows[0]["authoritative_cost_usd"] == pytest.approx(0.25)


def test_run_with_no_new_fetch_does_not_touch_sidecar(tmp_path):
    log = tmp_path / "session.jsonl"
    write_jsonl(log, [record(1, ["gen-1"])])
    sidecar = Path(str(log) + ".billing.jsonl")
    original = json.dumps(sidecar_entry("gen-1", 0.25)) + "\n"
    sidecar.write_text(original)
    fixed_ns = 1_700_000_000_123_456_789
    os.utime(sidecar, ns=(fixed_ns, fixed_ns))

    rows = reconcile_log(str(log), OpenRouterBilling("secret", http=RecordingHTTP()))

    assert rows[0]["authoritative_cost_usd"] == pytest.approx(0.25)
    assert sidecar.read_text() == original
    assert sidecar.stat().st_mtime_ns == fixed_ns


def test_summarize_keeps_pending_partial_out_of_complete_total():
    rows = [
        {
            "unreconcilable": False,
            "recorded_cost_usd": 0.40,
            "generations_pending": 0,
            "authoritative_cost_usd": 0.40,
        },
        {
            "unreconcilable": False,
            "recorded_cost_usd": 0.75,
            "generations_pending": 1,
            "authoritative_cost_usd": None,
            "authoritative_cost_usd_partial": 0.70,
        },
    ]

    totals = summarize(rows)

    assert totals["authoritative_cost_usd_complete"] == pytest.approx(0.40)
    assert totals["authoritative_cost_usd_partial"] == pytest.approx(0.70)


def test_cli_generation_and_reconcile_json(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("OPENROUTER_API_KEY", "secret")
    generation_url = "https://openrouter.ai/api/v1/generation?id=gen-1"
    http = RecordingHTTP({
        generation_url: (200, {"data": generation("gen-1", 0.25)}),
    })

    main(["generation", "gen-1"], http=http)
    assert json.loads(capsys.readouterr().out)["id"] == "gen-1"

    log = tmp_path / "session.jsonl"
    write_jsonl(log, [record(1, ["gen-1"])])
    main(["reconcile", "--log-path", str(log), "--json"], http=http)
    output_rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert output_rows[0]["authoritative_cost_usd"] == pytest.approx(0.25)


def test_cli_without_api_key_mentions_required_variable(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(SystemExit, match="OPENROUTER_API_KEY"):
        main(["credits"], http=RecordingHTTP())
