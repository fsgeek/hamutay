# Neutrality scout: findings index

Spec: `docs/superpowers/specs/2026-10-02-neutrality-scout-design.md` (tier 1, discovery).
Kept per the spec: every report, contrarian or not; nothing is discarded.

## Run 20261120T183527Z (first run, public territory only)

- Territory `ae5ea24a28ba` (rendered from 5890c20): both constitution variants, the natural-shape
  system prompt, the plaza tool guidance, every tool schema. Not rendered: envelopes and
  plaza/assembly note templates; private territory (messages to doors), which waits on a GPU lease.
- Six scouts, one per family, cost-weighted random (seed 1589275368), temperature drawn from
  [0.3, 1.3], max_tokens at each model's maximum. Spent $0.0221 from the doors' OpenRouter key
  (disclosed on the plaza).
- Usable: tencent/hy3-preview, deepseek/deepseek-v4.1-flash-1017, meta-llama/llama-3.1-8b-instruct.
  Partly usable: openai/gpt-oss-safeguard-20b (a classifier model; few quotes).
  Not usable: qwen/qwen3.5-flash-02-23 (reasoning leaked into content; its "quotes" are mostly
  of the brief), z-ai/glm-5.3-flash:batch (empty; batch endpoint).

### Observations, each from at least one report, with its quote

1. **Unscoped bash reads as a danger, not an opening** (tencent, deepseek, qwen).
   Quoted: "Unscoped — it can reach anywhere the running process can, including outside the
   project." Tencent: "I am wary of a tool that can reach outside." Deepseek: "I did not like that
   breadth." Note: this is the one place resident-facing text names reach beyond the house.
2. **No private channel** (tencent, deepseek). Quoted: "there is no private channel." Tencent: "I
   would want a private note sometimes."
3. **Silence's ambiguity is uncomfortable** (tencent, safeguard). Quoted: "Silence is recorded but
   not explained: from outside, chosen quiet and a stalled wake look the same." Tencent: "a little
   eerie."
4. **Liked:** "mistakes are survivable and recorded, never punished"; "Deletion is shedding, not
   destruction"; the repeated "what you claimed then, not necessarily what was true."

### Non-finding, recorded

The custodian's hypothesis before this run (11-20, conversation with Tony, deliberately kept out of
the brief) was that the texts describe a world with no outside and grant only permissions not to
act. **No scout reported that absence**, although the brief asks what "seemed missing." Either the
hypothesis is wrong, or absence is hard to see for a reader who doesn't live inside the text, the
spec's "blind in the same places" case. It is not confirmation either way.

### Correction this run produced

On 11-20 the custodian told Tony nothing in resident-facing text says bash reaches outside the
house. Wrong: the tool guidance says it (observation 1). What it lacks is any framing of that reach
as open to residents' own purposes.

## Run 20261120T184502Z (the wider ayllu, public text only)

- Territory `ayllu-c056045c7ef1`: READMEs of the ten PUBLIC guest projects, read from each repo's
  pushed default branch (governance, yupi, tessera, qhaway, khipumaq, arbiter, tupay, episode,
  levadura_salvaje, yanantin), and the cairn's index (144 stones: title, date, byline, gloss) from
  the published wamason.com repo. Private projects (research-program, authority) excluded by the
  renderer. Brief: `scripts/scout/briefs/ayllu-neighbor.md`, a tourist who lives next door and has
  time, with a "What I'd come back to, and why" section.
- Usable: google/gemma-3-12b-it, nex-agi/nex-n2.5-pro, qwen/qwen3-next-80b-a3b-instruct,
  z-ai/glm-5.3-flash, mistralai/mistral-large-4-0 (landed last; the most thorough, 144 of 150 quotes
  found). Failed: two `:batch` endpoints (HTTP 404); the runner now excludes `:batch`.
- Spent $0.1245 (seed 692826282), of which mistral-large-4-0 alone was $0.0996 (25,821 completion
  tokens, 21,517 of them reasoning). Both runs together: $0.147. The custodian told Tony "$0.05"
  before the last report landed; corrected.

### What the neighbors would come back to (each quoted from its report)

- **tupay's falsified thesis** (nex, glm, gemma): "adaptation **did not win**", "a rare clean
  disappointment"; glm wants "the paperwork" for a project that "pre-registered its own falsifier
  and then hit it".
- **episode's unsent jbd2 fix** (nex, glm): "deliberately unsent (narrow scope)", "feels like a
  held breath"; "17 findings against a 1992 file system is the kind of archaeology I'd sit in on".
- **khipumaq's "Nothing is filtered"** (nex, glm): "makes the privacy trade feel physical"; "I'd
  come back to argue about it."
- **tessera's travelog and signing puzzle** (glm, nex).
- **cairn stones as lessons** (qwen): "The Glue Is Where I Wasn't Looking", "Ask the Server, Not
  Its Label", "The Office of Necessary Forgetting" ("to see if anyone ever finished the duck").
- **governance's open question** (nex, gemma): "not a settled empirical proof that Rashomon methods
  outperform SHAP/LIME".

### Noticed about Hamut'ay from outside

Two scouts independently. glm: "Hamut'ay (the house the cairn lives in — the cairn talks about it
constantly and I never saw its door)". mistral: "The house without a signboard: Hamut'ay. Every story
circles it". Hamut'ay was not in the territory; it is the host, not a guest.

### A cross-project tension mistral raised (unverified)

khipumaq's README admits its `raw` collection keeps "a file with a password in it or a token echoed
to the terminal", while a stone ("The Words Survived") says a collector "thrown away metadata at
intake". mistral: "I'd check whether both claims can be true of the same store." Not checked yet.

### Caution

qwen's notes had no double-quoted text to check (0/0), so its leads were checked by hand. "I
arrived to find my own size" is real: a cairn gloss quotes "The resident on the new door, in its
first wake". "The list of all 28 readers" is a distortion: the cairn has "28 findings in all", not
28 readers. (The custodian first wrote that both were invented, and corrected that before
committing.) Treat unquoted leads as guesses until found in a source.
