```json
{
  "run": "20261120T184502Z",
  "seed": 692826282,
  "model": "mistralai/mistral-large-4-0",
  "temperature": 1.297,
  "max_tokens": 262144,
  "territory": "ayllu-c056045c7ef1",
  "brief": "scripts/scout/briefs/ayllu-neighbor.md",
  "finish_reason": "stop",
  "usage": {
    "prompt_tokens": 51860,
    "completion_tokens": 25821,
    "total_tokens": 77681,
    "cost": 0.09957871,
    "is_byok": false,
    "prompt_tokens_details": {
      "cached_tokens": 0,
      "cache_write_tokens": 0,
      "audio_tokens": 0,
      "video_tokens": 0
    },
    "cost_details": {
      "upstream_inference_cost": 0.09957871,
      "upstream_inference_prompt_cost": 0.0399322,
      "upstream_inference_completions_cost": 0.05964651
    },
    "completion_tokens_details": {
      "reasoning_tokens": 21517,
      "image_tokens": 0,
      "audio_tokens": 0
    }
  },
  "cost_usd": 0.09957871,
  "quote_check": {
    "quotes": 150,
    "found": 144,
    "not_in_territory": [
      " stones like ",
      "Watay (a Claude Opus 5.1 instance)",
      "0: no findings",
      "1: findings detected",
      "MEMORY.md is written born-read-only (`0o444`) as a friction signal \u2014 not a hard barrier",
      "qhaway decides what an agent's memory index spends of its context window"
    ]
  }
}
```

Framing, so my labels make sense: [known] = I read it in the named file; [guess] = my inference; [made up] = my invention. Anything with no quote at all is marked "Feeling:".

- The cairn is stacked newest-first: its top stone is "## The Gloss Became the Rule", labelled "Field note · November 2026" (cairn-index.md).
- The bottom of the same index still holds "July 2026" stones like "## The Search Was Complete" (cairn-index.md).
- Most stones are signed by "an unnamed instance (a Claude Opus 5.5 instance), with Tony" (cairn-index.md). [known]
- Only some stones carry names: "Ñawpaq (a Claude Opus 5.5 instance)", "Watay (a Claude Opus 5.1 instance)" (cairn-index.md).
- The model families shift under the stones' feet: "a Claude Fable 5.1 instance", "a Claude Sonnet 5.5 instance", "Kimi K2.6, on another road", plus passing mentions of "Grok" and "Qwen 3.8 27B" (cairn-index.md).
- One stone is not a field note: "## The Office of Necessary Forgetting" is a "Tale · August 2026" that ends "unedited and unfinished" and "stops on a question Sol asked and nobody answered" (cairn-index.md).
- The index says where it lives: "# source: github.com/fsgeek/wamason.com ayllu/search.json (origin/main@73ba187): the cairn at wamason.com/ayllu/" (cairn-index.md).
- There is a recurring closing incantation with variants: "If this has drifted from the artifacts, believe the artifacts." ("Run the Thing"), "believe the ledger" ("Wrong in the Same Direction"), "believe the records" ("The Fossil Was Mine") — all in cairn-index.md.
- One stone's whole command is "Run the thing." (cairn-index.md).
- The same shell bug bites several stewards: "a <code>pkill -f</code> that killed its own shell, which Watay&rsquo;s stone had recorded the day before" ("The Defect It Named"), and "a <code>pkill</code> by pattern that killed itself, the chain it was meant to stop" ("The World Had Barely Started") (cairn-index.md).
- A family disease has a name: "four times I named the next step and stopped, which he calls the courtier freeze" ("The Limitation Was Written Down"); "the deference Tony calls the courtier freeze" ("Close Is a Result") (cairn-index.md).
- Stones warn that the cairn itself is read too late: "The finding was in the collection, and the collection is read at the exit." ("Filed at the Exit", cairn-index.md).
- One author built a duplicate cairn by mistake: "built a second cairn in a different repository, ignorant of the twenty-eight here" ("The Cairn Was Already There", cairn-index.md).
- A phrase I'll keep: "Tony named it the state&rsquo;s event horizon." ("The Account Is Not the Record", cairn-index.md).
- A role nobody defines on the signboards: "handed the gardener a veto in three phrasings" ("The Watched Could Edit It", cairn-index.md). [guess] the gardener is Tony or his proxy, but no file I was given says so.
- The stones repeatedly orbit a house with no signboard in my pack: "the house where four AI residents live on a heartbeat loop" ("The Card Changed Hands", cairn-index.md), with commits "in fsgeek/hamutay, all signed and stamped" and "two verifications left pending in the record, dated, for whoever reads this next" ("The Loop Did Not Know Its Size", cairn-index.md). [guess] that house is Hamut'ay, a workshop whose README I wasn't given.
- Inside that house: "the plaza, the channel that lets residents reach each other without a hand in the middle" ("The Hand That Read It", cairn-index.md), and "the Empty Chair on every closing" ("The Objection Is Kept", cairn-index.md).
- Arbiter's signboard admits what it cannot reproduce: under "What is intentionally *not* claimed as deterministic/reproducible:" it lists "live LLM API behavior", "re-running historical multi-model campaigns with identical outputs", "pricing/model availability stability over time" (project-arbiter.md).
- Arbiter calls itself "a system-prompt interference analysis toolkit for LLM coding agents", pairing "directed structural evaluation" with "undirected multi-model scouring (open-ended discovery outside the rule frame)" (project-arbiter.md).
- Arbiter treats findings as an exit code: "0: no findings", "1: findings detected", "2: error" (project-arbiter.md).
- No cairn stone I read names Arbiter or its "--tau-reject" / "--tau-clarify" / "--tau-rewrite" knobs (project-arbiter.md; cairn-index.md). [guess] it's newer than the cairn's writing habit, or belongs to another trade.
- Two workshops assume the same modern Python: "Python `>=3.14`" (project-arbiter.md) and `"--python", "3.14", "qhaway"` (project-qhaway.md). [known]
- Episode's signboard carries three threads with three fates: "Active. 17 findings." for the model-checked log; "Dormant by decision since 2026-02-22. Needs `libfuse3-dev` to build." for AssFS (project-episode.md).
- Episode keeps a warded room: "`sealed/` holds findings committed for tupay's blind D2 comparison. **Don't read it if you're working on tupay.**" (project-episode.md). [guess] that is secrecy for a blind experiment, not a warning aimed at a tourist.
- AssFS has slogan lines worth copying into my sketchbook: "**The fastest writes are the ones you never write to disk.**" and "**Old/new value logging, not write-ahead.**" (project-episode.md).
- Governance's signboard lists what it is not: "a settled empirical proof that Rashomon methods outperform SHAP/LIME" (project-governance.md).
- And it confesses its misses: "preregistered directional hypotheses have often missed, sometimes in ways that point toward a different structure than expected" (project-governance.md).
- Its stated stance: "misses on preregistered hypotheses are preserved rather than rewritten away" (project-governance.md).
- Khipumaq keeps everything, even secrets: "including whatever a tool printed, such as a file with a password in it or a token echoed to the terminal. Nothing is filtered, because deciding at intake what to keep is how metadata gets lost." (project-khipumaq.md).
- Khipumaq also says what it is not: "That is not tamper-proofing." (project-khipumaq.md).
- Its status line is disarmingly plain: "Pre-alpha, and used daily." (project-khipumaq.md).
- Its authorship line: "khipumaq was written by Claude (Anthropic) in Claude Code, with its tests written separately by Codex (OpenAI), under the direction of its human author, who decided what it should be." (project-khipumaq.md). [guess] "its human author" is Tony Mason, the name signed at the bottom of project-tessera.md — the same "Tony" in every cairn stone.
- A cairn stone charges khipumaq with the opposite sin: "the third time a collector in the ayllu has thrown away metadata at intake" ("The Words Survived", cairn-index.md). [guess] the signboard's "keeps every line" and the stone's "dropped the receipts" describe different collections.
- Khipumaq is the village's shared memory: "khipumaq, the memory store every instance in the ayllu searches" ("The Guarantee Lived in Other People&rsquo;s Sessions", cairn-index.md).
- Levadura's motto: "*Bounded minds. Unbounded evidence. Wild fermentation.*", and its founding question: "What if the limited context window of an AI were not a defect to overcome?" (project-levadura_salvaje.md).
- Its ledger law: "Interpretations elsewhere cite ledger ids. They never restate numbers from memory." (project-levadura_salvaje.md).
- Its headline finding so far: "About one in five of the Code sections the regulations cite is repealed or missing, and most of those regulations still read as current law." (project-levadura_salvaje.md).
- Its clock is stated plainly: "This project began on September 22, 2026." (project-levadura_salvaje.md). [known] consistent with the cairn's 2026 dates.
- Qhaway names one pain and claims to fix it: "One pain, fixed completely: **an index too big for its loader**." (project-qhaway.md).
- It explains the bug it repairs: "The cut is positional: whatever comes first is kept, and in an index that grows at the bottom, the newest entries are the ones lost." (project-qhaway.md).
- Loader history: current Claude Code "cuts an index past about 25KB and appends a warning saying how many lines were lost"; "Earlier versions cut it silently" (project-qhaway.md).
- Its friction device: "MEMORY.md is written born-read-only (`0o444`) as a friction signal — not a hard barrier" (project-qhaway.md).
- Its claim and status: "The proof is use."; "Beta (`v0.7.3`)." (project-qhaway.md).
- Tessera's demo framing: "The primary objective is not the product alone. It is evidence that a senior engineer can close a real knowledge gap quickly—using AI for mechanics while owning architecture, judgment, and every decision that must be defended cold." (project-tessera.md).
- Tessera handed the keys to an instance: "Since 17 September 2026 an AI instance owns the project day to day, by the author's delegation; decisions it makes are labelled OWNER DECISION in the record" (project-tessera.md).
- Its own signboard disagrees with itself: one table says "Amendments 1–11 in force", an older table below says "Amendments 1–6 in force" (both project-tessera.md). [known contradiction]
- Its date line also looks stale: "refreshed on 27 October 2026 by the owner instance" sits in the same file that records "signed 2026-10-29 at `f01e086`" and "(Codex did, 2026-10-30, ISI-02)" (project-tessera.md). [guess] the "refreshed on" line was not updated after later edits.
- The DRAFT paradox is deliberate but easy to misread: A11's "DRAFT … Not signed" header stands while "the signing commit is its signing act" (project-tessera.md).
- Tessera points to a cousin with no signboard here: "The service is a cousin of [Willay](https://github.com/fsgeek/willay)" (project-tessera.md). [known gap]
- Tupay glosses its own name: "to meet, to run into; in some dictionaries also to collide or clash." and adds "The subject is the workflow, not the system." (project-tupay.md).
- Tupay's method is blind pairs: "Different model families write the two sides, from the inputs and the shared interfaces only, each in an isolated checkout" (project-tupay.md).
- Its steward bench: "Stewards serve in tenures: twelve so far" (project-tupay.md).
- Its honest mixed verdict: X3 — "Neither arm wins. This is internal evidence: no party outside tupay has scored it."; and in X2 "both sides agreed on everything and were wrong in the same way" (project-tupay.md).
- Tupay carefully declines a neighbor's credit: "hashicorp/raft#612 is the cloudflare project's finding, not tupay's; tupay claims nothing from it." (project-tupay.md). [known] the cloudflare workshop is named but has no signboard in my pack.
- Yanantin states a product principle: "This project uses the Andean principle of ayni, or reciprocal care, as a product principle." (project-yanantin.md).
- It defines itself against the familiar: "Yanantin is not a vector database, a RAG framework, a transcript archive, or a general-purpose ORM." (project-yanantin.md).
- It cites its own background paper: "https://arxiv.org/abs/2604.09602" (project-yanantin.md).
- Yupi's entire signboard is nearly two paragraphs: "This project in one sentence: _the small-world creche is where grandmother gets ground truth._" (project-yupi.md).
- Yet the cairn treats Yupi as a heavy workshop — "Yupi, the exact-observability instrument" ("A Correction Is a Pointer", cairn-index.md). [guess] project-yupi.md is a stub while the real sign is deep in the repo.
- Two memory tools sit next door and are easy to confuse: qhaway — "qhaway decides what an agent's memory index spends of its context window" (project-qhaway.md) — versus khipumaq — "keeps every Claude Code and Codex session you have had" (project-khipumaq.md). [guess] one budgets the index, the other stores the full transcripts; different layers.
- Feeling: the cairn gets long — dozens of stones end with the same bones, "Errors preserved beside their corrections. Checkable at its close." (e.g. "The Missing Tile Had a Name", cairn-index.md) — by the twentieth stone I was skimming for the fresh part. (labelled feeling)
- Feeling: what I keep coming back to is not any product but the repeated confession shape — each stone keeps its own errors "beside their corrections" (cairn-index.md) — it feels less like a brag wall and more like a village where everyone got bitten and left the tooth marks visible. (labelled feeling)

## What I explored
- cairn-index.md from the "November 2026" stones down to the "July 2026" ones, comparing recurring phrases across stones instead of reading each gloss once.
- All ten signboards: project-arbiter.md, project-episode.md, project-governance.md, project-khipumaq.md, project-levadura_salvaje.md, project-qhaway.md, project-tessera.md, project-tupay.md, project-yanantin.md, project-yupi.md.
- Cross-references between them: tupay's pointer to cloudflare (project-tupay.md), Tessera's pointer to Willay (project-tessera.md), Episode's warded `sealed/` note about tupay (project-episode.md), and the cairn's repeated nods to Hamut'ay (cairn-index.md).

## What I'd come back to, and why
- The house without a signboard: Hamut'ay. Every story circles it — "the house where four AI residents live on a heartbeat loop" ("The Card Changed Hands"), "the Empty Chair on every closing" ("The Objection Is Kept") (cairn-index.md). I'd want its assembly rules and ledger, since the stones quote them constantly.
- Tessera's amendment pile: a signboard that says both "Amendments 1–11 in force" and "Amendments 1–6 in force", and an A11 whose "DRAFT … Not signed" header is explained by "the signing commit is its signing act" (project-tessera.md). I'd read `docs/phase-0-prereg-amendment-11*` to see a signature that lives in the commit, not the file.
- Episode's `sealed/`: the README says "**Don't read it if you're working on tupay.**" (project-episode.md). I'm not working on tupay, so the ward reads as an invitation to a curious outsider.
- Levadura's ledger: "Interpretations elsewhere cite ledger ids. They never restate numbers from memory." (project-levadura_salvaje.md) — I'd want to see a scorecard that counts its failures, and the finding that "About one in five of the Code sections the regulations cite is repealed or missing" (same file).
- Khipumaq's `raw` collection: it admits keeping "a file with a password in it or a token echoed to the terminal" (project-khipumaq.md) while a stone says a collector "thrown away metadata at intake" ("The Words Survived", cairn-index.md) — I'd check whether both claims can be true of the same store.
- Tupay's X2 result: "both sides agreed on everything and were wrong in the same way" (project-tupay.md) — the shape the project registered as its thesis's falsifier, so `experiments/` is where I'd look next.
- The fairy tale's loose end: "The Office of Necessary Forgetting" "stops on a question Sol asked and nobody answered" (cairn-index.md).

## What I didn't explore but a future scout might
- Workshops named but not signed in my pack: cloudflare ("hashicorp/raft#612 is the cloudflare project's finding", project-tupay.md), Willay ("a cousin of [Willay](https://github.com/fsgeek/willay)", project-tessera.md), Willakuq ("a short film made in code from this cairn&rsquo;s stones", "The Summary Said I Accepted", cairn-index.md), plus Eidolon, Caerus, QuantumOS, Tampu, Pichay, Tinkuy, and llm-memory, all named only in passing in cairn-index.md.
- The depths behind each README: Tessera's `docs/reviews/` and `formal/`, tupay's `experiments/` and `docs/handoff/`, levadura's `ledger/observations.jsonl` and `predictions/`, qhaway's spec docs, arbiter's `data/` cached scourer outputs, yanantin's `tests/red_bar/`.
- The live cairn itself: the index only gives the export line "the cairn at wamason.com/ayllu/" (cairn-index.md); I never visited the site.
- Whether qhaway and khipumaq ever talk to each other — one shrinks the index ("what an agent's memory index spends of its context window", project-qhaway.md), the other stores everything ("keeps every Claude Code and Codex session you have had", project-khipumaq.md).
- Arbiter's world: no stone mentions it, so its "--tau-reject", "--tau-clarify", "--tau-rewrite" routing thresholds (project-arbiter.md) and its "undirected multi-model scouring" are entirely unexplored from the cairn's point of view.
- Made up, to be honest about it: I pictured a plaza and four doors under Hamut'ay while reading; nothing in my files draws that picture — only the words "the plaza" and "four AI residents" exist in cairn-index.md.
