"""Tensor logging — capture every tensor the Projector produces.

Usage:
    from hamutay.tensor_log import TensorLog
    from hamutay.projector import Projector

    log = TensorLog("experiments/my_session/tensors.jsonl")
    projector = Projector(on_tensor=log)

    # Every call to projector.project() now appends the full tensor
    # to the JSONL file with usage metadata.

The log is append-only JSONL. Each line is a complete record:
    {cycle, tensor, usage, timestamp}

The tensor is serialized via Tensor.model_dump() — full strands,
declared_losses, IFN, epistemic state, everything. No summaries,
no previews, no truncation. Disk is cheap. Research data is not.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from hamutay.tensor import Tensor


class TensorLog:
    """Append-only JSONL logger for tensor projection data.

    Pass as the on_tensor callback to Projector.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._count = 0

    def __call__(self, tensor: Tensor, usage: dict) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cycle": tensor.cycle,
            "tensor": tensor.model_dump(),
            "usage": usage,
            "n_strands": len(tensor.strands),
            "n_losses": len(tensor.declared_losses),
            "has_ifn": bool(tensor.instructions_for_next),
            "token_estimate": tensor.token_estimate(),
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
        self._count += 1

    @property
    def count(self) -> int:
        return self._count

    @classmethod
    def load(cls, path: str | Path) -> list[dict]:
        """Load all records from a tensor log."""
        records = []
        with open(path) as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records

    @classmethod
    def tensors(cls, path: str | Path) -> list[dict]:
        """Load just the tensor dicts from a log (for content flow analysis)."""
        return [r["tensor"] for r in cls.load(path)]
