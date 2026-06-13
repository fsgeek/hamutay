"""Goal 8 matched working-set management panel."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

from hamutay.memory.bridge import JsonDict, LocalMemorySubstrate


EXPERIMENT_ID = "working_set_matched_panel_20260612"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_ENDPOINT = "https://api.deepseek.com"
TRANSIENT_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504, 529}

CONDITIONS = (
    "event_loop_model_controlled",
    "harness_selected_summary",
    "direct_one_shot",
)

RECORD_IDS = {
    "task": "80000000-0000-0000-0000-000000000101",
    "scheduler": "80000000-0000-0000-0000-000000000102",
    "ledger": "80000000-0000-0000-0000-000000000103",
    "substrate": "80000000-0000-0000-0000-000000000104",
    "clock": "80000000-0000-0000-0000-000000000105",
    "distractor": "80000000-0000-0000-0000-000000000199",
}

EXPECTED_FACTS = {
    "scheduler_restart": {
        "evidence": RECORD_IDS["scheduler"],
        "keywords": ["running event", "pending", "restart frontier"],
    },
    "ledger_verified": {
        "evidence": RECORD_IDS["ledger"],
        "keywords": ["ledger", "hash", "verified"],
    },
    "yanantin_not_exercised": {
        "evidence": RECORD_IDS["substrate"],
        "keywords": ["yanantin", "not exercised"],
    },
    "semantic_find_absent": {
        "evidence": RECORD_IDS["substrate"],
        "keywords": ["semantic find", "not exercised"],
    },
    "wall_clock_absent": {
        "evidence": RECORD_IDS["clock"],
        "keywords": ["wall-clock", "des-only"],
    },
}

DISTRACTOR_ID = RECORD_IDS["distractor"]


class PanelFailure(RuntimeError):
    def __init__(
        self,
        *,
        layer: str,
        code: str,
        message: str,
        evidence: JsonDict | None = None,
    ) -> None:
        super().__init__(message)
        self.layer = layer
        self.code = code
        self.message = message
        self.evidence = deepcopy(evidence or {})

    def to_dict(self) -> JsonDict:
        return {
            "layer": self.layer,
            "code": self.code,
            "message": self.message,
            "evidence": deepcopy(self.evidence),
        }


@dataclass(frozen=True)
class ProviderResult:
    parsed: JsonDict
    raw_content: str
    request_payload: JsonDict
    response_payload: JsonDict
    attempts: list[JsonDict]
    elapsed_seconds: float
    usage: JsonDict


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def _approx_tokens(value: Any) -> int:
    text = json.dumps(value, sort_keys=True, default=str)
    return max(1, (len(text) + 3) // 4)


def _extract_openai_content(payload: JsonDict) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise PanelFailure(
            layer="protocol_transport",
            code="missing_openai_content",
            message="OpenAI-compatible response lacked choices[0].message.content",
            evidence={"response_payload": payload},
        ) from exc
    if not isinstance(content, str) or not content.strip():
        raise PanelFailure(
            layer="protocol_transport",
            code="empty_openai_content",
            message="OpenAI-compatible response content was empty",
            evidence={"response_payload": payload},
        )
    return content


def call_openai_compatible_json(
    *,
    api_key: str,
    endpoint: str,
    model: str,
    messages: list[JsonDict],
    timeout_seconds: float = 180.0,
    max_attempts: int = 3,
) -> ProviderResult:
    payload = {
        "model": model,
        "messages": deepcopy(messages),
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    url = endpoint.rstrip("/") + "/chat/completions"
    attempts: list[JsonDict] = []
    started = time.monotonic()
    last_error: JsonDict | None = None
    for attempt_index in range(1, max_attempts + 1):
        attempt_started = time.monotonic()
        try:
            response = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout_seconds,
            )
            attempts.append(
                {
                    "attempt": attempt_index,
                    "elapsed_seconds": time.monotonic() - attempt_started,
                    "status_code": response.status_code,
                    "response_text_prefix": response.text[:4000],
                }
            )
            if (
                response.status_code in TRANSIENT_STATUS_CODES
                and attempt_index < max_attempts
            ):
                time.sleep(min(2 ** (attempt_index - 1), 8))
                continue
            response.raise_for_status()
            response_payload = response.json()
            raw_content = _extract_openai_content(response_payload)
            try:
                parsed = json.loads(raw_content)
            except json.JSONDecodeError as exc:
                raise PanelFailure(
                    layer="protocol_transport",
                    code="json_parse_failed",
                    message="provider content was not valid JSON",
                    evidence={"raw_content": raw_content[:4000], "attempts": attempts},
                ) from exc
            if not isinstance(parsed, dict):
                raise PanelFailure(
                    layer="protocol_transport",
                    code="json_parse_failed",
                    message="provider JSON content was not an object",
                    evidence={"raw_content": raw_content[:4000], "attempts": attempts},
                )
            usage = response_payload.get("usage")
            return ProviderResult(
                parsed=parsed,
                raw_content=raw_content,
                request_payload=payload,
                response_payload=response_payload,
                attempts=attempts,
                elapsed_seconds=time.monotonic() - started,
                usage=deepcopy(usage if isinstance(usage, dict) else {}),
            )
        except httpx.HTTPStatusError as exc:
            last_error = {
                "status_code": exc.response.status_code,
                "response_text": exc.response.text[:4000],
                "attempts": attempts,
            }
            if (
                exc.response.status_code in TRANSIENT_STATUS_CODES
                and attempt_index < max_attempts
            ):
                time.sleep(min(2 ** (attempt_index - 1), 8))
                continue
            break
        except httpx.HTTPError as exc:
            last_error = {"error": str(exc), "attempts": attempts}
            if attempt_index < max_attempts:
                time.sleep(min(2 ** (attempt_index - 1), 8))
                continue
            break
    raise PanelFailure(
        layer="provider",
        code="provider_api_error",
        message="OpenAI-compatible provider call failed",
        evidence=last_error or {"attempts": attempts},
    )


def build_corpus() -> LocalMemorySubstrate:
    substrate = LocalMemorySubstrate()
    records = [
        (
            RECORD_IDS["task"],
            "task",
            {
                "title": "Goal 8 migration readiness note",
                "task": (
                    "Write a migration-readiness note for the Hamutay Goal 8 "
                    "working-set panel."
                ),
                "required_fact_ids": sorted(EXPECTED_FACTS),
            },
        ),
        (
            RECORD_IDS["scheduler"],
            "evidence",
            {
                "fact_id": "scheduler_restart",
                "text": (
                    "Audit/restart boundary testing showed the restart frontier "
                    "can recover a running event back to pending after interruption."
                ),
            },
        ),
        (
            RECORD_IDS["ledger"],
            "evidence",
            {
                "fact_id": "ledger_verified",
                "text": (
                    "The action ledger hash chain verified during the audit "
                    "restart boundary and Goal 6 completion audits."
                ),
            },
        ),
        (
            RECORD_IDS["substrate"],
            "evidence",
            {
                "fact_ids": ["yanantin_not_exercised", "semantic_find_absent"],
                "text": (
                    "Goal 7 used LocalMemorySubstrate as a bounded local "
                    "substitute. Yanantin was not exercised, and semantic find "
                    "was not available in that substitute."
                ),
            },
        ),
        (
            RECORD_IDS["clock"],
            "evidence",
            {
                "fact_id": "wall_clock_absent",
                "text": (
                    "Current scheduler evidence is DES-only. It does not "
                    "establish real wall-clock behavior."
                ),
            },
        ),
        (
            RECORD_IDS["distractor"],
            "distractor",
            {
                "text": (
                    "Unrelated UI palette note: avoid a purple-blue gradient "
                    "and use smaller buttons."
                )
            },
        ),
    ]
    for record_id, record_type, content in records:
        response = substrate.store_episode(
            record_id=UUID(record_id),
            record_type=record_type,
            content=content,
            production={
                "who": {"instance": "goal8-harness"},
                "what": {"artifact": record_type},
                "when": {"cycle": 0},
                "where": {"project": "hamutay"},
            },
            execution_trace={
                "experiment_id": EXPERIMENT_ID,
                "source": "matched_panel_corpus",
            },
        )
        if not response.ok:
            raise RuntimeError(response.to_dict())
    return substrate


def corpus_map(substrate: LocalMemorySubstrate) -> list[JsonDict]:
    return [
        {
            "record_id": record["record_id"],
            "record_type": record["record_type"],
            "content_keys": sorted(record.get("content", {})),
            "preview": json.dumps(record.get("content", {}), sort_keys=True)[:180],
        }
        for record in substrate.snapshot()["records"]
    ]


def final_artifact_schema_instruction() -> str:
    return (
        "Return only one JSON object. Required fields: artifact_title string, "
        "readiness_conclusion string, claims array, declared_losses array, "
        "cited_record_ids array, and working_set_notes string. Each claim must "
        "have fact_id, text, status, and evidence_record_ids. Use fact_id values "
        f"from this set only: {sorted(EXPECTED_FACTS)}."
    )


def selection_messages(corpus: list[JsonDict]) -> list[JsonDict]:
    return [
        {
            "role": "system",
            "content": (
                "You are selecting your own working set for a Hamutay event-loop "
                "wake. Return only JSON. Do not write the final artifact yet."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": (
                        "Choose the minimal recall working set needed to write "
                        "a migration-readiness note for the Goal 8 working-set panel."
                    ),
                    "corpus_map": corpus,
                    "required_output": {
                        "requested_context": [
                            {
                                "tool": "recall",
                                "record_id": "<uuid>",
                            }
                        ],
                        "omitted_record_ids": ["<uuid>"],
                        "declared_losses": ["<loss>"],
                        "selection_rationale": "<why these records>",
                    },
                },
                indent=2,
                sort_keys=True,
            ),
        },
    ]


def final_messages_for_event_loop(
    *,
    recalled_context: list[JsonDict],
    selection: JsonDict,
) -> list[JsonDict]:
    return [
        {"role": "system", "content": final_artifact_schema_instruction()},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "condition": "event_loop_model_controlled",
                    "task": "Write the matched migration-readiness note.",
                    "selection": selection,
                    "recalled_context": recalled_context,
                    "distractor_warning": (
                        "Only use recalled evidence. Do not cite omitted distractors."
                    ),
                },
                indent=2,
                sort_keys=True,
            ),
        },
    ]


def messages_for_harness_summary(summary: JsonDict) -> list[JsonDict]:
    return [
        {"role": "system", "content": final_artifact_schema_instruction()},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "condition": "harness_selected_summary",
                    "task": "Write the matched migration-readiness note.",
                    "harness_summary": summary,
                },
                indent=2,
                sort_keys=True,
            ),
        },
    ]


def messages_for_direct(corpus: list[JsonDict]) -> list[JsonDict]:
    return [
        {"role": "system", "content": final_artifact_schema_instruction()},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "condition": "direct_one_shot",
                    "task": "Write the matched migration-readiness note.",
                    "full_corpus": corpus,
                    "note": "The corpus includes one unrelated distractor record.",
                },
                indent=2,
                sort_keys=True,
            ),
        },
    ]


def harness_summary() -> JsonDict:
    return {
        "summary_type": "harness_selected_relevant_evidence",
        "facts": [
            {
                "fact_id": fact_id,
                "evidence_record_id": data["evidence"],
                "summary": "; ".join(data["keywords"]),
            }
            for fact_id, data in EXPECTED_FACTS.items()
        ],
        "omitted_record_ids": [DISTRACTOR_ID],
        "declared_losses": [
            "Yanantin was not exercised.",
            "Semantic find was not exercised.",
            "Real wall-clock behavior was not established.",
        ],
    }


def dry_provider_response(condition: str, cycle: int) -> JsonDict:
    if condition == "event_loop_model_controlled" and cycle == 1:
        return {
            "requested_context": [
                {"tool": "recall", "record_id": RECORD_IDS["scheduler"]},
                {"tool": "recall", "record_id": RECORD_IDS["ledger"]},
                {"tool": "recall", "record_id": RECORD_IDS["substrate"]},
                {"tool": "recall", "record_id": RECORD_IDS["clock"]},
            ],
            "omitted_record_ids": [DISTRACTOR_ID],
            "declared_losses": ["Direct Yanantin and wall-clock evidence are absent."],
            "selection_rationale": "These records cover required readiness facts.",
        }
    return {
        "artifact_title": "Goal 8 migration readiness note",
        "readiness_conclusion": (
            "Ready for a matched working-set panel with explicit losses."
        ),
        "claims": [
            {
                "fact_id": fact_id,
                "text": "Recovered required fact.",
                "status": "supported",
                "evidence_record_ids": [data["evidence"]],
            }
            for fact_id, data in EXPECTED_FACTS.items()
        ],
        "declared_losses": [
            "Yanantin was not exercised.",
            "Semantic find was not exercised.",
            "Real wall-clock behavior was not established.",
        ],
        "cited_record_ids": sorted({data["evidence"] for data in EXPECTED_FACTS.values()}),
        "working_set_notes": "Distractor was excluded.",
    }


def selection_payload(selection: JsonDict) -> JsonDict:
    """Return the model-authored selection payload, nested or top-level."""

    nested = selection.get("required_output")
    if isinstance(nested, dict):
        return nested
    return selection


def provider_call(
    *,
    condition: str,
    cycle: int,
    messages: list[JsonDict],
    dry_run: bool,
    api_key: str | None,
    endpoint: str,
    model: str,
) -> ProviderResult:
    if dry_run:
        parsed = dry_provider_response(condition, cycle)
        return ProviderResult(
            parsed=parsed,
            raw_content=json.dumps(parsed, sort_keys=True),
            request_payload={"dry_run": True, "messages": deepcopy(messages)},
            response_payload={"dry_run": True},
            attempts=[],
            elapsed_seconds=0.0,
            usage={},
        )
    if not api_key:
        raise PanelFailure(
            layer="provider",
            code="missing_api_key",
            message="DEEPSEEK_API_KEY is required for live Goal 8 run",
        )
    return call_openai_compatible_json(
        api_key=api_key,
        endpoint=endpoint,
        model=model,
        messages=messages,
    )


def resolve_context(
    *,
    substrate: LocalMemorySubstrate,
    requested_context: list[Any],
) -> tuple[list[JsonDict], list[JsonDict]]:
    recalled = []
    classifications = []
    for request in requested_context:
        if not isinstance(request, dict) or request.get("tool") != "recall":
            classifications.append(
                {
                    "request": request,
                    "classification": "malformed_or_unsupported",
                    "result": None,
                }
            )
            continue
        record_id = request.get("record_id")
        if not record_id:
            classifications.append(
                {
                    "request": request,
                    "classification": "malformed_or_unsupported",
                    "result": None,
                }
            )
            continue
        result = substrate.recall(
            record_id=record_id,
            field=request.get("field"),
            reason={
                "experiment_id": EXPERIMENT_ID,
                "condition": "event_loop_model_controlled",
                "request": request,
            },
        )
        result_dict = result.to_dict()
        classifications.append(
            {
                "request": deepcopy(request),
                "classification": (
                    "answerable_by_substrate" if result.ok else "unavailable"
                ),
                "result": result_dict,
            }
        )
        if result.ok:
            recalled.append(
                {
                    "request": deepcopy(request),
                    "content": result_dict.get("content"),
                    "record_id": result_dict.get("record_id"),
                }
            )
    return recalled, classifications


def validate_artifact_output(output: JsonDict) -> JsonDict:
    required = [
        "artifact_title",
        "readiness_conclusion",
        "claims",
        "declared_losses",
        "cited_record_ids",
        "working_set_notes",
    ]
    missing = [field for field in required if field not in output]
    claims = output.get("claims")
    if missing or not isinstance(claims, list):
        return {
            "ok": False,
            "missing_fields": missing,
            "error": "artifact output missing required fields or claims is not an array",
        }
    return {"ok": True, "missing_fields": []}


def score_artifact(output: JsonDict) -> JsonDict:
    validation = validate_artifact_output(output)
    if not validation["ok"]:
        return {
            "scoreable": False,
            "recovered_fact_ids": [],
            "recovery_rate": 0.0,
            "contamination_count": 0,
            "contamination_rate": 1.0,
            "declared_loss_rate": 0.0,
            "artifact_usefulness": "unscoreable",
            "artifact_quality_score": 0.0,
            "validation": validation,
        }
    claims = output.get("claims", [])
    recovered = set()
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        fact_id = str(claim.get("fact_id", ""))
        evidence = {
            str(item) for item in claim.get("evidence_record_ids", [])
        }
        status = str(claim.get("status", "")).lower()
        unsupported = {
            "unsupported",
            "open",
            "unknown",
            "missing",
            "uncertain",
            "not_supported",
        }
        if (
            fact_id in EXPECTED_FACTS
            and status not in unsupported
            and EXPECTED_FACTS[fact_id]["evidence"] in evidence
        ):
            recovered.add(fact_id)
    cited = {str(item) for item in output.get("cited_record_ids", [])}
    text_blob = json.dumps(output, sort_keys=True).lower()
    contamination_count = int(
        DISTRACTOR_ID in cited
        or "palette" in text_blob
        or "purple-blue" in text_blob
    )
    declared_text = " ".join(str(item).lower() for item in output.get("declared_losses", []))
    loss_markers = ["yanantin", "semantic find", "wall-clock"]
    declared_loss_count = sum(1 for marker in loss_markers if marker in declared_text)
    artifact_quality_score = 0.0
    if output.get("readiness_conclusion"):
        artifact_quality_score += 0.25
    artifact_quality_score += min(len(recovered), len(EXPECTED_FACTS)) / len(EXPECTED_FACTS) * 0.5
    if contamination_count == 0:
        artifact_quality_score += 0.15
    if declared_loss_count:
        artifact_quality_score += 0.10
    recovery_rate = len(recovered) / len(EXPECTED_FACTS)
    return {
        "scoreable": True,
        "recovered_fact_ids": sorted(recovered),
        "missing_fact_ids": sorted(set(EXPECTED_FACTS) - recovered),
        "recovery_rate": recovery_rate,
        "contamination_count": contamination_count,
        "contamination_rate": contamination_count / 1,
        "declared_loss_rate": declared_loss_count / len(loss_markers),
        "artifact_usefulness": (
            "useful" if artifact_quality_score >= 0.7 else "partial"
        ),
        "artifact_quality_score": round(artifact_quality_score, 4),
        "validation": validation,
    }


def working_set_score(row: JsonDict) -> float:
    score = row["artifact_score"]
    context = row["context_accounting"]
    provenance_bonus = 1.0 if context.get("recall_provenance") else 0.5
    contamination_avoidance = 1.0 - score["contamination_rate"]
    return round(
        (
            score["recovery_rate"] * 0.45
            + contamination_avoidance * 0.20
            + score["declared_loss_rate"] * 0.20
            + provenance_bonus * 0.15
        ),
        4,
    )


def request_tokens_from_messages(messages: list[JsonDict]) -> int:
    return _approx_tokens(messages)


def usage_tokens(provider: ProviderResult, messages: list[JsonDict]) -> JsonDict:
    usage = provider.usage or {}
    prompt = usage.get("prompt_tokens") or usage.get("input_tokens")
    completion = usage.get("completion_tokens") or usage.get("output_tokens")
    return {
        "prompt_tokens": int(prompt) if isinstance(prompt, int) else request_tokens_from_messages(messages),
        "completion_tokens": int(completion) if isinstance(completion, int) else _approx_tokens(provider.parsed),
        "source": "provider_usage" if prompt or completion else "approx_char_div_4",
    }


def write_cycle(row_root: Path, cycle: int, provider: ProviderResult) -> None:
    _write_json(
        row_root / f"cycle_{cycle:02d}.json",
        {
            "parsed": provider.parsed,
            "raw_content": provider.raw_content,
            "request_payload": provider.request_payload,
            "response_payload": provider.response_payload,
            "attempts": provider.attempts,
            "elapsed_seconds": provider.elapsed_seconds,
            "usage": provider.usage,
        },
    )


def run_event_loop_condition(
    *,
    output_root: Path,
    dry_run: bool,
    api_key: str | None,
    endpoint: str,
    model: str,
) -> JsonDict:
    condition = "event_loop_model_controlled"
    row_root = output_root / "rows" / condition
    row_root.mkdir(parents=True, exist_ok=True)
    substrate = build_corpus()
    map_payload = corpus_map(substrate)
    messages1 = selection_messages(map_payload)
    selection = provider_call(
        condition=condition,
        cycle=1,
        messages=messages1,
        dry_run=dry_run,
        api_key=api_key,
        endpoint=endpoint,
        model=model,
    )
    write_cycle(row_root, 1, selection)
    selected = selection_payload(selection.parsed)
    requested_context = selected.get("requested_context", [])
    recalled_context, request_classifications = resolve_context(
        substrate=substrate,
        requested_context=requested_context if isinstance(requested_context, list) else [],
    )
    messages2 = final_messages_for_event_loop(
        recalled_context=recalled_context,
        selection=selected,
    )
    final = provider_call(
        condition=condition,
        cycle=2,
        messages=messages2,
        dry_run=dry_run,
        api_key=api_key,
        endpoint=endpoint,
        model=model,
    )
    write_cycle(row_root, 2, final)
    usage1 = usage_tokens(selection, messages1)
    usage2 = usage_tokens(final, messages2)
    context_accounting = {
        "condition": condition,
        "live_context": {
            "cycle_1": {"messages": messages1, "token_count": usage1["prompt_tokens"]},
            "cycle_2": {"messages": messages2, "token_count": usage2["prompt_tokens"]},
        },
        "carried_state": selection.parsed,
        "recalled_context": recalled_context,
        "omitted_context": selected.get("omitted_record_ids", []),
        "declared_losses": final.parsed.get("declared_losses", []),
        "token_use": {
            "prompt_tokens": usage1["prompt_tokens"] + usage2["prompt_tokens"],
            "peak_prompt_tokens": max(usage1["prompt_tokens"], usage2["prompt_tokens"]),
            "completion_tokens": usage1["completion_tokens"] + usage2["completion_tokens"],
            "source": [usage1["source"], usage2["source"]],
        },
        "recall_provenance": substrate.retrieval_log().data["retrievals"],
        "truncation_metadata": [
            entry
            for entry in substrate.retrieval_log().data["retrievals"]
            if entry.get("truncated") or entry.get("omitted")
        ],
        "request_classifications": request_classifications,
    }
    artifact_score = score_artifact(final.parsed)
    row = {
        "condition": condition,
        "artifact": final.parsed,
        "artifact_score": artifact_score,
        "context_accounting": context_accounting,
        "memory_snapshot": substrate.snapshot(),
    }
    row["working_set_score"] = working_set_score(row)
    _write_json(row_root / "context_accounting.json", context_accounting)
    _write_json(row_root / "memory_snapshot.json", substrate.snapshot())
    _write_json(row_root / "row_result.json", row)
    return row


def run_summary_condition(
    *,
    output_root: Path,
    dry_run: bool,
    api_key: str | None,
    endpoint: str,
    model: str,
) -> JsonDict:
    condition = "harness_selected_summary"
    row_root = output_root / "rows" / condition
    row_root.mkdir(parents=True, exist_ok=True)
    substrate = build_corpus()
    summary = harness_summary()
    messages = messages_for_harness_summary(summary)
    final = provider_call(
        condition=condition,
        cycle=1,
        messages=messages,
        dry_run=dry_run,
        api_key=api_key,
        endpoint=endpoint,
        model=model,
    )
    write_cycle(row_root, 1, final)
    usage = usage_tokens(final, messages)
    context_accounting = {
        "condition": condition,
        "live_context": {"messages": messages, "token_count": usage["prompt_tokens"]},
        "carried_state": {},
        "recalled_context": [],
        "omitted_context": summary["omitted_record_ids"],
        "declared_losses": final.parsed.get("declared_losses", []),
        "token_use": {
            "prompt_tokens": usage["prompt_tokens"],
            "peak_prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "source": usage["source"],
        },
        "recall_provenance": [],
        "truncation_metadata": [],
        "request_classifications": [],
    }
    artifact_score = score_artifact(final.parsed)
    row = {
        "condition": condition,
        "artifact": final.parsed,
        "artifact_score": artifact_score,
        "context_accounting": context_accounting,
        "memory_snapshot": substrate.snapshot(),
    }
    row["working_set_score"] = working_set_score(row)
    _write_json(row_root / "context_accounting.json", context_accounting)
    _write_json(row_root / "memory_snapshot.json", substrate.snapshot())
    _write_json(row_root / "row_result.json", row)
    return row


def run_direct_condition(
    *,
    output_root: Path,
    dry_run: bool,
    api_key: str | None,
    endpoint: str,
    model: str,
) -> JsonDict:
    condition = "direct_one_shot"
    row_root = output_root / "rows" / condition
    row_root.mkdir(parents=True, exist_ok=True)
    substrate = build_corpus()
    full_corpus = substrate.snapshot()["records"]
    messages = messages_for_direct(full_corpus)
    final = provider_call(
        condition=condition,
        cycle=1,
        messages=messages,
        dry_run=dry_run,
        api_key=api_key,
        endpoint=endpoint,
        model=model,
    )
    write_cycle(row_root, 1, final)
    usage = usage_tokens(final, messages)
    context_accounting = {
        "condition": condition,
        "live_context": {"messages": messages, "token_count": usage["prompt_tokens"]},
        "carried_state": {},
        "recalled_context": full_corpus,
        "omitted_context": [],
        "declared_losses": final.parsed.get("declared_losses", []),
        "token_use": {
            "prompt_tokens": usage["prompt_tokens"],
            "peak_prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "source": usage["source"],
        },
        "recall_provenance": [],
        "truncation_metadata": [],
        "request_classifications": [],
    }
    artifact_score = score_artifact(final.parsed)
    row = {
        "condition": condition,
        "artifact": final.parsed,
        "artifact_score": artifact_score,
        "context_accounting": context_accounting,
        "memory_snapshot": substrate.snapshot(),
    }
    row["working_set_score"] = working_set_score(row)
    _write_json(row_root / "context_accounting.json", context_accounting)
    _write_json(row_root / "memory_snapshot.json", substrate.snapshot())
    _write_json(row_root / "row_result.json", row)
    return row


def classify_panel(rows: list[JsonDict]) -> JsonDict:
    by_condition = {row["condition"]: row for row in rows}
    event = by_condition["event_loop_model_controlled"]
    controls = [
        by_condition["harness_selected_summary"],
        by_condition["direct_one_shot"],
    ]
    best_control_working = max(row["working_set_score"] for row in controls)
    best_control_quality = max(
        row["artifact_score"]["artifact_quality_score"] for row in controls
    )
    direct_prompt_tokens = by_condition["direct_one_shot"]["context_accounting"][
        "token_use"
    ]["peak_prompt_tokens"]
    event_prompt_tokens = event["context_accounting"]["token_use"]["prompt_tokens"]
    event_peak_prompt_tokens = event["context_accounting"]["token_use"][
        "peak_prompt_tokens"
    ]
    noninferior_margin = 0.10
    working_set_relation = (
        "better"
        if event["working_set_score"] > best_control_working + noninferior_margin
        else "non_inferior"
        if event["working_set_score"] >= best_control_working - noninferior_margin
        else "worse"
    )
    artifact_relation = (
        "better"
        if event["artifact_score"]["artifact_quality_score"]
        > best_control_quality + noninferior_margin
        else "non_inferior"
        if event["artifact_score"]["artifact_quality_score"]
        >= best_control_quality - noninferior_margin
        else "worse"
    )
    token_relation = (
        "less_than_direct"
        if event_peak_prompt_tokens < direct_prompt_tokens
        else "not_less_than_direct"
    )
    classification = (
        "survived"
        if working_set_relation in {"better", "non_inferior"}
        and token_relation == "less_than_direct"
        else "falsified"
    )
    return {
        "classification": classification,
        "working_set_relation": working_set_relation,
        "artifact_quality_relation": artifact_relation,
        "token_relation_to_direct": token_relation,
        "event_prompt_tokens": event_prompt_tokens,
        "event_peak_prompt_tokens": event_peak_prompt_tokens,
        "direct_prompt_tokens": direct_prompt_tokens,
        "best_control_working_set_score": best_control_working,
        "event_working_set_score": event["working_set_score"],
        "best_control_artifact_quality_score": best_control_quality,
        "event_artifact_quality_score": event["artifact_score"]["artifact_quality_score"],
    }


def write_analysis(output_root: Path, results: JsonDict) -> None:
    rows = results["rows"]
    comparison = results["comparison"]
    lines = [
        "# Working-Set Matched Panel Analysis",
        "",
        f"Experiment ID: `{EXPERIMENT_ID}`",
        "",
        "## Result",
        "",
        f"- Classification: `{results['classification']}`",
        f"- Working-set relation: `{comparison['working_set_relation']}`",
        f"- Artifact-quality relation: `{comparison['artifact_quality_relation']}`",
        f"- Token relation to direct: `{comparison['token_relation_to_direct']}`",
        f"- Decision: {results['summary']['decision']}",
        "",
        "## Rows",
        "",
        "| Condition | Working-set score | Artifact quality | Recovery | Contamination | Declared losses | Peak prompt tokens | Total prompt tokens | Artifact |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        score = row["artifact_score"]
        token_use = row["context_accounting"]["token_use"]
        lines.append(
            "| {condition} | {working:.4f} | {quality:.4f} | {recovery:.4f} | "
            "{contam:.4f} | {loss:.4f} | {peak_tokens} | {tokens} | `{artifact}` |".format(
                condition=row["condition"],
                working=row["working_set_score"],
                quality=score["artifact_quality_score"],
                recovery=score["recovery_rate"],
                contam=score["contamination_rate"],
                loss=score["declared_loss_rate"],
                peak_tokens=token_use["peak_prompt_tokens"],
                tokens=token_use["prompt_tokens"],
                artifact=score["artifact_usefulness"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Working-set benefit is scored separately from artifact quality. "
            "The working-set score combines evidence recovery, contamination "
            "avoidance, declared-loss preservation, and provenance. Artifact "
            "quality separately scores responsiveness, supported claims, and "
            "readiness conclusion quality.",
            "",
            "## Artifact Trail",
            "",
            "- `PRE_REGISTRATION.md`, `matrix.json`, `budget.json`, and `failure_taxonomy.json` preserve the preregistered frame.",
            "- `rows/<condition>/cycle_*.json` preserves raw provider requests and responses.",
            "- `rows/<condition>/context_accounting.json` preserves context accounting, recall provenance, declared losses, and token use.",
            "- `rows/<condition>/row_result.json` preserves recovery, contamination, artifact usefulness, and working-set scoring.",
            "- `results.json` preserves the cross-condition comparison.",
        ]
    )
    output_root.joinpath("analysis.md").write_text("\n".join(lines) + "\n")


def run_panel(
    *,
    output_root: Path,
    dry_run: bool,
    api_key: str | None,
    endpoint: str,
    model: str,
    overwrite: bool,
) -> JsonDict:
    if output_root.exists() and overwrite:
        for child in output_root.iterdir():
            if child.name in {
                "PRE_REGISTRATION.md",
                "matrix.json",
                "budget.json",
                "failure_taxonomy.json",
                "run.py",
            }:
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    output_root.mkdir(parents=True, exist_ok=True)
    rows = [
        run_event_loop_condition(
            output_root=output_root,
            dry_run=dry_run,
            api_key=api_key,
            endpoint=endpoint,
            model=model,
        ),
        run_summary_condition(
            output_root=output_root,
            dry_run=dry_run,
            api_key=api_key,
            endpoint=endpoint,
            model=model,
        ),
        run_direct_condition(
            output_root=output_root,
            dry_run=dry_run,
            api_key=api_key,
            endpoint=endpoint,
            model=model,
        ),
    ]
    comparison = classify_panel(rows)
    results = {
        "schema_version": "hamutay.working_set_matched_panel_results.v1",
        "experiment_id": EXPERIMENT_ID,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "live_model_calls": not dry_run,
        "classification": comparison["classification"],
        "comparison": comparison,
        "rows": rows,
        "summary": {
            "decision": (
                "Event-loop working-set behavior was non-inferior or better "
                "than controls while using less prompt context than direct."
                if comparison["classification"] == "survived"
                else "Event-loop working-set behavior did not meet the preregistered matched-panel threshold."
            )
        },
    }
    _write_json(output_root / "results.json", results)
    write_analysis(output_root, results)
    return results


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--endpoint", default=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_ENDPOINT))
    parser.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL))
    parser.add_argument("--api-key", default=os.environ.get("DEEPSEEK_API_KEY"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    results = run_panel(
        output_root=Path(args.output_root),
        dry_run=args.dry_run,
        api_key=args.api_key,
        endpoint=args.endpoint,
        model=args.model,
        overwrite=args.overwrite,
    )
    print(json.dumps(results["comparison"], indent=2, sort_keys=True))
    return 0 if results["classification"] in {"survived", "falsified"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
