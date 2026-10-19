"""The Anthropic credit pool, as a fact a resident is told at each wake.

Tony's subscription carries a monthly pool of Anthropic API credit that
expires at the end of each billing period. A door launched with
`--credit-pool PATH` is told, in its wake envelope's operational notes, how
much of the pool remains and when it expires. The note is facts only; it
gives no advice about spending.

Spend is the house's own estimate: the pool file's `spent_before_tracking_usd`
plus every metered anthropic-direct wake in every door log under
`community/*/session.jsonl` within the period (cost from tokens, see
anthropic_direct.py). Spend outside community/ (smoke tests, experiments) is
not seen; Anthropic's bill is authoritative, and the Admin API is the way to
reconcile against it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class CreditPool:
    credit_usd: float
    period_start: date
    period_end: date  # the last day the credit is available, as the console states it
    spent_before_tracking_usd: float = 0.0
    period_start_confirmed: bool = False

    @property
    def window(self) -> tuple[datetime, datetime]:
        """[start of period_start, end of period_end) in UTC."""
        start = datetime.combine(self.period_start, time.min, tzinfo=timezone.utc)
        end = datetime.combine(self.period_end + timedelta(days=1), time.min, tzinfo=timezone.utc)
        return start, end


def _number(raw: dict, key: str, default: float | None = None) -> float:
    value = raw.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise SystemExit(f"credit pool: {key} must be a non-negative number, got {value!r}")
    return float(value)


def _date(raw: dict, key: str) -> date:
    value = raw.get(key)
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise SystemExit(f"credit pool: {key} must be an ISO date (YYYY-MM-DD), got {value!r}") from None


def load_credit_pool(path: str | Path) -> CreditPool:
    """Read the pool file; any malformed field refuses the launch, loudly."""
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, ValueError) as err:
        raise SystemExit(f"credit pool: cannot read {path}: {err}") from err
    if not isinstance(raw, dict):
        raise SystemExit(f"credit pool: {path} must hold a JSON object")
    pool = CreditPool(
        credit_usd=_number(raw, "credit_usd"),
        period_start=_date(raw, "period_start"),
        period_end=_date(raw, "period_end"),
        spent_before_tracking_usd=_number(raw, "spent_before_tracking_usd", 0.0),
        period_start_confirmed=raw.get("period_start_confirmed") is True,
    )
    if pool.period_end < pool.period_start:
        raise SystemExit("credit pool: period_end is before period_start")
    return pool


class PoolSpend:
    """Pool spend across every door log, re-reading a log only when it grows."""

    def __init__(self, project_root: str | Path, pool: CreditPool):
        from hamutay.heartbeat import DailyLedger

        self._root = Path(project_root)
        self._pool = pool
        self._ledger_cls = DailyLedger
        self._ledgers: dict[Path, object] = {}

    def total(self) -> dict:
        start, end = self._pool.window
        cost = self._pool.spent_before_tracking_usd
        wakes = unmeasured = 0
        for log in sorted(self._root.glob("community/*/session.jsonl")):
            ledger = self._ledgers.get(log)
            if ledger is None:
                ledger = self._ledgers[log] = self._ledger_cls(str(log))
            part = ledger.span(start, end, provider="anthropic")
            cost += part["cost_usd"]
            wakes += part["wakes"]
            unmeasured += part["unmeasured_wakes"]
        return {"cost_usd": cost, "wakes": wakes, "unmeasured_wakes": unmeasured}


def pool_note(pool: CreditPool, spend: dict, daily_ceiling_usd: float | None, now: datetime) -> str:
    """The sentence the resident reads. Facts only, no advice."""
    remaining = max(pool.credit_usd - spend["cost_usd"], 0.0)
    _, end = pool.window
    if now >= end:
        text = (
            f"Credit pool: the period that ended {pool.period_end.isoformat()} is over; "
            f"its unused credit did not carry over."
        )
    else:
        text = (
            f"Credit pool: ${remaining:.2f} of ${pool.credit_usd:.2f} remaining "
            f"(estimated from tokens; Anthropic's bill is authoritative). "
            f"It expires {pool.period_end.isoformat()}; unused credit does not carry over."
        )
        if spend.get("unmeasured_wakes"):
            text += (
                f" {spend['unmeasured_wakes']} wake(s) had no cost estimate, "
                f"so the remaining amount is an upper bound."
            )
    if daily_ceiling_usd is None:
        text += " There is no daily ceiling."
    else:
        text += f" Today's ceiling: ${daily_ceiling_usd:.2f}."
    return text


def pool_note_producer(project_root, pool: CreditPool, daily_ceiling_usd: float | None, *, now=None):
    """An `extra_notes` callable: (event, store_records) -> [note]."""
    spend = PoolSpend(project_root, pool)
    clock = now or (lambda: datetime.now(timezone.utc))

    def produce(event, store_records):
        return [pool_note(pool, spend.total(), daily_ceiling_usd, clock())]

    return produce
