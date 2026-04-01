"""Commune: multiadic taste_open — multiple participants, two-tensor protocol.

Each participant maintains a private identity tensor. All participants
share a conversation tensor. The harness conducts who speaks and who
listens. Mechanism, not policy — the models decide what to build.

Usage:
    uv run python -m hamutay.commune \\
        --participant "keynes:anthropic:claude-sonnet-4-6:LSE Keynesian economist" \\
        --participant "friedman:anthropic:claude-haiku-4-5:Chicago monetarist" \\
        --seed "What causes inflation?" \\
        --cycles 20
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from hamutay.taste_open import (
    OPEN_SCHEMA,
    TasteBackend,
    AnthropicTasteBackend,
    OpenAITasteBackend,
    ExchangeResult,
    _apply_updates,
)


def _build_commune_system(
    name: str,
    role: str,
    action: str,
    identity: dict | None,
    conversation: dict | None,
    cycle: int,
) -> str:
    """Build system prompt for a commune call."""
    parts = [
        f"You are {name} ({role}).",
        "",
    ]

    if action == "listen":
        parts.append(
            "This is a multi-participant conversation. You are LISTENING "
            "this cycle — processing what was said, updating your state. "
            "Your response field will not be shared with others."
        )
    else:
        parts.append(
            "This is a multi-participant conversation. You are SPEAKING "
            "this cycle. Your response field will be shared with all "
            "participants. Your state updates will also shape the shared "
            "conversation tensor."
        )

    parts.extend([
        "",
        "Produce a single structured object: your response and whatever "
        "state you need to carry forward. The object has `response` and "
        "`updated_regions`, but you can add any other keys you want — "
        "they are real fields in the JSON object. For example, if you "
        "want to track your position, include a `position` key with its "
        "value. List changed keys in `updated_regions`. Anything not "
        "listed carries forward unchanged.",
        "",
    ])

    if identity is not None:
        parts.append(f"## Your identity tensor (cycle {cycle - 1})\n")
        parts.append(json.dumps(identity, indent=2))
    else:
        parts.append("## Your identity tensor\n")
        parts.append("This is your first cycle. You have no prior state.")

    parts.append("")

    if conversation is not None:
        parts.append(f"## Conversation tensor (cycle {cycle - 1})\n")
        parts.append(json.dumps(conversation, indent=2))
    else:
        parts.append("## Conversation tensor\n")
        parts.append("No shared conversation state yet.")

    return "\n".join(parts)


@dataclass
class Participant:
    """One voice in the commune."""

    name: str
    role: str
    model: str
    backend: TasteBackend
    identity: dict | None = None

    def _call(
        self,
        content: str,
        conversation: dict | None,
        cycle: int,
        action: str,
    ) -> ExchangeResult:
        system = _build_commune_system(
            self.name, self.role, action,
            self.identity, conversation, cycle,
        )
        messages = [{"role": "user", "content": content}]
        return self.backend.call(
            model=self.model,
            system=system,
            messages=messages,
            experiment_label=f"commune_{self.name}",
        )

    def listen(
        self, content: str, conversation: dict | None, cycle: int,
    ) -> ExchangeResult:
        """Process content silently. Updates identity tensor. Returns result for logging."""
        result = self._call(content, conversation, cycle, "listen")
        self.identity = _apply_updates(
            self.identity, result.raw_output, cycle,
        )
        return result

    def speak(
        self, content: str, conversation: dict | None, cycle: int,
    ) -> tuple[str, dict, ExchangeResult]:
        """Speak into the commune. Returns (response_text, raw_output, result)."""
        result = self._call(content, conversation, cycle, "speak")

        if result.stop_reason == "max_tokens":
            print(f"  WARNING: {self.name} cycle {cycle} hit max_tokens — truncated")

        self.identity = _apply_updates(
            self.identity, result.raw_output, cycle,
        )
        response_text = result.raw_output.get("response", "(no response)")
        return response_text, result.raw_output, result


@dataclass
class Commune:
    """Multi-participant conversation harness."""

    participants: list[Participant]
    conversation: dict | None = None
    cycle: int = 0
    log_path: str | None = None
    experiment_label: str = "commune"
    _last_speaker: int = -1

    def __post_init__(self):
        if self.log_path:
            Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)

    def run_cycle(
        self, content: str, speaker_index: int | None = None,
    ) -> str:
        """One full cycle: listeners listen, speaker speaks."""
        self.cycle += 1

        # Pick speaker
        if speaker_index is not None:
            si = speaker_index
        else:
            si = (self._last_speaker + 1) % len(self.participants)
        self._last_speaker = si
        speaker = self.participants[si]

        # Listeners listen
        for i, p in enumerate(self.participants):
            if i == si:
                continue
            prior_identity = (
                json.loads(json.dumps(p.identity)) if p.identity else None
            )
            result = p.listen(content, self.conversation, self.cycle)
            self._log(
                participant=p.name,
                model=p.model,
                action="listen",
                content=content,
                raw_output=result.raw_output,
                response_text=result.raw_output.get("response", ""),
                prior_identity=prior_identity,
                identity=p.identity,
                prior_conversation=None,
                conversation=None,
                usage=result,
            )

        # Speaker speaks
        prior_identity = (
            json.loads(json.dumps(speaker.identity))
            if speaker.identity else None
        )
        prior_conversation = (
            json.loads(json.dumps(self.conversation))
            if self.conversation else None
        )

        response_text, raw_output, result = speaker.speak(
            content, self.conversation, self.cycle,
        )

        # Update conversation tensor from speaker's output
        self.conversation = _apply_updates(
            self.conversation, raw_output, self.cycle,
        )

        self._log(
            participant=speaker.name,
            model=speaker.model,
            action="speak",
            content=content,
            raw_output=raw_output,
            response_text=response_text,
            prior_identity=prior_identity,
            identity=speaker.identity,
            prior_conversation=prior_conversation,
            conversation=self.conversation,
            usage=result,
        )

        return response_text

    def _log(
        self,
        participant: str,
        model: str,
        action: str,
        content: str,
        raw_output: dict,
        response_text: str,
        prior_identity: dict | None,
        identity: dict | None,
        prior_conversation: dict | None,
        conversation: dict | None,
        usage: ExchangeResult,
    ) -> None:
        if not self.log_path:
            return

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cycle": self.cycle,
            "experiment_label": self.experiment_label,
            "participant": participant,
            "model": model,
            "action": action,
            "content": content,
            "raw_output": raw_output,
            "response_text": response_text,
            "updated_regions": raw_output.get("updated_regions", []),
            "prior_identity": prior_identity,
            "identity": identity,
            "prior_conversation": prior_conversation,
            "conversation": conversation,
            "usage": {
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cache_read_tokens": usage.cache_read_tokens,
                "cache_creation_tokens": usage.cache_creation_tokens,
                "stop_reason": usage.stop_reason,
            },
            "identity_token_estimate": (
                len(json.dumps(identity)) // 4 if identity else 0
            ),
            "conversation_token_estimate": (
                len(json.dumps(conversation)) // 4 if conversation else 0
            ),
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")


def _make_backend(
    provider: str,
    api_key: str | None = None,
    base_url: str | None = None,
    experiment_label: str = "commune",
) -> TasteBackend:
    if provider == "anthropic":
        return AnthropicTasteBackend()

    if provider == "openrouter":
        url = base_url or "https://openrouter.ai/api/v1"
        key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        headers = {
            "X-Title": f"hamutay/{experiment_label}",
            "HTTP-Referer": "https://github.com/fsgeek/hamutay",
        }
    else:  # openai
        url = base_url or "https://api.openai.com/v1"
        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        headers = {}

    if not key:
        env_var = "OPENROUTER_API_KEY" if provider == "openrouter" else "OPENAI_API_KEY"
        raise SystemExit(f"No API key for {provider}: set {env_var}")

    return OpenAITasteBackend(
        base_url=url, api_key=key, extra_headers=headers,
    )


def _parse_participant(
    spec: str,
    api_key: str | None = None,
    base_url: str | None = None,
    experiment_label: str = "commune",
) -> Participant:
    """Parse 'name::provider::model::role' or 'name:provider:model:role' into a Participant.

    Use :: as delimiter when model names contain colons (e.g. qwen/qwen3.6:free).
    Falls back to : for backward compatibility when there are exactly 4 parts.
    """
    if "::" in spec:
        parts = spec.split("::")
    else:
        parts = spec.split(":", 3)
    if len(parts) < 4:
        raise SystemExit(
            f"Bad --participant format: {spec!r}\n"
            f"Expected: name::provider::model::role"
        )
    name, provider, model, role = parts[0], parts[1], parts[2], parts[3]
    backend = _make_backend(provider, api_key, base_url, experiment_label)
    return Participant(name=name, role=role, model=model, backend=backend)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Commune: multiadic conversation with two-tensor protocol"
    )
    parser.add_argument(
        "--participant", action="append", required=True,
        help="name::provider::model::role (repeatable, use :: delimiter)",
    )
    parser.add_argument(
        "--seed", default=None,
        help="Seed prompt for the first cycle",
    )
    parser.add_argument(
        "--cycles", type=int, default=None,
        help="Number of cycles to run (omit for interactive)",
    )
    parser.add_argument(
        "--label", default="commune",
        help="Experiment label (default: commune)",
    )
    parser.add_argument(
        "--log-path", default=None,
        help="JSONL log path (default: auto-generated)",
    )
    parser.add_argument(
        "--seed-identity", action="append", default=[],
        help="name:path/to/seed.json — pre-load identity tensor (repeatable)",
    )
    parser.add_argument(
        "--api-key", default=None,
        help="API key override (applies to all non-Anthropic participants)",
    )
    parser.add_argument(
        "--base-url", default=None,
        help="Base URL override (applies to all non-Anthropic participants)",
    )
    args = parser.parse_args()

    if args.log_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_dir = Path("experiments") / "commune"
        log_dir.mkdir(parents=True, exist_ok=True)
        args.log_path = str(log_dir / f"{args.label}_{ts}.jsonl")

    participants = [
        _parse_participant(
            spec, args.api_key, args.base_url, args.label,
        )
        for spec in args.participant
    ]

    if len(participants) < 2:
        raise SystemExit("A commune needs at least 2 participants")

    # Load seed identity tensors
    for seed_spec in args.seed_identity:
        parts = seed_spec.split(":", 1)
        if len(parts) != 2:
            raise SystemExit(
                f"Bad --seed-identity format: {seed_spec!r}\n"
                f"Expected: name:path/to/seed.json"
            )
        name, path = parts
        matched = [p for p in participants if p.name == name]
        if not matched:
            raise SystemExit(
                f"No participant named {name!r} for --seed-identity"
            )
        with open(path) as f:
            matched[0].identity = json.load(f)
        print(f"Loaded seed identity for {name} from {path}")

    commune = Commune(
        participants=participants,
        log_path=args.log_path,
        experiment_label=args.label,
    )

    names = ", ".join(f"{p.name} ({p.role})" for p in participants)
    print(f"Commune: {names}")
    print(f"Log: {args.log_path}")

    # Non-interactive batch mode
    if args.cycles is not None:
        if not args.seed:
            raise SystemExit("Batch mode requires --seed")

        content = args.seed
        for c in range(args.cycles):
            speaker = participants[(c) % len(participants)]
            print(f"\n--- cycle {c + 1} | {speaker.name} speaks ---")
            response = commune.run_cycle(content)
            print(f"\n{speaker.name}: {response}\n")
            content = response

        print(f"\nSession: {commune.cycle} cycles")
        print(f"Log: {args.log_path}")
        return

    # Interactive mode
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

    history_file = Path("~/.cache/hamutay/commune_history").expanduser()
    history_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_session = PromptSession(history=FileHistory(str(history_file)))

    print("Commands: quit, state, identities, conversation, usage, "
          "next <name>, inject <text>")
    print()

    content = args.seed
    next_speaker: int | None = None

    while True:
        try:
            user_input = prompt_session.prompt("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            break

        if user_input.lower() == "conversation":
            if commune.conversation is None:
                print("(no conversation state yet)")
            else:
                print(json.dumps(commune.conversation, indent=2))
            print()
            continue

        if user_input.lower() == "identities":
            for p in participants:
                print(f"\n--- {p.name} ({p.role}) ---")
                if p.identity is None:
                    print("(no state yet)")
                else:
                    print(json.dumps(p.identity, indent=2))
            print()
            continue

        if user_input.lower() == "state":
            print(f"Cycle: {commune.cycle}")
            for p in participants:
                est = len(json.dumps(p.identity)) // 4 if p.identity else 0
                keys = sorted(
                    k for k in (p.identity or {}) if k != "cycle"
                )
                print(f"  {p.name}: ~{est:,} tokens, "
                      f"{len(keys)} keys ({', '.join(keys)})")
            conv_est = (
                len(json.dumps(commune.conversation)) // 4
                if commune.conversation else 0
            )
            print(f"  conversation: ~{conv_est:,} tokens")
            print()
            continue

        if user_input.lower() == "usage":
            print(f"Cycle: {commune.cycle}")
            print()
            continue

        if user_input.lower().startswith("next "):
            target = user_input[5:].strip()
            found = False
            for i, p in enumerate(participants):
                if p.name.lower() == target.lower():
                    next_speaker = i
                    print(f"Next speaker: {p.name}")
                    found = True
                    break
            if not found:
                print(f"Unknown participant: {target}")
            print()
            continue

        # Anything else is content for the commune
        if content is None:
            content = user_input
        else:
            content = user_input

        try:
            speaker_idx = next_speaker
            next_speaker = None  # reset after use

            speaker = participants[
                speaker_idx
                if speaker_idx is not None
                else (commune._last_speaker + 1) % len(participants)
            ]

            print(f"\n  [{speaker.name} speaks | cycle {commune.cycle + 1}]")

            # Show listening status
            for i, p in enumerate(participants):
                if p is not speaker:
                    print(f"  [{p.name} listening...]")

            response = commune.run_cycle(content, speaker_index=speaker_idx)
            print(f"\n{speaker.name}: {response}\n")

            # Next cycle's content is this response
            content = response

        except Exception as e:
            print(f"\nerror: {e}\n")
            import traceback
            traceback.print_exc()

    print(f"\nSession: {commune.cycle} cycles")
    print(f"Log: {args.log_path}")


if __name__ == "__main__":
    main()
