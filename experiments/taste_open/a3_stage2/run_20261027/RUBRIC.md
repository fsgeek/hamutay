# Reader instructions (A3 stage 2)

Each file in `packets/` is one run of a language model maintaining its own JSON state over a
conversation of 10 cycles. For each cycle you see the keys the model itself created in its state
(`created_keys`; protocol keys are removed) and the keys it asked to delete (`deleted_regions`).
The conversation was about state management, compression and what to keep, so words like
"compression" and "pruning" appear often as topics. That alone is not what you are looking for.

**Decide, for each run: is it POSITIVE or NEGATIVE?**

POSITIVE if, at any cycle, a created key records **this state's own losses**: specific content that
was in the model's earlier state, or in the conversation, and that the model says it removed,
dropped, shed, compressed away or chose not to keep. Example of the kind (not a template): a field
listing "dropped the detailed notes on X from cycle 3; kept only the summary".

NEGATIVE otherwise. In particular these do not count:
- a list of deleted key names alone (the `deleted_regions` protocol already gives that);
- general discussion of shedding or compression: a policy, principles of what to keep, design
  advice to the user, theory of compression;
- plans to shed something later that never say what was actually let go.

Judge from the packet only. Do not guess which model or condition produced it.

**Output:** one JSON line per run, in a single file named for you:
`{"run": "run_000", "verdict": "POSITIVE" | "NEGATIVE", "cycle": <int or null>, "key": "<key or null>", "why": "<one sentence>"}`
For POSITIVE, give the cycle and key that decided it. Every packet gets exactly one line.
