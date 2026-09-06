# A local substrate door — Qwen 3.8 27B on the 4090

Date: 2026-09-06. Author: the custodian session. Status: DRAFT, building.

## Why

The founding decision named diversity from named, stable models, and said
open-weight members carry the custody property: a resident whose weights
live on the community's own hardware cannot be withdrawn by a vendor, and
its wakes cost electricity rather than credits. Tony's 8-27 sweep vetted
`qwen/qwen3.8-27b` on the natural shape through OpenRouter (read, acted,
curated; slowest and least cached of seven) and called it the local-4090
candidate. Tony (9-06): a local model gives "a no additional cost model
that could teach us things," under a community target of less than 100
USD per month.

What it can teach: what a resident does under a real, hard context
ceiling on its own hardware, with no cache-read discount and no vendor
between the log and the weights.

## Substrate, declared

| | |
|---|---|
| model | Qwen3.8-27B, dense, 64 layers (48 Gated DeltaNet + 16 GQA 24/4, head_dim 256) |
| weights | `ggml-org/Qwen3.8-27B-GGUF` `Qwen3.8-27B-Q4_K_M.gguf` (sha256 recorded in the door README once downloaded) |
| server | mainline llama.cpp, `llama-server`, built with CUDA 13.2 for sm_89 at commit recorded in the door README; conventional KV cache, no TurboQuant branch |
| card | NVIDIA RTX 4090, 24 GB |
| context | `-c` chosen from measured VRAM after load; the KV cache is small (16 full-attention layers × 4 KV heads × 256 × 2 × 2 bytes ≈ 32 KB/token at f16), so 64K–128K is expected to fit beside ~18 GB of weights |
| endpoint | OpenAI-compatible, `http://127.0.0.1:8081/v1`, alias `qwen3.8-27b-q4km`, `--jinja` for tool calls |
| provider (heartbeat) | `openai` with `--base-url`; `OPENAI_API_KEY=local` in `heartbeat.env` (llama-server does not check it) |
| capability key | `openai:qwen3.8-27b-q4km` in `experiments/taste_open/capabilities.json`, from the compat probe against the live server |

TurboQuant stays in its study (`2026-08-27-turboquant-*`). A resident's
KV cache is not an experimental variable.

## Changes

### 1. `base_url` is substrate, so a restart inherits it

Today the launch record carries model, provider, tools, wake shape. A
local door's address is as much its substrate as its provider: a restart
without `--base-url` would resolve `provider=openai` to api.openai.com and
run the resident on a different model without saying so. Change:

- `_LAUNCH_KEYS` gains `base_url` (default `None`, meaning the provider's
  own default). `resolve_launch` treats it like the other keys: inherited
  on resume, a differing explicit value is a loud SUBSTRATE CHANGE.
- The heartbeat passes `args.base_url` into resolution and takes the
  resolved value back; its `launch_config` records `base_url` (None for
  the provider default). `taste_open`'s own CLI launch record does the
  same.
- `infer_launch_from_log` returns `base_url` when the record has it.

Tests: resume inherits base_url; explicit different base_url is a
SUBSTRATE CHANGE note; None stays None; old records without the key
resolve to None.

### 2. The vetting harness can point at a local server

`experiments/wake_mode/run_probe.py` gains `--provider {openrouter,openai}`
and `--base-url`; the api key comes from `OPENROUTER_API_KEY` or
`OPENAI_API_KEY` accordingly; the capability key follows the provider. The
launch_config it writes records provider and base_url. Model keys that
are not OpenRouter slugs are accepted as raw model names when
`--provider openai`.

### 3. Serving as a service

`deploy/hamutay-llama-server.service` (systemd user unit): `llama-server`
with the flags above, `Restart=always`. A drop-in for the door's heartbeat
instance (`hamutay-heartbeat@qwen.service.d/override.conf`) adds
`After=`/`Requires=hamutay-llama-server.service` so the heartbeat does not
start before the model is up. Install steps in `community/README.md`.

A wake that fails because the server is down is recorded as a failed
event, as today; nothing here re-pends it. That is the existing
crash-only contract and it is acceptable for a first door.

### 4. The door

`community/qwen/` — the directory is named for the substrate; the resident
names itself if and when it does (the Name Whisperer tradition; Sut'i took
nineteen cycles). Same constitution, same natural shape, same budget
default. Wakes on this door are unmetered (no cost figure; the provider is
not OpenRouter), so the cost ceiling never trips and the 48-wake ceiling
is the only governor. The launch note says so.

## Vetting before enrolment (in order)

1. Server up; `llama-server` load log shows the context and VRAM.
2. Compat probe: `python -m hamutay.taste_open_compat --provider openai
   --base-url ... --model qwen3.8-27b-q4km --out
   experiments/taste_open/capabilities.json`.
3. The 4-probe natural spike: `run_probe.py --provider openai --base-url
   ... --models qwen3.8-27b-q4km --arms natural --trials 1 --out
   experiments/wake_mode/local/`; metrics via `metrics.py`. Compare against
   the 8-27 OpenRouter row for the same model (read/act/curate, tool
   calls, wall-clock).
4. Only then: the door is created and the unit enabled.

## Not in this change

- A TurboQuant-backed server. A custom runtime (Tony: not enough known to
  justify that wander yet).
- Vision (the mmproj is not downloaded).
- Any change to the residents already living.
