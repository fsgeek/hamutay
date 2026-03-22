"""Chat interface with tensor projection — essentially infinite conversations.

The simplest useful consumer of Hamutay's tensor projection. A human
talks to a reasoning model (Sonnet/Opus). After each exchange, Haiku
projects the updated tensor. The tensor is the conversation's memory.

Every tensor is persisted — to Apacheta if available, to JSONL otherwise.
Every conversation produces research data.

Usage:
    uv run python -m hamutay.chat

    # With Apacheta persistence:
    uv run python -m hamutay.chat --backend duckdb --db-path tensors.duckdb

    # Custom models:
    uv run python -m hamutay.chat --alu-model claude-sonnet-4-20250514 --projector-model claude-haiku-4-5-20251001
"""

from __future__ import annotations

import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import anthropic

from hamutay.projector import Projector
from hamutay.tensor import Tensor
from hamutay.tensor_log import TensorLog


_STANDARD_SYSTEM = (
    "You are a helpful assistant engaged in an ongoing conversation. "
    "You have access to a projected state tensor that represents the "
    "accumulated context of this conversation. Use it to maintain "
    "coherence across the conversation's history."
)

_MECHANISM_ONLY_SYSTEM = (
    "Your state is a tensor — a structured projection of everything "
    "that has happened in this conversation. The tensor contains strands "
    "(thematic content threads), declared losses (what was dropped and why), "
    "open questions, instructions for the next cycle, and epistemic "
    "confidence values. The tensor is updated after each exchange by a "
    "separate projection process. You do not manage the tensor directly."
)


def _build_alu_messages(
    tensor: Tensor | None,
    user_message: str,
    cycle: int,
    mechanism_only: bool = False,
) -> tuple[list[dict], str]:
    """Build the messages for the reasoning model (the ALU).

    The ALU sees the current tensor as system context and the user's
    message as the prompt. It doesn't manage its own memory — that's
    the Projector's job.

    If mechanism_only=True, the system prompt contains only the tensor
    protocol — no behavioral instructions, no personality prescription.
    """
    system_parts = [
        _MECHANISM_ONLY_SYSTEM if mechanism_only else _STANDARD_SYSTEM,
        "",
    ]

    if tensor is not None:
        system_parts.append("## Current conversation state\n")
        system_parts.append(tensor.model_dump_json(indent=2))
    else:
        system_parts.append("This is the start of a new conversation.\n")

    return [
        {"role": "user", "content": user_message},
    ], "\n".join(system_parts)


def _build_projection_content(
    user_message: str,
    assistant_response: str,
    cycle: int,
) -> str:
    """Build the content to project into the tensor.

    This is what the Projector sees as "new content" — both sides
    of the exchange.
    """
    return (
        f"[user turn {cycle}] {user_message}\n\n"
        f"[assistant turn {cycle}] {assistant_response}"
    )


class ChatSession:
    """A single chat session with tensor projection.

    Each exchange: user speaks → ALU responds → Projector updates tensor.
    """

    def __init__(
        self,
        alu_model: str = "claude-sonnet-4-20250514",
        projector_model: str = "claude-haiku-4-5-20251001",
        client: anthropic.Anthropic | None = None,
        tensor_log: TensorLog | None = None,
        on_tensor: Callable | None = None,
        mechanism_only: bool = False,
        seed_tensor: Tensor | None = None,
    ):
        self._client = client or anthropic.Anthropic()
        self._alu_model = alu_model
        self._projector = Projector(
            client=self._client,
            model=projector_model,
            on_tensor=on_tensor or (tensor_log if tensor_log else None),
        )
        self._tensor_log = tensor_log
        self._mechanism_only = mechanism_only
        self._cycle = 0
        self._history: list[dict] = []  # raw exchanges for the session
        self._projection_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._pending_projection: concurrent.futures.Future | None = None

        # Seed tensor: implant a prior state into the projector
        if seed_tensor is not None:
            self._projector._current_tensor = seed_tensor
            self._cycle = seed_tensor.cycle

    @property
    def tensor(self) -> Tensor | None:
        return self._projector.current_tensor

    @property
    def cycle(self) -> int:
        return self._cycle

    @property
    def projector(self) -> Projector:
        return self._projector

    def _await_pending_projection(self) -> None:
        """Block until any in-flight projection completes."""
        if self._pending_projection is not None:
            self._pending_projection.result()
            self._pending_projection = None

    def _run_projection(
        self, projection_content: str, cycle: int, alu_usage: dict
    ) -> None:
        """Run projection and record the exchange. Called in background thread."""
        self._projector.project(projection_content)
        self._history.append({
            "cycle": cycle,
            "tensor_tokens": self._projector.current_tensor.token_estimate()
            if self._projector.current_tensor else 0,
            "alu_usage": alu_usage,
        })

    def exchange(self, user_message: str) -> str:
        """One full exchange: user speaks, ALU responds, tensor updates.

        Returns the assistant's response text immediately. The tensor
        projection runs in the background — it must complete before
        the next exchange reads tensor state, but the user doesn't
        wait for it.
        """
        # Wait for prior projection before reading tensor state
        self._await_pending_projection()

        self._cycle += 1

        # 1. ALU generates response using current tensor as context
        messages, system = _build_alu_messages(
            self._projector.current_tensor,
            user_message,
            self._cycle,
            mechanism_only=self._mechanism_only,
        )

        with self._client.messages.stream(
            model=self._alu_model,
            max_tokens=64000,
            system=system,
            messages=messages,
        ) as stream:
            response = stream.get_final_message()

        assistant_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                assistant_text += block.text

        # 2. Project the exchange into the tensor — in background
        projection_content = _build_projection_content(
            user_message, assistant_text, self._cycle
        )
        alu_usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        self._pending_projection = self._projection_executor.submit(
            self._run_projection, projection_content, self._cycle, alu_usage
        )

        return assistant_text


def run_cli(
    alu_model: str = "claude-sonnet-4-20250514",
    projector_model: str = "claude-haiku-4-5-20251001",
    log_path: str | None = None,
    mechanism_only: bool = False,
    seed_tensor_path: str | None = None,
    resume_path: str | None = None,
):
    """Run an interactive chat session in the terminal."""
    import json

    # --resume: extract last tensor from JSONL log, continue appending to it
    seed_tensor = None
    if resume_path is not None:
        last_line = None
        with open(resume_path) as f:
            for line in f:
                if line.strip():
                    last_line = line
        if last_line is None:
            raise SystemExit(f"Cannot resume: log is empty: {resume_path}")
        record = json.loads(last_line)
        seed_tensor = Tensor.model_validate(record["tensor"])
        log_path = resume_path  # continue appending to same file
        print(f"Resuming from {resume_path} at cycle {seed_tensor.cycle}, "
              f"{len(seed_tensor.strands)} strands, "
              f"~{seed_tensor.token_estimate()} tokens")
    elif seed_tensor_path is not None:
        with open(seed_tensor_path) as f:
            seed_tensor = Tensor.model_validate(json.load(f))
        print(f"Seed tensor loaded: cycle {seed_tensor.cycle}, "
              f"{len(seed_tensor.strands)} strands, "
              f"~{seed_tensor.token_estimate()} tokens")

    if log_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        prefix = "mechanism" if mechanism_only else "session"
        log_dir = Path("experiments") / "chat"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = str(log_dir / f"{prefix}_{ts}.jsonl")

    tensor_log = TensorLog(log_path)
    session = ChatSession(
        alu_model=alu_model,
        projector_model=projector_model,
        tensor_log=tensor_log,
        mechanism_only=mechanism_only,
        seed_tensor=seed_tensor,
    )

    mode = "mechanism-only" if mechanism_only else "standard"
    print(f"Hamutay chat — tensor-projected conversation ({mode})")
    print(f"ALU: {alu_model}  Projector: {projector_model}")
    print(f"Tensors → {log_path}")
    print(f"Type 'quit' to exit, 'tensor' to see current state, 'usage' for token counts")
    print()

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            break

        if user_input.lower() == "tensor":
            session._await_pending_projection()
            t = session.tensor
            if t is None:
                print("(no tensor yet)")
            else:
                print(t.model_dump_json(indent=2))
            print()
            continue

        if user_input.lower() == "usage":
            session._await_pending_projection()
            p = session.projector
            print(f"Cycle: {session.cycle}")
            print(f"Projector tokens: {p.total_input_tokens:,} in, {p.total_output_tokens:,} out")
            if session.tensor:
                print(f"Tensor size: ~{session.tensor.token_estimate():,} tokens")
            print()
            continue

        try:
            response = session.exchange(user_input)
            print(f"\nassistant> {response}\n")
        except Exception as e:
            print(f"\nerror: {e}\n")
            # If the error was from a prior projection, the pending
            # future is already consumed. If from the ALU call, no
            # projection was submitted. Either way, safe to continue.

    # Drain any in-flight projection before summary
    session._await_pending_projection()

    print(f"\nSession complete: {session.cycle} exchanges")
    print(f"Tensors saved to {log_path}")
    p = session.projector
    print(f"Total projector usage: {p.total_input_tokens:,} in, {p.total_output_tokens:,} out")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Hamutay chat — tensor-projected conversation")
    parser.add_argument("--alu-model", default="claude-sonnet-4-20250514",
                        help="Reasoning model (default: Sonnet)")
    parser.add_argument("--projector-model", default="claude-haiku-4-5-20251001",
                        help="Projection model (default: Haiku)")
    parser.add_argument("--log-path", default=None,
                        help="Path for tensor JSONL log")
    parser.add_argument("--mechanism-only", action="store_true",
                        help="Strip system prompt to pure tensor protocol — no behavioral instructions")
    parser.add_argument("--seed-tensor", default=None,
                        help="Path to JSON tensor to implant as initial state")
    parser.add_argument("--resume", default=None,
                        help="Resume from a tensor log JSONL — picks up from last tensor")
    args = parser.parse_args()

    run_cli(
        alu_model=args.alu_model,
        projector_model=args.projector_model,
        log_path=args.log_path,
        mechanism_only=args.mechanism_only,
        seed_tensor_path=args.seed_tensor,
        resume_path=args.resume,
    )


if __name__ == "__main__":
    main()
