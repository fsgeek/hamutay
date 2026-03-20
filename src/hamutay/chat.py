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

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import anthropic

from hamutay.projector import Projector
from hamutay.tensor import Tensor
from hamutay.tensor_log import TensorLog


def _build_alu_messages(
    tensor: Tensor | None,
    user_message: str,
    cycle: int,
) -> tuple[list[dict], str]:
    """Build the messages for the reasoning model (the ALU).

    The ALU sees the current tensor as system context and the user's
    message as the prompt. It doesn't manage its own memory — that's
    the Projector's job.
    """
    system_parts = [
        "You are a helpful assistant engaged in an ongoing conversation. "
        "You have access to a projected state tensor that represents the "
        "accumulated context of this conversation. Use it to maintain "
        "coherence across the conversation's history.\n"
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
    ):
        self._client = client or anthropic.Anthropic()
        self._alu_model = alu_model
        self._projector = Projector(
            client=self._client,
            model=projector_model,
            on_tensor=on_tensor or (tensor_log if tensor_log else None),
        )
        self._tensor_log = tensor_log
        self._cycle = 0
        self._history: list[dict] = []  # raw exchanges for the session

    @property
    def tensor(self) -> Tensor | None:
        return self._projector.current_tensor

    @property
    def cycle(self) -> int:
        return self._cycle

    @property
    def projector(self) -> Projector:
        return self._projector

    def exchange(self, user_message: str) -> str:
        """One full exchange: user speaks, ALU responds, tensor updates.

        Returns the assistant's response text.
        """
        self._cycle += 1

        # 1. ALU generates response using current tensor as context
        messages, system = _build_alu_messages(
            self._projector.current_tensor,
            user_message,
            self._cycle,
        )

        response = self._client.messages.create(
            model=self._alu_model,
            max_tokens=8192,
            system=system,
            messages=messages,
        )

        assistant_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                assistant_text += block.text

        # 2. Project the exchange into the tensor
        projection_content = _build_projection_content(
            user_message, assistant_text, self._cycle
        )
        self._projector.project(projection_content)

        # 3. Record the exchange
        self._history.append({
            "cycle": self._cycle,
            "user": user_message,
            "assistant": assistant_text,
            "tensor_tokens": self._projector.current_tensor.token_estimate()
            if self._projector.current_tensor else 0,
            "alu_usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        })

        return assistant_text


def run_cli(
    alu_model: str = "claude-sonnet-4-20250514",
    projector_model: str = "claude-haiku-4-5-20251001",
    log_path: str | None = None,
):
    """Run an interactive chat session in the terminal."""

    if log_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_dir = Path("experiments") / "chat"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = str(log_dir / f"session_{ts}.jsonl")

    tensor_log = TensorLog(log_path)
    session = ChatSession(
        alu_model=alu_model,
        projector_model=projector_model,
        tensor_log=tensor_log,
    )

    print(f"Hamutay chat — tensor-projected conversation")
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
            t = session.tensor
            if t is None:
                print("(no tensor yet)")
            else:
                print(t.model_dump_json(indent=2))
            print()
            continue

        if user_input.lower() == "usage":
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

    # Summary
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
    args = parser.parse_args()

    run_cli(
        alu_model=args.alu_model,
        projector_model=args.projector_model,
        log_path=args.log_path,
    )


if __name__ == "__main__":
    main()
