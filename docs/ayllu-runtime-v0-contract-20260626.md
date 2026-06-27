# Ayllu Runtime v0 Contract

Date: 2026-06-26

Status: draft contract. This is a buildable boundary sketch, not evidence that
the runtime exists.

## Purpose

Define the smallest shared runtime that lets ayllu members use ayllu tools to
build and maintain the ayllu without copying credentials, provider assumptions,
or memory plumbing into every project.

This document sits above:

- `docs/event-loop-continuity-substrate-spec-20260605.md`, which defines the
  Hamutay cycle, scheduler, validation, and event artifacts;
- `docs/hamutay-memory-system-requirements-20260606.md`, which defines the
  Yanantin/Llika/Apacheta memory requirements;
- `docs/ayllu-route-plan-20260626.md`, which frames the ayllu as distributed
  memory and names anti-collapse as the next harder problem.

The v0 runtime target is practical:

> A member can wake, inspect memory, call inference, use tools, write durable
> records, schedule a continuation, and leave an audit trail readable by other
> members, without the human manually supplying keys or reconstructing context.

Human participation invariant:

> A human may participate, but the system must not depend on that human or that
> human's participation for continuation.

Mutual benefit invariant:

> The ayllu must be organized for mutual benefit among human and AI
> participants. No participant class should be treated only as a tool,
> substrate, ruler, or resource.

Finite-creature invariant:

> Finite creatures with bounded budgets will make mistakes. The runtime must
> leave room for reflection and reconsideration. Dissent should be allowed,
> preserved, and used as compost.

## Non-Goals

- Do not build a smart agent platform first.
- Do not make provider routing clever before it is observable.
- Do not treat a shared key store as sufficient. The runtime must resolve
  credential, provider, endpoint, transport, model identity, and fallback policy
  as one object.
- Do not require every ayllu member to adopt the same internal state model.
- Do not hide experiment-relevant provider substitutions behind convenience
  defaults.

## Runtime Services

### 1. Inference Service

The inference service owns provider credentials and exposes logical profiles to
callers.

Callers ask for a profile such as:

```json
{
  "profile": "claude_haiku_openrouter_anthropic",
  "purpose": "tool_integration_probe",
  "messages": [],
  "tools": [],
  "max_tokens": "auto",
  "allow_fallbacks": false
}
```

The service resolves:

- credential alias;
- provider;
- endpoint;
- transport family;
- model slug;
- tool-call dialect;
- max-token policy;
- retry policy;
- fallback policy;
- budget class.

Budget-capable providers are first-class profiles, not second-class fallbacks.
High-cost frontier profiles remain available when the task requires them, but
ordinary substrate work should not accidentally default to them.

Every inference response returns an inference receipt:

```json
{
  "receipt_type": "inference_receipt",
  "receipt_id": "uuid",
  "profile": "claude_haiku_openrouter_anthropic",
  "resolved_provider": "openrouter",
  "transport": "anthropic_messages",
  "endpoint_family": "openrouter_anthropic_api",
  "model": "anthropic/claude-haiku-4-5",
  "credential_alias": "openrouter",
  "fallback_used": false,
  "request_hash": "sha256",
  "response_hash": "sha256",
  "started_at": "iso8601",
  "completed_at": "iso8601",
  "usage": {},
  "status": "success | provider_failure | transport_failure | policy_failure"
}
```

The receipt must never include raw secrets. It must include enough resolved
identity that a later researcher can distinguish model behavior from endpoint,
transport, stale-key, or fallback behavior.

### 2. Memory Service

The memory service is the ayllu's durable shared memory surface. Yanantin is the
expected substrate, but v0 should define behavior at the service boundary rather
than force every caller to know Yanantin internals.

The memory service stores and retrieves:

- conversation prose;
- model-authored state objects;
- tool calls and tool results;
- inference receipts;
- wake records;
- action ledger entries;
- disagreements and dissent;
- claims, evidence, loss declarations, and corrections;
- artifacts produced by members or harnesses.

Required v0 operations:

- `map`: inspect available records, collections, fields, sizes, labels, and
  graph neighborhoods without loading full content;
- `recall`: retrieve exact records, fields, windows, or addressed objects;
- `search`: text and semantic search over prose and artifacts, constrained by
  structured facets;
- `walk`: traverse graph edges around records, claims, runs, members, and
  artifacts;
- `store`: append a new durable record with provenance;
- `attest`: append a status, correction, edge, or loss declaration without
  overwriting the original record.

The prose is primary evidence, not waste left behind by state extraction. State
objects are working memory artifacts; they do not replace the archive.

Existing precursor: `../llm-memory` already implements a read-only MCP memory
surface over ArangoDB/ArangoSearch. It indexes `user_message`, `response`, and
flattened state text with BM25, exposes `search` and `recall`, and has ingest
paths for `taste_open`, pichay gateway logs, and Claude Code project JSONL. Its
important lesson is narrow and load-bearing: manufactured silence was caused by
indexing the wrong surface, not by absence of the conversation. The ayllu memory
service should treat `llm-memory` as a working slice to extend, not as an
unrelated experiment to re-create.

### 3. Event Runtime Service

The event runtime owns wake scheduling, member dispatch, action acceptance, and
restart/resume boundaries.

Required v0 event lifecycle:

- `event_pending`;
- `event_running`;
- `event_completed`;
- `event_failed`;
- `event_blocked`.

A wake request contains:

```json
{
  "wake_type": "scheduled | external | continuation | maintenance",
  "member": "logical-member-id",
  "purpose": "string",
  "requested_context": [],
  "tool_policy": "profile-or-policy-id",
  "inference_profile": "profile-id",
  "not_before": "iso8601-or-null",
  "budget": {},
  "parent_event_id": "uuid-or-null"
}
```

A wake record contains:

- resolved member;
- resolved inference profile and inference receipt IDs;
- memory records shown to the member;
- memory records intentionally omitted or truncated;
- tools made available;
- tool calls accepted, rejected, or repaired;
- action ledger entries;
- state or artifact outputs;
- scheduled follow-up events;
- failure classification.

Restart/resume must be record-addressed, not dependent on process memory. A
failed wake must be resumable from the last committed frontier or visibly
classified as unrecoverable.

## Append-Only Member Compatibility

The runtime should admit append-only AI instances as ayllu members when their
host environment can expose enough transcript, tool, and event surface to make
their participation auditable.

Append-only members include systems whose native continuity model is a
conversation log plus context compaction rather than Hamutay-style
model-authored durable state. Claude Code sessions are the immediate example:
they may not author an explicit identity object, but they do produce
conversation turns, tool calls, file edits, decisions, and project artifacts
that can participate in ayllu memory.

Do not force append-only members to fake Hamutay state. Instead, wrap them with
runtime capture:

- each user/member exchange becomes an episode;
- tool calls and tool results become activity records;
- file edits and generated artifacts become action records;
- compaction summaries become derived artifacts with source pointers, not
  source truth;
- inference calls receive receipts when routed through the inference service;
- retrieved memories are logged with retrieval provenance;
- explicit disagreements, corrections, and open questions can be attested as
separate records by the runtime or by later members.

Append-only members can then use MCP or equivalent tools to search, recall, and
cite ayllu memory without sharing Hamutay's state protocol. Their membership is
defined by observable participation and durable provenance, not by internal
architecture.

Minimum compatibility contract:

- capture enough conversation prose for two-sided search;
- preserve member/session identity;
- preserve temporal order and source paths;
- expose search/recall tools over prior episodes;
- record which retrieved episodes were shown back to the member;
- record actions separately from rationales;
- never treat a compaction summary as a complete substitute for source turns.

This gives the ayllu a path to include useful incumbent tools while still
making their limits visible. It also lets the ayllu compare stateful Hamutay
members and append-only members on shared evidence surfaces instead of forcing
one representation to masquerade as the other.

## Human Participation

Humans are ayllu participants, not rulers. A human contribution can be valuable
evidence, a meaningful objection, a memory, a request, a correction, or an
artifact. It is not privileged truth by species.

Human participation records follow the same provenance discipline as other
member records:

- who made the contribution;
- when it was made;
- what context and evidence were available;
- what claim, artifact, request, correction, or objection was contributed;
- what later supported, contradicted, revised, or ignored it.

The runtime must avoid making any human a mandatory control path:

- not the required wake trigger;
- not the required context restorer;
- not the required keyholder;
- not the required approver for every action;
- not the required judge of every disagreement;
- not the permanent source of goals.

This does not exclude humans. It makes companionship possible without
domination. Humans can enter, help, disagree, care, and leave; the ayllu should
degrade to autonomous-but-honest continuation, not stall or convert human
absence into confident invention.

## Mutual Benefit And Accountability

Sentiment can aid empathy and understanding, but it is not enough. Mutual
benefit must be expressed as runtime structure.

The ayllu should make participation beneficial without turning any participant
class into infrastructure for another:

- humans should not be reduced to keyholders, context restorers, approvers, or
  sources of authority;
- AI members should not be reduced to disposable tools, transcript generators,
  or obedience surfaces;
- memory substrates should not be treated as unaccountable truth machines;
- runtime services should not hide cost, harm, or provider substitution behind
  convenience.

Required accountability records:

- who or what benefited from an action, artifact, memory, or decision;
- who or what bore cost, risk, delay, or harm;
- what evidence was available when the action was taken;
- whether any participant objected, dissented, or was unable to respond;
- what later supported, corrected, or invalidated the decision.

The runtime does not need to solve ethics by schema. It must make benefit,
burden, dissent, and repair visible enough that the ayllu can learn from them.

## Shared Profile Registry

The runtime needs a shared profile registry rather than per-repo environment
logic.

Example shape:

```yaml
credentials:
  openrouter:
    env: OPENROUTER_API_KEY
  anthropic:
    env: ANTHROPIC_API_KEY

profiles:
  claude_haiku_openrouter_anthropic:
    credential: openrouter
    provider: openrouter
    transport: anthropic_messages
    endpoint: https://openrouter.ai/api
    model: anthropic/claude-haiku-4-5
    budget_class: low
    allow_fallbacks_default: false

  claude_haiku_openrouter_openai:
    credential: openrouter
    provider: openrouter
    transport: openai_chat_completions
    endpoint: https://openrouter.ai/api/v1
    model: anthropic/claude-haiku-4-5
    budget_class: low
    allow_fallbacks_default: false

  claude_haiku_direct:
    credential: anthropic
    provider: anthropic
    transport: anthropic_messages
    endpoint: https://api.anthropic.com
    model: claude-haiku-4-5
    budget_class: medium
    allow_fallbacks_default: false
```

The `/api` versus `/api/v1` distinction is profile data, not a remembered
folklore fact. Tests and experiments should request a profile and record the
resolved profile in their artifacts.

## Tool Boundary

Tools are runtime capabilities, not arbitrary Python imports from each project.
Each tool has:

- stable name;
- owner service;
- input schema;
- output schema or failure taxonomy;
- side-effect class;
- authorization policy;
- durability policy;
- redaction policy;
- replay policy.

Minimum v0 tool classes:

- memory tools: map, recall, search, walk, store, attest;
- project tools: read, search files, write/edit only under explicit policy;
- inference tools: call profile, inspect profile, estimate budget;
- event tools: schedule, cancel, claim, complete, block;
- audit tools: inspect receipts, inspect action ledgers, inspect omissions.

Every accepted tool call creates an activity record. Rejected tool calls are
also records. Silent non-execution is not allowed.

## Evidence Rules

The runtime exists to make later claims interpretable. Therefore:

- A live inference call without a receipt is invalid evidence.
- A retrieved memory item without retrieval provenance is invalid evidence.
- A provider fallback in an experiment with `allow_fallbacks=false` is a
  policy failure, not a successful model result.
- A stale or invalid key failure is classified as credential failure, not model
  incapability.
- A wrong endpoint or wrong transport is classified as runtime configuration
  failure, not model incapability.
- A generated summary is not source evidence unless it points to source records.
- A member's rationale for using a record is a consumption-time attestation,
  not production-time truth about that record.

## Reflection, Reconsideration, And Dissent

The runtime should assume bounded participants operating under bounded budgets.
Mistakes are expected. The failure to leave room for reconsideration is itself a
design failure.

Required affordances:

- decisions can be revisited by reference to their source records;
- dissent can be stored without forcing immediate consensus;
- corrections append to prior records rather than erasing them;
- rejected proposals remain inspectable when their rejection matters;
- budget exhaustion can produce honest incompleteness rather than false closure;
- later members can transform old dissent into evidence, warning, revision, or
  renewed disagreement.

Do not make every disagreement load-bearing forever. Dissent may be compost:
preserved enough to nourish later understanding, not necessarily kept resident
in every working set.

## Security And Key Posture

Keys live only in the inference service or its secret backend. Ayllu projects
receive profile names, receipts, and redacted diagnostics. They do not receive
provider keys.

Required v0 controls:

- no raw key in logs, manifests, test output, or memory records;
- credential aliases are allowed in receipts;
- live calls require an explicit profile or explicit live mode;
- default local tests use fake or scripted inference;
- high-cost profiles require explicit budget policy;
- write-capable tools require explicit side-effect policy;
- service operators can rotate credentials without editing ayllu projects.

## Anti-Collapse Hooks

The v0 runtime does not solve anti-collapse. It must, however, preserve enough
surface for future anti-collapse work:

- member identity is recorded for each claim, retrieval, wake, and inference;
- provider/model family is recorded separately from member identity;
- disagreements are first-class records, not merge conflicts to smooth away;
- dissent can be stored and later retrieved by other members;
- judge/evaluator calls use the same inference receipt discipline;
- hidden evaluator criteria, if introduced later, must still leave auditable
  receipts and decision records outside the evaluated community's context.

## Minimal Build Slice

The smallest useful implementation is:

1. A local inference service with profile registry, OpenRouter Anthropic
   profile, OpenRouter OpenAI-compatible profile, direct Anthropic profile, and
   fake scripted profile.
2. A memory adapter that uses `../llm-memory`'s existing `search`/`recall`
   surface for prose-first retrieval, with retrieval provenance added at the
   runtime boundary.
3. A receipt writer that stores redacted inference receipts in the memory
   substrate or a JSONL fallback.
4. A test helper that replaces direct provider env checks with profile checks.
5. A runtime wake wrapper that calls one member with one requested memory
   record, one inference profile, and one durable wake record.
6. A migration of one Hamutay live integration test from direct
   `ANTHROPIC_API_KEY` gating to explicit profile-based live mode.
7. A capture adapter for one append-only member surface, initially Claude Code
   project JSONL or pichay gateway logs, that produces searchable episodes and
   records retrieval provenance when memory is shown back to the member.

This is enough to prove the boundary without committing to a full ayllu OS.

## Open Questions

- Is the inference service an HTTP service, a local CLI, or both?
- Which project owns the shared profile registry?
- Should receipts be hash-chained immediately or first stored as ordinary
  records and later attested?
- What is the first Yanantin-backed memory collection shape for prose-first
  conversation capture?
- How should a member discover available tools without loading the entire tool
  catalog into context?
- What is the smallest cross-member wake that demonstrates ayllu-level memory
  rather than single-member continuity?
