"""Reconcile a session log against OpenRouter's own books.

The cycle record carries in-band cost and generation ids
(OpenAITasteBackend._cost_kwargs). The *authoritative* billing record lives
on OpenRouter's side: GET /api/v1/generation?id=<gen> returns what was
actually charged, with native token counts and the provider that served it;
GET /api/v1/credits returns the account's total spend and balance. This
module fetches those, persists every generation record to an append-only
sidecar beside the log (<log>.billing.jsonl), and reports recorded vs.
authoritative cost per cycle.

Honesty rules:
- A generation that OpenRouter has not made visible yet (404; they are
  eventually consistent) is PENDING, not missing: it is retried on the next
  run and the cycle's authoritative cost stays None until every generation
  is in hand. A partial sum is carried beside it, labelled partial.
- A record with no generation ids (any wake before 2026-08-29, every
  Anthropic-direct record) is UNRECONCILABLE and says so; its token counts
  are reported, no dollar figure is invented for it.
- The log is never rewritten. The sidecar is append-only and is the cache:
  a generation fetched once is never fetched again.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import quote

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"

HTTPGet = Callable[[str, dict], tuple[int, dict]]


def _urllib_get(url: str, headers: dict) -> tuple[int, dict]:
    import urllib.error
    import urllib.request

    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        try:
            return err.code, json.loads(body)
        except ValueError:
            return err.code, {"error": {"message": body, "code": err.code}}


class OpenRouterBilling:
    """Thin client over the two billing endpoints. `http` is injectable."""

    def __init__(
        self,
        api_key: str,
        http: HTTPGet | None = None,
        base_url: str = OPENROUTER_API_BASE,
    ):
        if not api_key:
            raise ValueError("OpenRouterBilling needs an api_key")
        self._api_key = api_key
        self._http = http or _urllib_get
        self._base_url = base_url.rstrip("/")

    def _get(self, path: str) -> tuple[int, dict]:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        return self._http(f"{self._base_url}{path}", headers)

    def credits(self) -> dict:
        status, body = self._get("/credits")
        if status != 200:
            raise RuntimeError(f"OpenRouter /credits returned {status}: {body}")
        data = body.get("data") or {}
        total_credits = float(data.get("total_credits") or 0.0)
        total_usage = float(data.get("total_usage") or 0.0)
        return {
            "total_credits": total_credits,
            "total_usage": total_usage,
            "remaining": total_credits - total_usage,
        }

    def generation(self, generation_id: str) -> dict | None:
        """The authoritative record, or None if OpenRouter can't see it yet."""
        status, body = self._get(f"/generation?id={quote(generation_id, safe='')}")
        if status == 404:
            return None
        if status != 200:
            raise RuntimeError(
                f"OpenRouter /generation returned {status} for "
                f"{generation_id}: {body}"
            )
        data = body.get("data")
        if not isinstance(data, dict):
            raise RuntimeError(
                f"OpenRouter /generation returned no data for {generation_id}"
            )
        if not _is_number(data.get("usage")):
            raise RuntimeError(
                f"OpenRouter /generation record for {generation_id} carries no "
                f"numeric usage (got {data.get('usage')!r}); refusing to cache "
                "an unpriced generation"
            )
        return data


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# --- sidecar ----------------------------------------------------------------


def sidecar_path_for(log_path: str) -> Path:
    return Path(log_path + ".billing.jsonl")


def _load_sidecar(path: Path) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    if not path.exists():
        return entries
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            gen_id = entry.get("generation_id")
            if gen_id in entries:
                raise RuntimeError(
                    f"{path}: duplicate sidecar entry for {gen_id}; the sidecar "
                    "is append-once per generation, so this is corruption or a "
                    "concurrent writer — resolve by hand"
                )
            if not _is_number(entry.get("usage_usd")):
                raise RuntimeError(
                    f"{path}: sidecar entry for {gen_id} has non-numeric usage_usd "
                    f"{entry.get('usage_usd')!r}; an unpriced entry would read as "
                    "free — resolve by hand"
                )
            entries[gen_id] = entry
    return entries


def _sidecar_entry(cycle: int | None, record_id: str | None, gen: dict) -> dict:
    providers = gen.get("provider_responses") or []
    provider = None
    if providers and isinstance(providers[0], dict):
        provider = providers[0].get("provider_name")
    return {
        "generation_id": gen.get("id"),
        "cycle": cycle,
        "record_id": record_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "usage_usd": gen.get("usage"),
        "model": gen.get("model"),
        "provider": provider,
        "native_tokens_prompt": gen.get("native_tokens_prompt"),
        "native_tokens_completion": gen.get("native_tokens_completion"),
        "native_tokens_cached": gen.get("native_tokens_cached"),
        "native_tokens_reasoning": gen.get("native_tokens_reasoning"),
        "latency_ms": gen.get("latency"),
        "generation_time_ms": gen.get("generation_time"),
        "created_at": gen.get("created_at"),
        "finish_reason": gen.get("finish_reason"),
        "raw": gen,
    }


# --- reconcile --------------------------------------------------------------


def _read_records(log_path: str) -> list[dict]:
    records = []
    with open(log_path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def reconcile_log(log_path: str, billing: OpenRouterBilling) -> list[dict]:
    """One row per cycle record: recorded vs. authoritative cost.

    Fetches every generation id not already in the sidecar, appends what it
    gets, and leaves not-yet-visible ones for the next run.
    """
    sidecar = sidecar_path_for(log_path)
    known = _load_sidecar(sidecar)
    rows: list[dict] = []
    new_entries: list[dict] = []

    for record in _read_records(log_path):
        usage = record.get("usage") or {}
        cycle = record.get("cycle")
        record_id = record.get("record_id")
        gen_ids = usage.get("generation_ids") or []
        if not all(isinstance(g, str) and g for g in gen_ids):
            raise ValueError(
                f"{log_path}: cycle {cycle} record {record_id}: generation_ids "
                f"contains non-string entries ({gen_ids!r}); refusing to fetch"
            )
        row: dict = {
            "cycle": cycle,
            "record_id": record_id,
            "timestamp": record.get("timestamp"),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
            "recorded_cost_usd": usage.get("cost_usd"),
            "cost_turns_unreported": usage.get("cost_turns_unreported"),
            "generations_total": len(gen_ids),
            "generations_fetched": 0,
            "generations_pending": 0,
            "authoritative_cost_usd": None,
            "unreconcilable": not gen_ids,
        }
        if not gen_ids:
            rows.append(row)
            continue
        row["generations_attributed_elsewhere"] = 0

        partial = 0.0
        fetched = 0
        for gen_id in gen_ids:
            entry = known.get(gen_id)
            if entry is None:
                gen = billing.generation(gen_id)
                if gen is None:
                    continue
                entry = _sidecar_entry(cycle, record_id, gen)
                known[gen_id] = entry
                new_entries.append(entry)
            fetched += 1
            owner = entry.get("record_id")
            if owner is not None and record_id is not None and owner != record_id:
                # Already charged to the record that first referenced it
                # (same run or an earlier one); never count a generation twice.
                row["generations_attributed_elsewhere"] += 1
                continue
            partial += float(entry["usage_usd"])
        row["generations_fetched"] = fetched
        row["generations_pending"] = len(gen_ids) - fetched
        if row["generations_pending"] == 0:
            row["authoritative_cost_usd"] = partial
        else:
            row["authoritative_cost_usd_partial"] = partial
        rows.append(row)

    if new_entries:
        with open(sidecar, "a") as f:
            for entry in new_entries:
                f.write(json.dumps(entry, default=str) + "\n")
    return rows


def summarize(rows: list[dict]) -> dict:
    recorded = 0.0
    complete = 0.0
    partial = 0.0
    unreconcilable = 0
    pending = 0
    for row in rows:
        if row.get("unreconcilable"):
            unreconcilable += 1
        cost = row.get("recorded_cost_usd")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            recorded += float(cost)
        if row.get("generations_pending"):
            pending += 1
            partial += float(row.get("authoritative_cost_usd_partial") or 0.0)
        elif row.get("authoritative_cost_usd") is not None:
            complete += float(row["authoritative_cost_usd"])
    return {
        "cycles": len(rows),
        "cycles_unreconcilable": unreconcilable,
        "cycles_pending": pending,
        "recorded_cost_usd": recorded,
        "authoritative_cost_usd_complete": complete,
        "authoritative_cost_usd_partial": partial,
    }


# --- CLI --------------------------------------------------------------------


def _fmt_usd(value) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:.4f}"
    return "-"


def _print_reconcile(rows: list[dict], out) -> None:
    print(f"{'cycle':>6} {'recorded':>10} {'authoritative':>14} "
          f"{'gens':>5} {'pending':>8} {'in_tokens':>10} note", file=out)
    for row in rows:
        if row.get("unreconcilable"):
            note = "unreconcilable: no generation ids in record"
        elif row.get("generations_pending"):
            note = (f"pending: partial "
                    f"{_fmt_usd(row.get('authoritative_cost_usd_partial'))}")
        else:
            rec = row.get("recorded_cost_usd")
            auth = row.get("authoritative_cost_usd")
            if isinstance(rec, (int, float)) and isinstance(auth, (int, float)):
                note = f"delta {auth - rec:+.6f}"
            else:
                note = ""
        print(f"{str(row.get('cycle')):>6} {_fmt_usd(row.get('recorded_cost_usd')):>10} "
              f"{_fmt_usd(row.get('authoritative_cost_usd')):>14} "
              f"{row.get('generations_total'):>5} {row.get('generations_pending'):>8} "
              f"{str(row.get('input_tokens') or '-'):>10} {note}", file=out)
    s = summarize(rows)
    print(file=out)
    print(f"cycles {s['cycles']}  unreconcilable {s['cycles_unreconcilable']}  "
          f"pending {s['cycles_pending']}", file=out)
    print(f"recorded {s['recorded_cost_usd']:.4f} USD   "
          f"authoritative (complete cycles) {s['authoritative_cost_usd_complete']:.4f} USD   "
          f"partial (pending cycles) {s['authoritative_cost_usd_partial']:.4f} USD",
          file=out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hamutay.billing",
        description="Ask OpenRouter what a session actually cost.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("credits", help="Account total spend and remaining balance.")
    gen = sub.add_parser("generation", help="One generation's authoritative record.")
    gen.add_argument("generation_id")
    rec = sub.add_parser(
        "reconcile",
        help="Fetch every generation a log recorded; persist to <log>.billing.jsonl; "
             "report recorded vs authoritative cost per cycle.",
    )
    rec.add_argument("--log-path", required=True)
    rec.add_argument("--json", action="store_true", help="Emit rows as JSON lines.")
    return parser


def main(argv: list[str] | None = None, http: HTTPGet | None = None) -> None:
    args = build_parser().parse_args(argv)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is not set")
    billing = OpenRouterBilling(api_key=api_key, http=http)

    if args.command == "credits":
        c = billing.credits()
        print(f"total_credits {c['total_credits']:.2f} USD")
        print(f"total_usage   {c['total_usage']:.2f} USD")
        print(f"remaining     {c['remaining']:.2f} USD")
        return
    if args.command == "generation":
        gen = billing.generation(args.generation_id)
        if gen is None:
            print(f"{args.generation_id}: not visible yet (404)")
            return
        print(json.dumps(gen, indent=2))
        return
    if args.command == "reconcile":
        rows = reconcile_log(args.log_path, billing)
        if args.json:
            for row in rows:
                print(json.dumps(row))
        else:
            _print_reconcile(rows, sys.stdout)
        return


if __name__ == "__main__":
    main()
