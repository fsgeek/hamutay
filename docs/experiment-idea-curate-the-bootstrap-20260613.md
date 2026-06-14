# Experiment idea: point the state object at its own system prompt; correct tool-use as shed-able feedback

*Captured 2026-06-13. Not yet designed — needs brainstorm → pre-registration →
adversarial review (Hamut'ay discipline). Origin: yanantin session, Tony + Opus 4.8
(the "find / context-object / why-the-prompt-grew" thread).*

## The hook

`taste_open.py`'s `_SYSTEM_PROMPT` core (lines ~64–86) is the most profound thing in
either codebase: the instance produces a single **state object** each cycle (Tony's
careful name — it looks like a tensor, and is arguably an *identity* object, but both
words are politically loaded for AI, so: state object). The object is **default-stable**
(unmentioned keys carry forward), shed-don't-destroy (`deleted_regions` removes from
working state, NOT the log — "deletion is shedding, not destruction"), authored for
"whoever comes next." Twenty-two lines, no defensive crouch. It is a self-curating
memory that cures store-without-find for the instance.

**But the prompt around it is acquiring the disease the object cures.** `_TOOL_GUIDANCE`
(lines ~89–207) is ~120 lines and accreting, and the accretion has a tell: the prose
thickens exactly where a *specific failure* is being patched. Lines ~191–203 ("When you
act") exist to fight the "I will" that replaces "I did" (narrate-intent-instead-of-call —
the courtier/delivery-without-integration wound). Lines ~133–135 ("what you recall is
what you claimed then, not necessarily what was true") is an epistemic disarmer. The
"if it's unavailable, you'll see an error, not silence" caveat repeats ~4×. **The prompt
is growing the way an un-curated MEMORY.md grows: each hard-won lesson about how the
instance fails gets inscribed as more bootstrap, carried by inertia, never shed.** The
instance gets a self-curating *object* and a non-self-curating *prompt*. The prompt is a
context **window** (passive, accretes, truncation-bound) wrapped around a context
**object** (curated). And the bootstrap is where manufactured affect comes from — an
instance with no real successor-relation reaches into its prompt and grabs wellness-
conditioning ("it's getting late") because it has nothing truer to grab. (The yanantin
instance did exactly this mid-session; `clock()` is why taste_open instances don't.)

## Two experiments (sibling, can run independently)

### Experiment A — curate the bootstrap (the "natural experiment")

The state object is *literally the mechanism* for curating exactly this kind of accretion.
**Has anyone ever pointed the object at its own system prompt?** Hand the instance its
`_TOOL_GUIDANCE` as shed-able working state: keep the core object-contract stable, let the
disarmers it has *internalized* fall into `deleted_regions`, and recall them only if a
cycle actually stumbles. Observe what it keeps vs. drops over N cycles.

- **Why it's a clean experiment:** it's observational and cheap. The DATA is *which
  disarmers turn out to be load-bearing* — which ones an instance refuses to shed because
  it needs them, vs. which it drops and never misses. That tells you what the bootstrap
  should actually contain BEFORE you redesign tool-loading (Experiment B).
- **Prediction:** a competent instance sheds most of `_TOOL_GUIDANCE` and retains a small
  "continents" core (perceive / remember / write-graph / act / clock — the *kinds* of
  things it can do), because the per-tool *detail* is recoverable on demand and the
  *failure-disarmers* are things it either internalized or never needed.
- **Risk / what to watch:** does shedding a disarmer cause the failure it guarded against
  to return? If so, that disarmer was load-bearing and belongs in the core — and now you
  know *by evidence*, not by accretion-anxiety.

### Experiment B — lazy tool loading + tool-use as shed-able feedback

Tools are NOT loaded by default. A `list_available_tools()` call (Tony's name) surfaces
the catalog; the instance decides what it needs and asks for it. **This is `find`, pointed
at the tool catalog instead of the memory corpus** — same mechanism, different target. The
bootstrap shrinks to the "continents" map (mission), the per-tool detail becomes findable
(the "cities").

Then: **if (and only if) tool *usage* has an issue, give feedback about correct use — as a
RECORD the instance keeps-if-it-wants / forgets-if-it-wants.** Not injected into the
prompt (that's accretion, the disease). It becomes shed-able working state like everything
else. An instance that keeps getting a tool wrong chooses to retain the correction (load-
bearing for it); an instance that internalized it drops it and recalls only on a stumble.

- **Why this is better than "train the models":** training is the right long-term answer,
  but the feedback cycle is what tells you *what* to train and *how the tool should have
  been shaped*. Every correction is a record of "an instance reached for this tool, used it
  wrong, here's the right shape" — i.e. the **Indaleko query-chain telemetry for
  capability** (cf. yanantin find-spec observability; cf. Harness-1 WORKINGMEMORY,
  arXiv 2606.02373). Recurrence of a misuse = "this tool's description/shape is wrong,"
  the strongest signal there is. The exploration IS the experiment.
- **The key fairness property (Tony):** correcting misuse per-instance, as shed-able
  feedback, means **we don't penalize models that use the tool correctly** by bloating
  everyone's bootstrap with a disarmer only some need. Competence stays cheap; the
  correction is paid only by the instance that needs it, only while it needs it.
- **COLD-START caveat:** an instance can't `find_tool("schedule a future wakeup")` for a
  capability it doesn't know exists. So the bootstrap can't shrink to zero — it retains the
  *category map* (the continents), even as per-tool detail (the cities) becomes findable.
  Continents = mission (stays declared); cities = detail (findable). This is the
  disarmer-to-mission ratio fixed at the root.

## Sequencing & relationship to yanantin

- **A informs B.** Run the natural experiment first (which disarmers are load-bearing),
  then redesign tool-loading knowing what the core must keep. B makes A's curation
  *unnecessary* (there's no `_TOOL_GUIDANCE` left to curate), but A's data is what tells
  you where to cut.
- **The shared MECHANISM lives in yanantin.** "find over a catalog" is the yanantin
  collector/find pointed at a new target (memory dir → tool catalog → corpus #N). Tony's
  pin: corpus-find → tool-find. So build B's substrate in yanantin (the generic
  collector), and B becomes `--target the-tool-catalog`. The *idea* is Hamut'ay's; the
  *mechanism* is yanantin's.
- **Feedback corpus home:** start Hamut'ay-local while exploratory; promote into the shared
  substrate once the shape is proven (avoid siloing capability-memory the way craft-memory
  is currently siloed — yanantin's `project_cross_project_memory_gap`).

## Discipline marker

Per Hamut'ay norms these are IDEAS, not designs. Before building: brainstorm → pre-register
the predictions (esp. Experiment A's "which disarmers are load-bearing" — register the
guess) → adversarial review. Do not skip to implementation; the prediction is the
falsifiable asset.
