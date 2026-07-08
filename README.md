# Hamut'ay

**A mind that has to choose what to forget.**

A large language model has no memory. It has a context window, and we keep
mistaking one for the other. The context window feels like memory because
nothing falls out of it — but pile more onto it and the model works *worse*,
measurably (Du et al. 2025: length alone degrades performance 14–85%, even
when the relevant fact is right there). The desk is too big.

Hamut'ay starts from a single inversion: **treat the context window as a
cache, not as memory.** The interesting question stops being "how do we fit
more on the desk" and becomes the one every actual mind has to answer: *what
do we write down, and what do we let go?*

Instead of an append-only log with compaction, Hamut'ay projects a
conversation into a small, structured prose object — a **tensor** — on every
cycle: named strands of thought, open questions, a changelog of *what it just
threw away*, and instructions for the next cycle. (The word "tensor" here
means the structured prose object, not a numerical array.)

## What this repository is

Both an instrument and its record. It contains the framework, and the primary
experimental data behind the findings — **including the corrections to our own
overclaims, which are load-bearing evidence rather than errata.** The project
studies how a rewrite-memory forgets; it would be dishonest to hide its own
strata.

A few things we think we've learned (and how well we know each is tracked
conservatively in [`docs/paper-evidence-ledger.md`](docs/paper-evidence-ledger.md)):

- **It doesn't compress — it rewrites.** The wording barely survives cycle to
  cycle (~9% lexical survival), while the *meaning* stays close (0.870 mean
  content-embedding cosine). Memory as re-explanation, not storage.
- **The one thing a mind won't volunteer** is a record of what it discarded.
  Given a free schema, models invent scaffolding, planning, even
  tension-tracking — but never a declared-losses changelog. That honesty has
  to be designed in. It is the load-bearing part.
- **A model can manage its own memory** coherently over hundreds of cycles.
- **The mechanism underneath is stochastic, not a clock.** The "breathing" we
  fell in love with is real but aperiodic; the curation richness we hunted a
  cause for turned out to be a coin.

The narrative version of all this — including the four ways we were wrong, and
the fossil we think matters most — lives in
[`docs/blog-the-cache-not-the-memory.sanitized.md`](docs/blog-the-cache-not-the-memory.sanitized.md).

## Running it

There is no system Python; dependencies are managed with `uv`.

```
uv run python -m hamutay
```

starts a tensor-projected conversation. Every session produces research data
(tensor JSONL under `experiments/chat/`) — the chat interface is both a
demonstration and an instrument.

## Status

Early, ongoing research. The findings here are real and the corrections are
real; both are load-bearing. The frequencies we don't yet know (how often a
fossil is a false belief; how the curation basins are weighted) are the things
we're measuring next — and we'll try not to fall in love with the first answer.

## License

MIT — see [`LICENSE`](LICENSE). If you use this software or its findings,
citation metadata is in [`CITATION.cff`](CITATION.cff).
