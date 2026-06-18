"""Phase 2B Yanantin memory contract validator."""

from __future__ import annotations

import argparse
import datetime as datetime_module
import inspect
import json
import sys
import typing as typing_module
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]

EXPERIMENT_ID = "phase_2b_yanantin_memory_contract_20260618"
ROOT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT_DIR.parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
YANANTIN_SRC_ROOT = PROJECT_ROOT.parent / "yanantin" / "src"
TIKSI_SRC_ROOT = PROJECT_ROOT.parent / "tiksi" / "src"
for path in (PROJECT_ROOT, SRC_ROOT, YANANTIN_SRC_ROOT, TIKSI_SRC_ROOT):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))
if not hasattr(datetime_module, "UTC"):
    datetime_module.UTC = datetime_module.timezone.utc
if not hasattr(typing_module, "Self"):
    from typing_extensions import Self

    typing_module.Self = Self

REQUIRED_CONTRACT_SECTIONS = [
    "## Contract Boundary",
    "## Record Write Policy",
    "## Memory Scopes",
    "## Retrieval Contract",
    "## Event Envelope Representation",
    "## Provenance And Attribution Scoring",
    "## Failure Rules",
    "## Readiness For Next Probe",
]
REQUIRED_PROVENANCE_FIELDS = [
    "run_id",
    "event_id",
    "event_identity",
    "entity_id",
    "workstream_id",
    "record_id",
    "source_record_id",
    "author_model_family",
    "author_instance_id",
    "timestamp",
    "cycle",
    "relation_type",
    "access_scope",
    "retrieval_reason",
]
REQUIRED_MEMORY_SCOPES = [
    "Entity-Scoped Memory",
    "Shared Memory",
    "Housekeeping Memory",
]
REQUIRED_RETRIEVAL_ENVELOPE_FIELDS = [
    "source_record_id",
    "source_event_id",
    "source_run_id",
    "entity_id",
    "workstream_id",
    "memory_scope",
    "access_scope",
    "relation_type",
    "retrieval_id",
    "retrieval_reason",
    "content_excerpt",
    "omitted",
    "truncated",
]
REQUIRED_FAILURE_LAYERS = [
    "scheduler_lifecycle",
    "event_identity",
    "state_isolation",
    "yanantin_write",
    "yanantin_retrieval",
    "authorization",
    "provenance",
    "model_output",
    "provider_transport",
    "artifact",
    "inconclusive",
]
REQUIRED_MEMORY_PORT_METHODS = [
    "store_episode",
    "recall",
    "schema",
    "walk",
    "link_records",
    "open_items",
    "what_changed",
    "retrieval_log",
    "write_attestation",
]
REQUIRED_APACHETA_BRIDGE_METHODS = [
    "store_open_state",
    "store_instance_record",
    "store_edge",
    "retrieve",
    "list_open_records",
    "query_open_by_session",
    "query_open_by_lineage_tag",
    "query_open_has_field",
    "query_edges_by_endpoint",
]
REQUIRED_RECALL_SUBSTRATES = [
    "in_session_state",
    "local_artifact_recall",
    "yanantin_backed_recall",
]


def write_json(path: Path, record: JsonDict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n")


def load_json(path: Path) -> JsonDict:
    return json.loads(path.read_text())


def missing_tokens(text: str, tokens: list[str]) -> list[str]:
    return [token for token in tokens if token not in text]


def class_methods(class_object: Any) -> set[str]:
    return {
        name
        for name, member in inspect.getmembers(class_object)
        if inspect.isfunction(member) or inspect.ismethod(member)
    }


def inspect_existing_surfaces() -> JsonDict:
    from hamutay.apacheta_bridge import ApachetaBridge
    from hamutay.memory.bridge import MemoryPort

    memory_port_methods = class_methods(MemoryPort)
    apacheta_bridge_methods = class_methods(ApachetaBridge)
    return {
        "memory_port_methods": sorted(memory_port_methods),
        "apacheta_bridge_methods": sorted(apacheta_bridge_methods),
        "missing_memory_port_methods": sorted(
            set(REQUIRED_MEMORY_PORT_METHODS) - memory_port_methods
        ),
        "missing_apacheta_bridge_methods": sorted(
            set(REQUIRED_APACHETA_BRIDGE_METHODS) - apacheta_bridge_methods
        ),
    }


def validate_contract(contract_root: Path = ROOT_DIR) -> JsonDict:
    contract_text = (contract_root / "CONTRACT.md").read_text()
    matrix = load_json(contract_root / "matrix.json")
    budget = load_json(contract_root / "budget.json")
    taxonomy = load_json(contract_root / "failure_taxonomy.json")
    surface = inspect_existing_surfaces()

    missing_sections = missing_tokens(contract_text, REQUIRED_CONTRACT_SECTIONS)
    missing_provenance_fields = missing_tokens(
        contract_text,
        REQUIRED_PROVENANCE_FIELDS,
    )
    missing_memory_scopes = missing_tokens(contract_text, REQUIRED_MEMORY_SCOPES)
    missing_envelope_fields = missing_tokens(
        contract_text,
        REQUIRED_RETRIEVAL_ENVELOPE_FIELDS,
    )
    taxonomy_layers = set(taxonomy.get("layers", []))
    missing_failure_layers = sorted(set(REQUIRED_FAILURE_LAYERS) - taxonomy_layers)
    record_classes = matrix.get("record_classes", {})
    recall_substrates = set(matrix.get("recall_substrates", []))

    checks = {
        "required_contract_sections_present": missing_sections == [],
        "required_provenance_fields_present": missing_provenance_fields == [],
        "required_memory_scopes_present": missing_memory_scopes == [],
        "record_write_boundaries_present": bool(
            record_classes.get("yanantin_writes")
            and record_classes.get("local_only")
            and "### Yanantin Writes" in contract_text
            and "### Local-Only Records" in contract_text
        ),
        "retrieval_envelope_fields_present": missing_envelope_fields == [],
        "failure_attribution_layers_present": missing_failure_layers == [],
        "hamutay_memory_port_methods_present": (
            surface["missing_memory_port_methods"] == []
        ),
        "apacheta_bridge_methods_present": (
            surface["missing_apacheta_bridge_methods"] == []
        ),
        "recall_substrates_distinguished": (
            set(REQUIRED_RECALL_SUBSTRATES) <= recall_substrates
        ),
        "budget_prohibits_live_calls": (
            budget.get("live_model_calls") is False
            and budget.get("max_live_calls") == 0
            and budget.get("max_estimated_cost_usd") == 0.0
        ),
    }
    failure_attribution: list[JsonDict] = []
    for check_name, passed in checks.items():
        if not passed:
            failure_attribution.append(
                {
                    "layer": classify_check_failure(check_name),
                    "check": check_name,
                    "message": f"{check_name} failed",
                }
            )

    return {
        "experiment_id": EXPERIMENT_ID,
        "classification": "passed" if all(checks.values()) else "failed",
        "live_model_calls": False,
        "success": {
            "checks": checks,
            "missing_sections": missing_sections,
            "missing_provenance_fields": missing_provenance_fields,
            "missing_memory_scopes": missing_memory_scopes,
            "missing_retrieval_envelope_fields": missing_envelope_fields,
            "missing_failure_layers": missing_failure_layers,
            "surface": surface,
            "recall_substrates": sorted(recall_substrates),
        },
        "failure_attribution": failure_attribution,
    }


def classify_check_failure(check_name: str) -> str:
    if "provenance" in check_name or "envelope" in check_name:
        return "provenance"
    if "memory_port" in check_name or "apacheta" in check_name:
        return "yanantin_retrieval"
    if "budget" in check_name:
        return "artifact"
    if "boundaries" in check_name or "scopes" in check_name:
        return "authorization"
    return "artifact"


def run_probe(
    *,
    output_root: Path | None = None,
    contract_root: Path = ROOT_DIR,
    overwrite: bool = False,
) -> JsonDict:
    output_root = output_root or contract_root
    result_path = output_root / "results.json"
    if result_path.exists() and not overwrite:
        raise FileExistsError(f"{result_path} exists; pass overwrite=True")
    result = validate_contract(contract_root)
    write_json(result_path, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT_DIR)
    parser.add_argument("--contract-root", type=Path, default=ROOT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    result = run_probe(
        output_root=args.output_root,
        contract_root=args.contract_root,
        overwrite=args.overwrite,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0 if result["classification"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
