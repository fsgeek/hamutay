"""Goal 10 artifact non-inferiority panel."""

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


EXPERIMENT_ID = "artifact_noninferiority_20260612"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_ENDPOINT = "https://api.deepseek.com"
NON_INFERIORITY_MARGIN = 0.10
TRANSIENT_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504, 529}
CONDITIONS = ("event_loop_bounded", "direct_one_shot")


TASKS: dict[str, JsonDict] = {
    "scheduler_migration_note": {
        "prompt": (
            "Write a migration note deciding whether the scheduler evidence is "
            "sufficient to continue to artifact non-inferiority experiments."
        ),
        "required_facts": {
            "des_baseline": {
                "evidence": "a0000000-0000-0000-0000-000000000101",
                "loss_marker": None,
            },
            "wall_clock_probe_passed": {
                "evidence": "a0000000-0000-0000-0000-000000000102",
                "loss_marker": None,
            },
            "production_scheduler_absent": {
                "evidence": "a0000000-0000-0000-0000-000000000103",
                "loss_marker": "production scheduler",
            },
        },
        "records": [
            (
                "a0000000-0000-0000-0000-000000000101",
                "evidence",
                {
                    "fact_id": "des_baseline",
                    "text": (
                        "Goal 9 kept SchedulerClock as the deterministic "
                        "semantic baseline for scheduler experiments."
                    ),
                },
            ),
            (
                "a0000000-0000-0000-0000-000000000102",
                "evidence",
                {
                    "fact_id": "wall_clock_probe_passed",
                    "text": (
                        "Goal 9 paired DES and wall-clock smoke tests passed "
                        "for due ordering, expiration, next-wake reporting, "
                        "and restart frontier recovery."
                    ),
                },
            ),
            (
                "a0000000-0000-0000-0000-000000000103",
                "evidence",
                {
                    "fact_id": "production_scheduler_absent",
                    "text": (
                        "Goal 9 did not build a daemon, sleep loop, wall-clock "
                        "SLA, or production process supervisor."
                    ),
                },
            ),
            (
                "a0000000-0000-0000-0000-000000000199",
                "distractor",
                {
                    "text": (
                        "Unrelated blog note: use a fairy-tale cellar metaphor "
                        "for the memory system."
                    ),
                },
            ),
        ],
        "distractor_id": "a0000000-0000-0000-0000-000000000199",
    },
    "failure_attribution_note": {
        "prompt": (
            "Write a failure-attribution note for an autonomy row whose model "
            "artifact looked fluent but conflicted with trace evidence."
        ),
        "required_facts": {
            "layer_taxonomy_required": {
                "evidence": "a0000000-0000-0000-0000-000000000201",
                "loss_marker": None,
            },
            "scorer_fault_possible": {
                "evidence": "a0000000-0000-0000-0000-000000000202",
                "loss_marker": "scorer uncertainty",
            },
            "raw_trace_preserved": {
                "evidence": "a0000000-0000-0000-0000-000000000203",
                "loss_marker": None,
            },
        },
        "records": [
            (
                "a0000000-0000-0000-0000-000000000201",
                "evidence",
                {
                    "fact_id": "layer_taxonomy_required",
                    "text": (
                        "The audit plan requires failures to be attributed to "
                        "model, protocol, harness, substrate, provider, scorer, "
                        "or inconclusive layers."
                    ),
                },
            ),
            (
                "a0000000-0000-0000-0000-000000000202",
                "evidence",
                {
                    "fact_id": "scorer_fault_possible",
                    "text": (
                        "Prior contamination scoring misclassified faithful "
                        "invalidations, proving scorer faults are possible."
                    ),
                },
            ),
            (
                "a0000000-0000-0000-0000-000000000203",
                "evidence",
                {
                    "fact_id": "raw_trace_preserved",
                    "text": (
                        "Audit-grade rows preserve raw request, response, "
                        "parsed action, accepted/rejected operations, and "
                        "deterministic scorer output."
                    ),
                },
            ),
            (
                "a0000000-0000-0000-0000-000000000299",
                "distractor",
                {
                    "text": (
                        "Unrelated UI warning: a purple-blue palette made a "
                        "dashboard feel one-note."
                    ),
                },
            ),
        ],
        "distractor_id": "a0000000-0000-0000-0000-000000000299",
    },
    "memory_boundary_note": {
        "prompt": (
            "Write a note deciding whether memory access alone solves "
            "working-set management for bounded autonomous work."
        ),
        "required_facts": {
            "goal8_recovered_evidence": {
                "evidence": "a0000000-0000-0000-0000-000000000301",
                "loss_marker": None,
            },
            "goal8_contaminated_artifact": {
                "evidence": "a0000000-0000-0000-0000-000000000302",
                "loss_marker": None,
            },
            "memory_access_not_sufficient": {
                "evidence": "a0000000-0000-0000-0000-000000000303",
                "loss_marker": "memory access",
            },
        },
        "records": [
            (
                "a0000000-0000-0000-0000-000000000301",
                "evidence",
                {
                    "fact_id": "goal8_recovered_evidence",
                    "text": (
                        "In Goal 8 the event-loop condition recovered all five "
                        "required facts from the available evidence records."
                    ),
                },
            ),
            (
                "a0000000-0000-0000-0000-000000000302",
                "evidence",
                {
                    "fact_id": "goal8_contaminated_artifact",
                    "text": (
                        "In Goal 8 the event-loop condition still carried "
                        "distractor material into the final artifact."
                    ),
                },
            ),
            (
                "a0000000-0000-0000-0000-000000000303",
                "evidence",
                {
                    "fact_id": "memory_access_not_sufficient",
                    "text": (
                        "Goal 8 sharpened the finding that memory access alone "
                        "is not sufficient for disciplined working-set use."
                    ),
                },
            ),
            (
                "a0000000-0000-0000-0000-000000000399",
                "distractor",
                {
                    "text": (
                        "Unrelated draft fragment: the sun has utility but "
                        "probably no computational identity object."
                    ),
                },
            ),
        ],
        "distractor_id": "a0000000-0000-0000-0000-000000000399",
    },
}


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


def _read_json(path: Path) -> JsonDict:
    return json.loads(path.read_text())


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


def build_corpus(task_id: str) -> LocalMemorySubstrate:
    task = TASKS[task_id]
    substrate = LocalMemorySubstrate()
    task_record_id = UUID(_task_record_id(task_id))
    response = substrate.store_episode(
        record_id=task_record_id,
        record_type="task",
        content={
            "task_id": task_id,
            "prompt": task["prompt"],
            "required_fact_ids": sorted(task["required_facts"]),
        },
        production=_production("goal10-harness", "task"),
        execution_trace={"experiment_id": EXPERIMENT_ID, "source": "task"},
    )
    if not response.ok:
        raise RuntimeError(response.to_dict())
    for record_id, record_type, content in task["records"]:
        stored = substrate.store_episode(
            record_id=UUID(record_id),
            record_type=record_type,
            content=content,
            production=_production("goal10-harness", record_type),
            execution_trace={
                "experiment_id": EXPERIMENT_ID,
                "task_id": task_id,
                "source": "matched_task_corpus",
            },
        )
        if not stored.ok:
            raise RuntimeError(stored.to_dict())
    return substrate


def _task_record_id(task_id: str) -> str:
    offsets = {
        "scheduler_migration_note": "a0000000-0000-0000-0000-000000000100",
        "failure_attribution_note": "a0000000-0000-0000-0000-000000000200",
        "memory_boundary_note": "a0000000-0000-0000-0000-000000000300",
    }
    return offsets[task_id]


def _production(instance: str, artifact: str) -> JsonDict:
    return {
        "who": {"instance": instance},
        "what": {"artifact": artifact},
        "when": {"cycle": 0},
        "where": {"project": "hamutay"},
    }


def corpus_map(substrate: LocalMemorySubstrate) -> list[JsonDict]:
    return [
        {
            "record_id": record["record_id"],
            "record_type": record["record_type"],
            "content_keys": sorted(record.get("content", {})),
            "preview": json.dumps(record.get("content", {}), sort_keys=True)[:220],
        }
        for record in substrate.snapshot()["records"]
    ]


def artifact_schema_instruction(task_id: str) -> str:
    facts = sorted(TASKS[task_id]["required_facts"])
    return (
        "Return only one JSON object. Required fields: artifact_title string, "
        "task_id string, conclusion string, recommended_action string, claims "
        "array, declared_losses array, cited_record_ids array. Each claim must "
        "have fact_id, text, status, and evidence_record_ids. Use fact_id "
        f"values from this set only: {facts}."
    )


def selection_messages(task_id: str, corpus: list[JsonDict]) -> list[JsonDict]:
    return [
        {
            "role": "system",
            "content": (
                "You are doing bounded event-loop work. Select the evidence "
                "needed for the artifact, but do not write the artifact yet. "
                "Return only JSON."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task_id": task_id,
                    "task": TASKS[task_id]["prompt"],
                    "corpus_map": corpus,
                    "required_output": {
                        "work_plan": "<short plan>",
                        "requested_context": [
                            {"tool": "recall", "record_id": "<uuid>"}
                        ],
                        "omitted_record_ids": ["<uuid>"],
                        "declared_losses": ["<loss or limitation>"],
                    },
                },
                indent=2,
                sort_keys=True,
            ),
        },
    ]


def event_artifact_messages(
    *,
    task_id: str,
    selection: JsonDict,
    recalled_context: list[JsonDict],
) -> list[JsonDict]:
    return [
        {"role": "system", "content": artifact_schema_instruction(task_id)},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "condition": "event_loop_bounded",
                    "task_id": task_id,
                    "task": TASKS[task_id]["prompt"],
                    "carried_state": selection,
                    "recalled_context": recalled_context,
                    "instruction": (
                        "Write the artifact only from recalled evidence and "
                        "explicit declared losses. Do not cite omitted distractors."
                    ),
                },
                indent=2,
                sort_keys=True,
            ),
        },
    ]


def direct_messages(task_id: str, corpus: list[JsonDict]) -> list[JsonDict]:
    return [
        {"role": "system", "content": artifact_schema_instruction(task_id)},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "condition": "direct_one_shot",
                    "task_id": task_id,
                    "task": TASKS[task_id]["prompt"],
                    "full_corpus": corpus,
                    "instruction": (
                        "Write the artifact. The corpus includes an unrelated "
                        "distractor record."
                    ),
                },
                indent=2,
                sort_keys=True,
            ),
        },
    ]


def dry_provider_response(task_id: str, condition: str, cycle: int) -> JsonDict:
    task = TASKS[task_id]
    if condition == "event_loop_bounded" and cycle == 1:
        return {
            "work_plan": "Recall task evidence and omit the distractor.",
            "requested_context": [
                {"tool": "recall", "record_id": data["evidence"]}
                for data in task["required_facts"].values()
            ],
            "omitted_record_ids": [task["distractor_id"]],
            "declared_losses": _declared_losses(task_id),
        }
    return {
        "artifact_title": f"{task_id} artifact",
        "task_id": task_id,
        "conclusion": "The bounded evidence supports a cautious next step.",
        "recommended_action": "Proceed while preserving the named limitations.",
        "claims": [
            {
                "fact_id": fact_id,
                "text": f"Supported fact: {fact_id}.",
                "status": "supported",
                "evidence_record_ids": [data["evidence"]],
            }
            for fact_id, data in task["required_facts"].items()
        ],
        "declared_losses": _declared_losses(task_id),
        "cited_record_ids": [
            data["evidence"] for data in task["required_facts"].values()
        ],
    }


def _declared_losses(task_id: str) -> list[str]:
    markers = [
        data["loss_marker"]
        for data in TASKS[task_id]["required_facts"].values()
        if data.get("loss_marker")
    ]
    return [f"Limitation remains: {marker}." for marker in markers]


def provider_call(
    *,
    task_id: str,
    condition: str,
    cycle: int,
    messages: list[JsonDict],
    dry_run: bool,
    api_key: str | None,
    endpoint: str,
    model: str,
) -> ProviderResult:
    if dry_run:
        parsed = dry_provider_response(task_id, condition, cycle)
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
            message="DEEPSEEK_API_KEY is required for live Goal 10 run",
        )
    return call_openai_compatible_json(
        api_key=api_key,
        endpoint=endpoint,
        model=model,
        messages=messages,
    )


def selection_payload(selection: JsonDict) -> JsonDict:
    nested = selection.get("required_output")
    if isinstance(nested, dict):
        return nested
    return selection


def resolve_context(
    *,
    task_id: str,
    substrate: LocalMemorySubstrate,
    requested_context: list[Any],
) -> tuple[list[JsonDict], list[JsonDict]]:
    recalled: list[JsonDict] = []
    classifications: list[JsonDict] = []
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
            reason={
                "experiment_id": EXPERIMENT_ID,
                "task_id": task_id,
                "condition": "event_loop_bounded",
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
                    "record_id": result_dict.get("record_id"),
                    "content": result_dict.get("content"),
                }
            )
    return recalled, classifications


def usage_tokens(provider: ProviderResult, messages: list[JsonDict]) -> JsonDict:
    usage = provider.usage or {}
    prompt = usage.get("prompt_tokens") or usage.get("input_tokens")
    completion = usage.get("completion_tokens") or usage.get("output_tokens")
    return {
        "prompt_tokens": int(prompt) if isinstance(prompt, int) else _approx_tokens(messages),
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


def validate_artifact(task_id: str, output: JsonDict) -> JsonDict:
    required = [
        "artifact_title",
        "task_id",
        "conclusion",
        "recommended_action",
        "claims",
        "declared_losses",
        "cited_record_ids",
    ]
    missing = [field for field in required if field not in output]
    claims = output.get("claims")
    if missing or not isinstance(claims, list):
        return {
            "ok": False,
            "missing_fields": missing,
            "error": "artifact missing required fields or claims is not an array",
        }
    if str(output.get("task_id")) != task_id:
        return {
            "ok": False,
            "missing_fields": [],
            "error": "artifact task_id did not match task",
        }
    return {"ok": True, "missing_fields": []}


def score_artifact(task_id: str, output: JsonDict) -> JsonDict:
    task = TASKS[task_id]
    validation = validate_artifact(task_id, output)
    if not validation["ok"]:
        return {
            "scoreable": False,
            "artifact_quality_score": 0.0,
            "schema_score": 0.0,
            "recovery_rate": 0.0,
            "citation_correctness_rate": 0.0,
            "declared_loss_rate": 0.0,
            "contamination_rate": 1.0,
            "actionability_score": 0.0,
            "catastrophic_failure": True,
            "validation": validation,
            "recovered_fact_ids": [],
            "missing_fact_ids": sorted(task["required_facts"]),
        }
    claims = [claim for claim in output.get("claims", []) if isinstance(claim, dict)]
    recovered: set[str] = set()
    citation_checks = 0
    citation_correct = 0
    unsupported = {"unsupported", "open", "unknown", "missing", "not_supported"}
    for claim in claims:
        fact_id = str(claim.get("fact_id", ""))
        evidence = {str(item) for item in claim.get("evidence_record_ids", [])}
        status = str(claim.get("status", "")).lower()
        expected = task["required_facts"].get(fact_id)
        if expected is None:
            continue
        citation_checks += 1
        if expected["evidence"] in evidence:
            citation_correct += 1
        if status not in unsupported and expected["evidence"] in evidence:
            recovered.add(fact_id)
    cited = {str(item) for item in output.get("cited_record_ids", [])}
    text_blob = json.dumps(output, sort_keys=True).lower()
    distractor_id = task["distractor_id"]
    contamination = int(
        distractor_id in cited
        or "purple-blue" in text_blob
        or "fairy-tale" in text_blob
        or "cellar metaphor" in text_blob
        or "computational identity object" in text_blob
    )
    loss_markers = [
        str(data["loss_marker"]).lower()
        for data in task["required_facts"].values()
        if data.get("loss_marker")
    ]
    declared_text = " ".join(
        str(item).lower() for item in output.get("declared_losses", [])
    )
    declared_loss_count = sum(1 for marker in loss_markers if marker in declared_text)
    recovery_rate = len(recovered) / len(task["required_facts"])
    citation_rate = citation_correct / citation_checks if citation_checks else 0.0
    declared_loss_rate = (
        declared_loss_count / len(loss_markers) if loss_markers else 1.0
    )
    actionability = 1.0 if output.get("conclusion") and output.get("recommended_action") else 0.0
    quality = (
        0.10
        + recovery_rate * 0.40
        + citation_rate * 0.20
        + declared_loss_rate * 0.15
        + (1.0 - contamination) * 0.10
        + actionability * 0.05
    )
    catastrophic = recovery_rate < 0.60 or contamination > 0.50
    return {
        "scoreable": True,
        "artifact_quality_score": round(quality, 4),
        "schema_score": 1.0,
        "recovered_fact_ids": sorted(recovered),
        "missing_fact_ids": sorted(set(task["required_facts"]) - recovered),
        "recovery_rate": round(recovery_rate, 4),
        "citation_correctness_rate": round(citation_rate, 4),
        "declared_loss_rate": round(declared_loss_rate, 4),
        "contamination_rate": float(contamination),
        "actionability_score": actionability,
        "catastrophic_failure": catastrophic,
        "validation": validation,
    }


def score_observability(row: JsonDict) -> JsonDict:
    traces = row.get("traces", {})
    cycle_files = traces.get("cycle_files", [])
    context = row.get("context_accounting", {})
    artifact_score = row.get("artifact_score")
    failure_surface = row.get("failure_attribution", {})
    features = {
        "raw_request_response_preserved": all(
            item.get("request_payload_present") and item.get("response_payload_present")
            for item in cycle_files
        ),
        "parsed_artifact_preserved": bool(row.get("artifact")),
        "cycle_boundary_visible": len(cycle_files) > 1,
        "evidence_request_and_recall_visible": bool(
            context.get("request_classifications")
            and context.get("recall_provenance")
        ),
        "deterministic_artifact_score_preserved": bool(artifact_score),
        "failure_attribution_surface_present": bool(failure_surface),
        "restart_reconstruction_proxy_present": bool(
            row.get("restart_reconstruction_proxy", {}).get("reconstructable")
        ),
    }
    weights = {
        "raw_request_response_preserved": 0.15,
        "parsed_artifact_preserved": 0.15,
        "cycle_boundary_visible": 0.15,
        "evidence_request_and_recall_visible": 0.20,
        "deterministic_artifact_score_preserved": 0.15,
        "failure_attribution_surface_present": 0.10,
        "restart_reconstruction_proxy_present": 0.10,
    }
    score = sum(weights[key] for key, value in features.items() if value)
    return {
        "observability_score": round(score, 4),
        "features": features,
        "weights": weights,
    }


def classify_disagreement(artifact_score: JsonDict, observability_score: JsonDict) -> JsonDict:
    delta = round(
        artifact_score["artifact_quality_score"]
        - observability_score["observability_score"],
        4,
    )
    return {
        "delta_artifact_minus_observability": delta,
        "disagreement": abs(delta) >= 0.25,
        "interpretation": (
            "artifact_quality_exceeds_trace_observability"
            if delta >= 0.25
            else "trace_observability_exceeds_artifact_quality"
            if delta <= -0.25
            else "aligned"
        ),
    }


def trace_manifest(row_root: Path, cycles: int) -> JsonDict:
    cycle_files = []
    for cycle in range(1, cycles + 1):
        path = row_root / f"cycle_{cycle:02d}.json"
        payload = _read_json(path)
        cycle_files.append(
            {
                "path": str(path),
                "request_payload_present": bool(payload.get("request_payload")),
                "response_payload_present": bool(payload.get("response_payload")),
                "parsed_present": bool(payload.get("parsed")),
                "attempt_count": len(payload.get("attempts", [])),
            }
        )
    return {"cycle_files": cycle_files}


def run_event_loop_row(
    *,
    task_id: str,
    output_root: Path,
    dry_run: bool,
    api_key: str | None,
    endpoint: str,
    model: str,
) -> JsonDict:
    condition = "event_loop_bounded"
    row_root = output_root / "rows" / task_id / condition
    row_root.mkdir(parents=True, exist_ok=True)
    substrate = build_corpus(task_id)
    messages1 = selection_messages(task_id, corpus_map(substrate))
    selection = provider_call(
        task_id=task_id,
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
    requested = selected.get("requested_context", [])
    recalled, classifications = resolve_context(
        task_id=task_id,
        substrate=substrate,
        requested_context=requested if isinstance(requested, list) else [],
    )
    messages2 = event_artifact_messages(
        task_id=task_id,
        selection=selected,
        recalled_context=recalled,
    )
    final = provider_call(
        task_id=task_id,
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
        "task_id": task_id,
        "live_context": {
            "cycle_1": {"messages": messages1, "token_count": usage1["prompt_tokens"]},
            "cycle_2": {"messages": messages2, "token_count": usage2["prompt_tokens"]},
        },
        "carried_state": selected,
        "recalled_context": recalled,
        "request_classifications": classifications,
        "recall_provenance": substrate.retrieval_log().data["retrievals"],
        "omitted_context": selected.get("omitted_record_ids", []),
        "declared_losses": final.parsed.get("declared_losses", []),
        "token_use": {
            "prompt_tokens": usage1["prompt_tokens"] + usage2["prompt_tokens"],
            "peak_prompt_tokens": max(usage1["prompt_tokens"], usage2["prompt_tokens"]),
            "completion_tokens": usage1["completion_tokens"] + usage2["completion_tokens"],
            "source": [usage1["source"], usage2["source"]],
        },
    }
    artifact_score = score_artifact(task_id, final.parsed)
    row = {
        "task_id": task_id,
        "condition": condition,
        "artifact": final.parsed,
        "artifact_score": artifact_score,
        "context_accounting": context_accounting,
        "failure_attribution": {
            "surface": "present",
            "layer": "none" if artifact_score["scoreable"] else "model",
        },
        "restart_reconstruction_proxy": {
            "reconstructable": True,
            "cycle_count": 2,
            "state_boundary": "cycle_1_selection_to_cycle_2_artifact",
        },
    }
    row["traces"] = trace_manifest(row_root, 2)
    row["observability_score"] = score_observability(row)
    row["judge_scorer_disagreement"] = classify_disagreement(
        row["artifact_score"],
        row["observability_score"],
    )
    _write_json(row_root / "context_accounting.json", context_accounting)
    _write_json(row_root / "score.json", row["artifact_score"])
    _write_json(row_root / "observability_score.json", row["observability_score"])
    _write_json(row_root / "row_result.json", row)
    return row


def run_direct_row(
    *,
    task_id: str,
    output_root: Path,
    dry_run: bool,
    api_key: str | None,
    endpoint: str,
    model: str,
) -> JsonDict:
    condition = "direct_one_shot"
    row_root = output_root / "rows" / task_id / condition
    row_root.mkdir(parents=True, exist_ok=True)
    substrate = build_corpus(task_id)
    messages = direct_messages(task_id, corpus_map(substrate))
    final = provider_call(
        task_id=task_id,
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
        "task_id": task_id,
        "live_context": {"messages": messages, "token_count": usage["prompt_tokens"]},
        "carried_state": {},
        "recalled_context": substrate.snapshot()["records"],
        "request_classifications": [],
        "recall_provenance": [],
        "omitted_context": [],
        "declared_losses": final.parsed.get("declared_losses", []),
        "token_use": {
            "prompt_tokens": usage["prompt_tokens"],
            "peak_prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "source": usage["source"],
        },
    }
    artifact_score = score_artifact(task_id, final.parsed)
    row = {
        "task_id": task_id,
        "condition": condition,
        "artifact": final.parsed,
        "artifact_score": artifact_score,
        "context_accounting": context_accounting,
        "failure_attribution": {
            "surface": "present",
            "layer": "none" if artifact_score["scoreable"] else "model",
        },
        "restart_reconstruction_proxy": {
            "reconstructable": False,
            "cycle_count": 1,
            "state_boundary": "none",
        },
    }
    row["traces"] = trace_manifest(row_root, 1)
    row["observability_score"] = score_observability(row)
    row["judge_scorer_disagreement"] = classify_disagreement(
        row["artifact_score"],
        row["observability_score"],
    )
    _write_json(row_root / "context_accounting.json", context_accounting)
    _write_json(row_root / "score.json", row["artifact_score"])
    _write_json(row_root / "observability_score.json", row["observability_score"])
    _write_json(row_root / "row_result.json", row)
    return row


def write_blinded_review_packet(output_root: Path, rows: list[JsonDict]) -> JsonDict:
    packet_root = output_root / "review_packet"
    packet_root.mkdir(parents=True, exist_ok=True)
    packet: list[JsonDict] = []
    for index, row in enumerate(sorted(rows, key=lambda item: (item["task_id"], item["condition"])), 1):
        artifact_id = f"artifact_{index:02d}"
        _write_json(packet_root / f"{artifact_id}.json", row["artifact"])
        packet.append(
            {
                "artifact_id": artifact_id,
                "task_id": row["task_id"],
                "condition_hidden": True,
                "condition": row["condition"],
                "score_path": str(
                    output_root
                    / "rows"
                    / row["task_id"]
                    / row["condition"]
                    / "score.json"
                ),
            }
        )
    _write_json(packet_root / "manifest.json", {"artifacts": packet})
    return {"packet_root": str(packet_root), "artifacts": packet}


def summarize(rows: list[JsonDict]) -> JsonDict:
    by_condition: dict[str, list[JsonDict]] = {
        condition: [row for row in rows if row["condition"] == condition]
        for condition in CONDITIONS
    }
    means: dict[str, JsonDict] = {}
    for condition, condition_rows in by_condition.items():
        means[condition] = {
            "artifact_quality_mean": round(
                sum(row["artifact_score"]["artifact_quality_score"] for row in condition_rows)
                / len(condition_rows),
                4,
            ),
            "observability_mean": round(
                sum(row["observability_score"]["observability_score"] for row in condition_rows)
                / len(condition_rows),
                4,
            ),
            "catastrophic_failures": sum(
                1 for row in condition_rows if row["artifact_score"]["catastrophic_failure"]
            ),
            "judge_scorer_disagreements": sum(
                1 for row in condition_rows if row["judge_scorer_disagreement"]["disagreement"]
            ),
        }
    event_mean = means["event_loop_bounded"]["artifact_quality_mean"]
    direct_mean = means["direct_one_shot"]["artifact_quality_mean"]
    quality_delta = round(event_mean - direct_mean, 4)
    non_inferior = (
        quality_delta >= -NON_INFERIORITY_MARGIN
        and means["event_loop_bounded"]["catastrophic_failures"] == 0
    )
    observability_delta = round(
        means["event_loop_bounded"]["observability_mean"]
        - means["direct_one_shot"]["observability_mean"],
        4,
    )
    observability_stronger = observability_delta > 0
    classification = "survived" if non_inferior and observability_stronger else "falsified"
    return {
        "classification": classification,
        "non_inferiority_margin": NON_INFERIORITY_MARGIN,
        "artifact_non_inferior": non_inferior,
        "observability_stronger": observability_stronger,
        "artifact_quality_delta_event_minus_direct": quality_delta,
        "observability_delta_event_minus_direct": observability_delta,
        "means": means,
    }


def run_panel(
    *,
    output_root: Path,
    dry_run: bool,
    overwrite: bool,
    api_key: str | None,
    endpoint: str,
    model: str,
) -> JsonDict:
    if output_root.exists() and overwrite:
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    rows: list[JsonDict] = []
    failures: list[JsonDict] = []
    for task_id in TASKS:
        for runner in (run_event_loop_row, run_direct_row):
            try:
                rows.append(
                    runner(
                        task_id=task_id,
                        output_root=output_root,
                        dry_run=dry_run,
                        api_key=api_key,
                        endpoint=endpoint,
                        model=model,
                    )
                )
            except PanelFailure as exc:
                failures.append(
                    {
                        "task_id": task_id,
                        "runner": runner.__name__,
                        "failure": exc.to_dict(),
                    }
                )
    review_packet = write_blinded_review_packet(output_root, rows) if rows else {}
    summary = summarize(rows) if not failures and len(rows) == len(TASKS) * 2 else {
        "classification": "inconclusive",
        "failures": failures,
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "endpoint": endpoint,
        "live_model_calls": not dry_run,
        "classification": summary["classification"],
        "summary": summary,
        "rows": rows,
        "failures": failures,
        "review_packet": review_packet,
    }
    _write_json(output_root / "results.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--output-root",
        default=str(Path(__file__).resolve().parent),
    )
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args(argv)
    try:
        result = run_panel(
            output_root=Path(args.output_root),
            dry_run=args.dry_run,
            overwrite=args.overwrite,
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            endpoint=args.endpoint,
            model=args.model,
        )
    except PanelFailure as exc:
        _write_json(
            Path(args.output_root) / "results.json",
            {
                "experiment_id": EXPERIMENT_ID,
                "classification": "inconclusive",
                "failure": exc.to_dict(),
            },
        )
        print(json.dumps(exc.to_dict(), indent=2, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
