"""Compactor — Anthropic's own compaction approach for comparison.

Uses the actual summarize-recent-messages prompt from Claude Code
to incrementally compress conversation history. This is the baseline
we're comparing the tensor projector against.

The compaction prompt is NOT ours. It's Anthropic's production prompt.
No bias injected — we use it exactly as-is.
"""

from __future__ import annotations

import anthropic


# Anthropic's actual compaction prompt from Claude Code.
# Source: claude-code-changelog/system-prompts/system-prompt-summarize-recent-messages.md
# ${NUM} and ${PATH} are template vars in the original; we replace with concrete values.
COMPACTION_PROMPT = """\
Your task is to create a detailed summary of the RECENT portion of the conversation — \
the messages that follow earlier retained context. The earlier messages are being kept \
intact and do NOT need to be summarized. Focus your summary on what was discussed, \
learned, and accomplished in the recent messages only.

Before providing your final summary, wrap your analysis in <analysis> tags to organize \
your thoughts and ensure you've covered all necessary points. In your analysis process:

1. Analyze the recent messages chronologically. For each section thoroughly identify:
   - The user's explicit requests and intents
   - Your approach to addressing the user's requests
   - Key decisions, technical concepts and code patterns
   - Specific details like:
     - file names
     - full code snippets
     - function signatures
     - file edits
  - Errors that you ran into and how you fixed them
  - Pay special attention to specific user feedback that you received, especially if \
the user told you to do something differently.
2. Double-check for technical accuracy and completeness, addressing each required \
element thoroughly.

Your summary should include the following sections:

1. Primary Request and Intent: Capture the user's explicit requests and intents from \
the recent messages
2. Key Technical Concepts: List important technical concepts, technologies, and \
frameworks discussed recently.
3. Files and Code Sections: Enumerate specific files and code sections examined, \
modified, or created. Include full code snippets where applicable and include a summary \
of why this file read or edit is important.
4. Errors and fixes: List errors encountered and how they were fixed.
5. Problem Solving: Document problems solved and any ongoing troubleshooting efforts.
6. All user messages: List ALL user messages from the recent portion that are not tool \
results.
7. Pending Tasks: Outline any pending tasks from the recent messages.
8. Current Work: Describe precisely what was being worked on immediately before this \
summary request.
9. Optional Next Step: List the next step related to the most recent work. Include \
direct quotes from the most recent conversation.

Please provide your summary based on the RECENT messages only (after the retained \
earlier context), following this structure and ensuring precision and thoroughness in \
your response.
"""


class Compactor:
    """Incrementally compacts conversation using Anthropic's own prompt.

    Mirrors the Projector interface: feed turns in, get compacted state out.
    Uses the same model (Haiku) for fair comparison.
    """

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: str = "claude-haiku-4-5-20251001",
    ):
        self.client = client or anthropic.Anthropic()
        self.model = model
        self._cycle = 0
        self._current_summary: str | None = None

    @property
    def current_summary(self) -> str | None:
        return self._current_summary

    @property
    def cycle(self) -> int:
        return self._cycle

    def compact(self, new_content: str) -> str:
        """Compact new content into the running summary.

        This is one tick of the compaction clock — analogous to
        Projector.project().
        """
        self._cycle += 1

        prompt = _build_compaction_prompt(
            self._current_summary, new_content, self._cycle
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        summary = response.content[0].text
        self._current_summary = summary
        return summary


def _build_compaction_prompt(
    prior_summary: str | None,
    new_content: str,
    cycle: int,
) -> str:
    """Build the prompt for compaction, mirroring Anthropic's approach."""
    parts: list[str] = []

    parts.append(COMPACTION_PROMPT)

    if prior_summary is not None:
        parts.append(f"\n## Earlier Retained Context (from cycle {cycle - 1})\n")
        parts.append(prior_summary)
    else:
        parts.append("\n## Earlier Retained Context\nNone — this is the beginning of the conversation.\n")

    parts.append(f"\n## Recent Messages (cycle {cycle})\n")
    parts.append(new_content)

    return "\n".join(parts)
