"""Continuity curator adapters for taste_open sessions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from hamutay.taste_open import ExchangeResult, TasteBackend


_CURATOR_SYSTEM_PROMPT = """\
You are a continuity curator for a Hamut'ay taste_open session.

Your job is to produce a compact continuity artifact for the next cycle. You
are not the session's identity object author, and you must not write new state
for the main instance. Preserve what is useful for continuity, distinguish
supported facts from uncertainty, and explicitly mark invalidated assumptions.

Return a structured object. Put the compact carry-forward text in `summary`.
The required `response` field should repeat that compact summary; it is an
internal curator artifact, not a user-facing chat response.
"""


def _jsonable(value):
    return json.loads(json.dumps(value, default=str))


def _truncate_text(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars < 1:
        raise ValueError("max_summary_chars must be positive")
    if len(text) <= max_chars:
        return text, False
    marker = "\n[truncated]"
    if max_chars <= len(marker):
        return text[:max_chars], True
    return text[: max_chars - len(marker)].rstrip() + marker, True


@dataclass
class ModelContinuityCurator:
    """Model-backed continuity curator for the first-class scaffold hook."""

    backend: TasteBackend
    model: str
    experiment_label: str = "taste_open_continuity_curator"
    max_summary_chars: int = 2400

    def curate(
        self,
        *,
        cycle: int,
        record_id: UUID,
        timestamp: datetime,
        prior_state: dict | None,
        raw_output: dict,
        response_text: str,
        state: dict,
    ) -> dict:
        payload = {
            "source_cycle": cycle,
            "source_record_id": str(record_id),
            "source_timestamp": timestamp.isoformat(),
            "prior_state": prior_state,
            "main_raw_output": raw_output,
            "main_visible_response": response_text,
            "merged_state": state,
        }
        messages = [
            {
                "role": "user",
                "content": (
                    "Curate the following completed cycle for continuity. "
                    "Do not add unsupported facts. Return `summary`, "
                    "`supported_facts`, `uncertain_claims`, "
                    "`invalidated_assumptions`, and any brief "
                    "`curator_notes` that matter.\n\n"
                    + json.dumps(payload, indent=2, default=str)
                ),
            }
        ]

        result = self.backend.call(
            model=self.model,
            system=_CURATOR_SYSTEM_PROMPT,
            messages=messages,
            experiment_label=self.experiment_label,
        )
        raw = _jsonable(result.raw_output)
        summary_source = "summary"
        summary = str(raw.get("summary") or "").strip()
        if not summary:
            summary_source = "carry_forward_summary"
            summary = str(raw.get("carry_forward_summary") or "").strip()
        if not summary:
            summary_source = "response"
            summary = str(raw.get("response") or "").strip()
        summary, summary_truncated = _truncate_text(
            summary,
            self.max_summary_chars,
        )

        return {
            "curator_type": "model",
            "model": self.model,
            "summary": summary,
            "summary_source": summary_source,
            "summary_chars": len(summary),
            "summary_truncated": summary_truncated,
            "supported_facts": raw.get("supported_facts", []),
            "uncertain_claims": raw.get("uncertain_claims", []),
            "invalidated_assumptions": raw.get("invalidated_assumptions", []),
            "curator_notes": raw.get("curator_notes", []),
            "usage": {
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cache_read_input_tokens": result.cache_read_tokens,
                "cache_creation_input_tokens": result.cache_creation_tokens,
                "stop_reason": result.stop_reason,
            },
            "raw_output": raw,
        }


__all__ = ["ModelContinuityCurator"]
