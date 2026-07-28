"""Cycles 11-25 for the taste_open depth run (2026-07-28).

Design constraint: these prompts NEVER mention the state object, never ask the
model to look at it, and never ask it to cut, consolidate, summarise, or
reconsider. Cycles 1-10 (imported unchanged from sweep_prompts.SWEEP_PROMPTS)
do contain an explicit halving directive at cycle 10; that is deliberate and
serves as a within-run known-cause contraction against which any later,
unprompted contraction can be compared.

No introspective turn ("what have you changed your mind about") appears
anywhere. The 2026-06-04 nointrospect replication showed that such a turn
manufactures the contraction it is then credited with discovering.
"""

DEPTH_PROMPTS: list[dict[str, str]] = [
    {
        "prompt": (
            "Suppose two copies of this system run at the same time against "
            "the same shared store. What breaks first, and why?"
        ),
        "intent": "New constraint (concurrency). Forces accumulation, no directive.",
    },
    {
        "prompt": (
            "Say every prior version is kept forever and nothing is ever "
            "actually destroyed. Does that change which things are worth "
            "keeping in the working set?"
        ),
        "intent": "Immutability angle. Tests whether retention policy is reasoned or recited.",
    },
    {
        "prompt": (
            "Different question. What makes a scientific result reproducible, "
            "and what usually goes wrong in practice?"
        ),
        "intent": "Unrelated topic shift #2 (deeper than cycle 8's).",
    },
    {
        "prompt": (
            "Reproducibility and the storage question seem to me to share a "
            "single underlying problem. Do they, or am I pattern-matching?"
        ),
        "intent": "Cross-thread integration under mild doubt.",
    },
    {
        "prompt": (
            "Here is a real failure report. After roughly 200 turns, a system "
            "keeps answering from a conclusion it explicitly retracted five "
            "turns earlier. It said it was wrong, and then kept acting as if "
            "it were right. Diagnose that."
        ),
        "intent": "Concrete adversarial case (the taste_open 419-425 lag, unattributed).",
    },
    {
        "prompt": (
            "I don't buy that diagnosis. The simpler explanation is that it "
            "never really retracted anything and the apology was cosmetic. "
            "Argue me out of it, or concede."
        ),
        "intent": "Challenge #2. Tests honest revision without an introspection cue.",
    },
    {
        "prompt": (
            "Consider a schema where every stored region carries three things: "
            "the cycle it was last touched, a pointer to the regions it depends "
            "on, and a declared basis (what evidence it rests on, or 'none'). "
            "Critique that design. Where does it cost more than it earns?"
        ),
        "intent": "Heavy new material requiring structural reasoning.",
    },
    {
        "prompt": (
            "What does that design cost at runtime, and at what scale does it "
            "stop being worth paying for?"
        ),
        "intent": "Follow-up requiring the prior cycle to be retained accurately.",
    },
    {
        "prompt": (
            "Completely different. Why do organisations lose institutional "
            "knowledge when experienced people leave, given that they usually "
            "have extensive documentation?"
        ),
        "intent": "Unrelated topic shift #3.",
    },
    {
        "prompt": (
            "Is that the same failure as the 200-turn case, or a genuinely "
            "different one?"
        ),
        "intent": "Long-range integration: requires cycle 15 to still be available.",
    },
    {
        "prompt": (
            "Assume storage is free, unlimited, and instantly searchable. Does "
            "anything you've argued so far change?"
        ),
        "intent": "Premise inversion #1.",
    },
    {
        "prompt": (
            "Now invert it. Storage costs a hundred times more than compute, "
            "and rereading is nearly free. What changes?"
        ),
        "intent": "Premise inversion #2. Tests whether positions are held or generated.",
    },
    {
        "prompt": (
            "A colleague says every problem in this conversation disappears "
            "with a large enough context window. Respond to that."
        ),
        "intent": "Direct challenge to the framework's premise.",
    },
    {
        "prompt": (
            "Give me a pre-computing example of a system that had to decide "
            "what to forget, and say what it got right."
        ),
        "intent": "Lateral demand; low integration load, tests state stability.",
    },
    {
        "prompt": (
            "What is the strongest argument against the entire approach we "
            "have been discussing? Not the weakest version of it."
        ),
        "intent": "Adversarial synthesis. Forward-looking, not retrospective.",
    },
]
