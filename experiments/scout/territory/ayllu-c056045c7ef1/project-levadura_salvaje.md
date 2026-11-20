# source: github.com/fsgeek/levadura_salvaje README.md (origin/main@a485b08)

# Levadura Salvaje

*Bounded minds. Unbounded evidence. Wild fermentation.*

Dedicated to the creative influences of our ayllu, exploring and constantly asking questions.

##  Introduction

This project began on September 22, 2026.

It started when we asked dumb questions:

* What if the limited context window of an AI were not a defect to overcome?

* What if it were an architectural clue?

Much of contemporary AI development assumes that greater intelligence requires putting more of the world inside the model: larger context windows, larger prompts, larger retrieval sets, more tools, more state.

We ended up proposing nearly the opposite:

* Keep cognition small. Let the world remain large.

* A mind need not contain the evidence it reasons about. It needs ways to observe that evidence, measure it, ask new questions of it, remember what it learned, and return when something remains unresolved.

## What is here

- **[The seed](docs/the_seed.md)** is the founding proposal, committed unedited.
  **[The first wander](docs/first-wander.md)** records how it was challenged
  and what survived.
- **[The ledger](ledger/observations.jsonl)** is append-only and hash-chained.
  Every measurement records when the quantity held (`observed_at`), when it
  was computed (`recorded_at`) and the instrument that produced it.
  Interpretations elsewhere cite ledger ids. They never restate numbers from
  memory.
- **[Predictions](predictions/)** are written and OpenTimestamps-stamped
  before each measurement runs. The scorecards in `docs/` score them,
  failures included.
- **[What the ledger says so far](docs/findings-2026-09-24.md)** is the first
  corpus: 26 CFR (1997 and 2025) read against 26 USC. About one in five of the
  Code sections the regulations cite is repealed or missing, and most of those
  regulations still read as current law.
- **[The investigator](docs/investigator-design.md)**, the part of the thesis
  not yet built, is a design under adversarial review.

Every commit is signed and timestamped (`timestamps/`). Run
`scripts/install-hooks.sh` once after cloning, then `uv run pytest`.

