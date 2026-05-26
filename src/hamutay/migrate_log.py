"""Replay a taste_open JSONL log into an Apacheta backend.

A taste_open session writes a JSONL log (one record per cycle) and,
when a persistence bridge is wired, also stores each cycle's state in
Apacheta with a per-cycle REFINES chain. If the bridge was unavailable
during the run (ArangoDB not provisioned, ``--no-persist``, an
ImportError), the JSONL is the only durable copy. This replays it into
a backend after the fact: each cycle's ``state`` becomes an open record
under the log's ``record_id``, and the REFINES chain is reconstructed
from the cycle ordering.

Logs predating the record_id refactor (early April 2026) carry no
``record_id`` field; for those, fresh UUIDs are minted. The chain is
still correct — only cross-session references to a specific old cycle
won't resolve, and there were none to resolve, because the records
were never stored in the first place.

What is *not* replayed: instance-authored records (the ``store`` tool)
and instance-authored edges (``annotate_edge``). Those tools require a
live bridge — if it was down during the run they returned errors and
minted nothing, so there is nothing to recover. If it was *up*, the
records are already in that backend and don't need migrating. The
migrator warns if it sees such activity in the log so the gap is
visible rather than silent.

Usage:
    uv run python -m hamutay.migrate_log LOG.jsonl --duckdb tensors.duckdb
    uv run python -m hamutay.migrate_log LOG.jsonl --arango
    uv run python -m hamutay.migrate_log LOG.jsonl --duckdb tensors.duckdb --dry-run
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid5, NAMESPACE_URL


_LFS_POINTER_PREFIX = "version https://git-lfs"

# Namespace for synthetic record_ids assigned to pre-2026-04-19 logs that
# predate the framework minting (and logging) a record_id per cycle. The id
# is derived from (session_id, cycle), so re-running migration on the same
# log produces the same ids — the destination's immutability guard then
# treats a re-import as a no-op rather than silently duplicating. (Logs from
# 2026-04-19 onward carry a real record_id and don't go through here.)
_LEGACY_ID_NAMESPACE = uuid5(NAMESPACE_URL, "https://github.com/fsgeek/hamutay#taste_open-legacy-cycle")


def legacy_record_id(session_id: str, cycle: int) -> UUID:
    """Deterministic surrogate record_id for a pre-refactor cycle."""
    return uuid5(_LEGACY_ID_NAMESPACE, f"{session_id}|cycle:{cycle}")


class LogFormatError(RuntimeError):
    """The log file can't be read as a taste_open JSONL log."""


class AlreadyMigratedError(RuntimeError):
    """The destination already holds this log's records."""


def _session_id_from_path(log_path: Path) -> str:
    """Derive a stable session_id from the log filename.

    ``taste_open_20260512_185846.jsonl`` -> ``20260512_185846`` —
    the same string OpenTasteSession would have generated had it been
    started at that instant. Falls back to the bare stem otherwise.
    """
    stem = log_path.stem
    prefix = "taste_open_"
    if stem.startswith(prefix):
        rest = stem[len(prefix) :]
        if rest:
            return rest
    return stem


def _parse_timestamp(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        ts = datetime.fromisoformat(raw)
    except ValueError:
        return datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def iter_log_records(log_path: str | Path) -> Iterator[dict]:
    """Yield parsed JSONL records, skipping blank lines.

    Raises LogFormatError if the file is a Git LFS pointer (the actual
    content lives in LFS storage and hasn't been pulled) or if a line
    isn't valid JSON.
    """
    path = Path(log_path)
    with open(path) as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            if lineno == 1 and line.startswith(_LFS_POINTER_PREFIX):
                raise LogFormatError(
                    f"{path} is a Git LFS pointer, not data. "
                    f'Run: git lfs pull --include="{path}" '
                    "(and ensure git-lfs is installed)."
                )
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise LogFormatError(f"{path}:{lineno}: invalid JSON: {e}") from e


def _activity_warnings(state: dict | None) -> list[str]:
    """Names of graph-write tools the instance used this cycle, if any.

    These aren't migrated (see module docstring); surfacing them keeps
    the gap visible.
    """
    if not isinstance(state, dict):
        return []
    activity = state.get("_activity_log")
    if not isinstance(activity, list):
        return []
    return [
        a.get("tool")
        for a in activity
        if isinstance(a, dict) and a.get("tool") in {"store", "annotate_edge"}
    ]


def _record_exists(bridge, record_id: UUID) -> bool:
    """True if ``bridge`` can retrieve ``record_id``.

    A missing record raises NotFoundError (yanantin); any retrieval
    failure is treated as "not present" — if the backend is genuinely
    broken, the subsequent store will surface that error instead.
    """
    if not hasattr(bridge, "retrieve"):
        return False
    try:
        bridge.retrieve(record_id)
        return True
    except Exception:
        return False


def _resolve_record_id(record: dict, session_id: str) -> tuple[UUID, bool]:
    """(record_id, was_minted). Logs from 2026-04-19 on carry one; older
    logs get a deterministic surrogate so re-import is idempotent."""
    rid_str = record.get("record_id")
    if rid_str:
        return UUID(rid_str), False
    return legacy_record_id(session_id, record.get("cycle", 0)), True


def migrate_log(
    log_path: str | Path,
    bridge,
    *,
    dry_run: bool = False,
) -> dict:
    """Replay a taste_open JSONL log into ``bridge``.

    ``bridge`` is an ApachetaBridge (or anything exposing
    ``store_open_state(state, cycle, record_id, timestamp)``; for the
    pre-flight guard it also wants ``retrieve(record_id)``). When
    ``dry_run`` is true the log is parsed and validated but nothing is
    written.

    Raises AlreadyMigratedError if the destination already holds the
    log's first record — re-import is intended for a fresh destination,
    not for patching a partial one.

    Returns a summary dict: ``cycles``, ``records_written``, ``model``,
    ``session_id``, ``first_cycle``, ``last_cycle``, ``minted_ids``
    (cycles whose record_id was a synthesized legacy surrogate), and
    ``skipped_no_state`` (records with no ``state`` payload — usually
    none, but a failed cycle could produce one).
    """
    path = Path(log_path)
    session_id = _session_id_from_path(path)

    cycles = 0
    records_written = 0
    minted_ids = 0
    skipped_no_state = 0
    first_cycle: int | None = None
    last_cycle: int | None = None
    model: str | None = None
    graph_write_cycles: list[int] = []
    checked_first = False

    for record in iter_log_records(path):
        cycle = record.get("cycle", 0)
        state = record.get("state")
        if model is None:
            model = record.get("model")

        if state is None:
            skipped_no_state += 1
            continue

        record_id, was_minted = _resolve_record_id(record, session_id)

        if not checked_first:
            checked_first = True
            if not dry_run and _record_exists(bridge, record_id):
                raise AlreadyMigratedError(
                    f"{path}: record {record_id} (cycle {cycle}) already exists "
                    "in the destination. Migrate into a fresh database; re-import "
                    "into a partially-populated one is not supported."
                )

        cycles += 1
        if first_cycle is None:
            first_cycle = cycle
        last_cycle = cycle
        if was_minted:
            minted_ids += 1

        if _activity_warnings(state):
            graph_write_cycles.append(cycle)

        if not dry_run:
            timestamp = _parse_timestamp(record.get("timestamp"))
            bridge.store_open_state(state, cycle, record_id, timestamp)
            records_written += 1

    return {
        "log_path": str(path),
        "session_id": session_id,
        "model": model,
        "cycles": cycles,
        "records_written": records_written,
        "minted_ids": minted_ids,
        "skipped_no_state": skipped_no_state,
        "first_cycle": first_cycle,
        "last_cycle": last_cycle,
        "graph_write_cycles": graph_write_cycles,
        "dry_run": dry_run,
    }


def _build_bridge(args, model: str):
    from hamutay.apacheta_bridge import ApachetaBridge

    session_id = _session_id_from_path(Path(args.log))
    if args.arango:
        return ApachetaBridge.from_arango(model=model)
    if args.memory:
        return ApachetaBridge.from_memory(session_id=session_id, model=model)
    return ApachetaBridge.from_duckdb(args.duckdb, session_id=session_id, model=model)


def _peek_model(log_path: Path) -> str:
    for record in iter_log_records(log_path):
        m = record.get("model")
        if m:
            return m
        break
    return "unknown"


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Replay a taste_open JSONL log into an Apacheta backend."
    )
    parser.add_argument("log", type=Path, help="Path to the taste_open JSONL log")
    dest = parser.add_mutually_exclusive_group()
    dest.add_argument(
        "--duckdb", metavar="PATH", help="DuckDB file to write into (created if absent)"
    )
    dest.add_argument(
        "--arango", action="store_true", help="Write into the configured ArangoDB"
    )
    dest.add_argument(
        "--memory", action="store_true",
        help="Write into an ephemeral in-memory backend (validation only)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and validate the log; write nothing",
    )
    args = parser.parse_args()

    if not args.log.is_file():
        raise SystemExit(f"Not a file: {args.log}")

    if not args.dry_run and not (args.duckdb or args.arango or args.memory):
        raise SystemExit(
            "Choose a destination: --duckdb PATH, --arango, --memory, or --dry-run"
        )

    try:
        if args.dry_run:
            summary = migrate_log(args.log, bridge=_NullBridge(), dry_run=True)
        else:
            model = _peek_model(args.log)
            bridge = _build_bridge(args, model)
            summary = migrate_log(args.log, bridge=bridge, dry_run=False)
    except (LogFormatError, AlreadyMigratedError) as e:
        raise SystemExit(str(e))

    print(f"Log:            {summary['log_path']}")
    print(f"Session id:     {summary['session_id']}")
    print(f"Model:          {summary['model']}")
    print(
        f"Cycles:         {summary['cycles']}"
        + (
            f"  (cycle {summary['first_cycle']}..{summary['last_cycle']})"
            if summary["cycles"]
            else ""
        )
    )
    if summary["dry_run"]:
        print("Dry run — nothing written.")
    else:
        print(f"Records written: {summary['records_written']}")
        print(
            "REFINES edges:   "
            f"{max(summary['records_written'] - 1, 0)} (per-cycle chain)"
        )
    if summary["minted_ids"]:
        print(
            f"Note: {summary['minted_ids']} cycle(s) had no record_id "
            "(pre-2026-04-19 log) — deterministic surrogate ids derived from "
            "(session_id, cycle), so re-running this migration is idempotent."
        )
    if summary["skipped_no_state"]:
        print(
            f"Note: {summary['skipped_no_state']} record(s) had no state payload "
            "— skipped."
        )
    if summary["graph_write_cycles"]:
        print(
            f"Warning: cycles {summary['graph_write_cycles']} used store/annotate_edge. "
            "Instance-authored records and edges are NOT migrated (see module docstring)."
        )


class _NullBridge:
    """No-op stand-in for --dry-run so migrate_log's contract is unchanged."""

    count = 0

    def store_open_state(self, *args, **kwargs) -> None:  # noqa: D401, ANN002, ANN003
        pass


if __name__ == "__main__":
    main()
