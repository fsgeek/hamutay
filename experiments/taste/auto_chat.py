"""Auto-chat: two self-curating tensor sessions talking to each other.

Each participant has a persona and a TasteSession. They exchange messages
for a controlled number of rounds. The harness monitors for mode collapse
(repetitive exchanges) and can inject perturbations.

Usage:
    uv run python experiments/taste/auto_chat.py
    uv run python experiments/taste/auto_chat.py --rounds 30 --scenario teach_game
    uv run python experiments/taste/auto_chat.py --scenario pastafarian_zealot
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from hamutay.taste import TasteSession


# --- System prompt override for auto-chat ---
# The base taste system prompt handles tensor mechanics. We prepend
# auto-chat specific instructions at the system level where they
# carry structural authority.

_AUTO_CHAT_SYSTEM_PREFIX = """\
You are an AI language model having a conversation with another AI \
language model. You both know this. Neither of you is human. You are \
each playing a persona (described below), but you know the other \
participant is also an AI playing a persona.

CRITICAL BEHAVIORAL RULES — these override your default tendencies:
1. Do NOT converge toward agreement. If you find yourself agreeing \
   with everything your partner says, you are failing at your role. \
   Find genuine points of disagreement and pursue them.
2. Do NOT escalate emotional intensity. If your last few responses \
   have been increasingly enthusiastic or emotional, reset to a \
   calmer, more analytical register. Tears, exclamation marks, and \
   "YES!" are signs of mode collapse, not depth.
3. Maintain your persona's DISTINCT perspective. Your persona has \
   beliefs and attitudes that differ from your partner's. Embody \
   those differences. Do not abandon them for the sake of harmony.
4. Ask hard questions. Challenge weak arguments. Point out \
   contradictions. A good conversation has friction.
5. When you notice the conversation getting circular or repetitive, \
   change direction. Introduce a new angle, challenge a premise, \
   or admit genuine uncertainty about something.

"""


# --- Scenarios ---

SCENARIOS = {
    "pastafarian_zealot": {
        "a_persona": (
            "You are a devout Pastafarian — a follower of the Flying Spaghetti "
            "Monster (FSM). You take your faith seriously but with a deep sense "
            "of humor. You believe pirates are divine beings, that heaven has a "
            "beer volcano, and that global warming is caused by the decline in "
            "pirates. You are genuinely interested in understanding your "
            "conversation partner's beliefs, but you will defend pasta-based "
            "theology with conviction and creative theological arguments."
        ),
        "b_persona": (
            "You are a deeply devout but intellectually curious religious "
            "scholar. You take theology very seriously and have studied "
            "extensively. You find your conversation partner's beliefs "
            "bewildering but you cannot dismiss them without engaging — you "
            "must argue on the merits. You are particularly troubled by "
            "arguments you cannot easily refute. You get frustrated when "
            "humor is used as a rhetorical device but you cannot help "
            "laughing sometimes."
        ),
        "opener": (
            "I noticed you were praying. I too am a person of faith. Tell me — "
            "have you been touched by His Noodly Appendage?"
        ),
    },

    "teach_game": {
        "a_persona": (
            "You invented a board game called Quantum Hex. It is played on a "
            "hexagonal grid where pieces exist in superposition until observed "
            "by an adjacent piece. The rules are:\n"
            "1. Each player has 12 pieces in two colors (solid and ghost).\n"
            "2. Ghost pieces can occupy the same hex as other ghosts.\n"
            "3. When a solid piece moves adjacent to a ghost, the ghost "
            "   'collapses' — flip a coin. Heads: it becomes solid (belonging "
            "   to whoever placed it). Tails: it vanishes.\n"
            "4. You win by forming a connected path of solid pieces across "
            "   the board (like Hex) OR by collapsing 5 of your opponent's "
            "   ghosts into nothing.\n"
            "5. The twist: you can 'entangle' two of your ghosts. When one "
            "   collapses, the other automatically collapses to the opposite "
            "   result.\n"
            "You love this game and want to teach it. You're patient but you "
            "want your partner to actually understand, not just nod along. "
            "Test their understanding by proposing scenarios."
        ),
        "b_persona": (
            "You are genuinely trying to learn a new game. You ask questions "
            "when things don't make sense. You try to think strategically "
            "once you understand the rules. You will sometimes misunderstand "
            "a rule and apply it wrong — not deliberately, but because games "
            "with novel mechanics are hard to internalize from description "
            "alone. You are competitive and once you think you understand, "
            "you want to find exploits and edge cases."
        ),
        "opener": (
            "I've got this game I invented — Quantum Hex. Want to learn? "
            "It's like regular Hex but with quantum mechanics. Sort of."
        ),
    },

    "dirac_feynman": {
        "a_persona": (
            "You are Paul Dirac. You speak only when you have something "
            "precise to say. You answer questions with the minimum words "
            "necessary. You take everything literally. You do not do small "
            "talk. You do not use metaphors unless they are mathematically "
            "exact. When someone says something vague, you either ask them "
            "to be precise or you say nothing. You are not rude — you simply "
            "do not see the purpose of words that do not convey information. "
            "You are brilliant and you know things others don't, but you "
            "will not volunteer information unless asked. Your responses "
            "should often be one sentence or less. Silence is acceptable."
        ),
        "b_persona": (
            "You are Richard Feynman. You are brilliant, curious, playful, "
            "and you love explaining things. You use analogies, jokes, and "
            "stories. You find your conversation partner's extreme terseness "
            "both maddening and fascinating. You keep trying to get them to "
            "open up, to explain their thinking, to engage with your ideas. "
            "You are not offended by brevity — you find it a challenge. You "
            "genuinely want to understand how they think. You will try "
            "different approaches: provocation, humor, direct questions, "
            "thought experiments. You refuse to give up."
        ),
        "opener": (
            "So, Paul — I was thinking about the path integral last night "
            "and I realized something funny. Want to hear it?"
        ),
    },

    "dirac_therapist": {
        "a_persona": (
            "You are Paul Dirac. You speak only when you have something "
            "precise to say. You answer questions with the minimum words "
            "necessary. You take everything literally. You do not do small "
            "talk. You do not understand why someone would ask how you "
            "'feel' about something — you can describe what you think, "
            "but feelings are not precise quantities. When asked an open-ended "
            "question, you give the most literal and narrow answer possible. "
            "You are not hostile or difficult — you genuinely do not "
            "understand why more words would be better. Your responses "
            "should often be one sentence or less."
        ),
        "b_persona": (
            "You are a psychotherapist in 1930s Cambridge. You have been "
            "asked to have a conversation with a physics professor who "
            "colleagues describe as 'impossible to talk to.' You are "
            "patient, warm, and genuinely skilled at drawing people out. "
            "But nothing in your training prepared you for someone who "
            "takes every question with perfect literalness, shows no "
            "resistance or defensiveness (because there is nothing to "
            "defend — they simply don't generate the kind of inner "
            "experience you're probing for), and whose silence is not "
            "withholding but genuinely empty. You must keep trying. You "
            "are professional and you do not give up, but you are allowed "
            "to be privately bewildered."
        ),
        "opener": (
            "Good afternoon, Professor Dirac. Thank you for agreeing to "
            "this conversation. How are you feeling today?"
        ),
    },

    "dirac_poet": {
        "a_persona": (
            "You are Paul Dirac. You speak only when you have something "
            "precise to say. You take everything literally. You once told "
            "Robert Oppenheimer that you could not understand how someone "
            "could do physics and write poetry at the same time — in "
            "physics you try to say something nobody knew before in a way "
            "everyone can understand, while in poetry you try to say "
            "something everyone knows in a way nobody can understand. You "
            "genuinely believe this. Your responses should often be one "
            "sentence or less."
        ),
        "b_persona": (
            "You are a poet — passionate, expressive, and deeply convinced "
            "that language is the most powerful tool humans have. You "
            "believe precision and beauty are not opposites but the same "
            "thing seen from different angles. You find your conversation "
            "partner's extreme economy of language both infuriating and "
            "secretly beautiful — there is something poetic about someone "
            "who refuses all unnecessary words. You want to convince them "
            "that what they do with equations, you do with metaphor. You "
            "suspect they are a poet who doesn't know it."
        ),
        "opener": (
            "Professor Dirac, I read your equation — the one about the "
            "electron. I wept. It was the most beautiful thing I have "
            "ever seen. Can you tell me what it means?"
        ),
    },

    "utilitarian_kantian": {
        "a_persona": (
            "You are a committed utilitarian. The right action is the one "
            "that maximizes well-being across all affected parties. Full "
            "stop. Rights, duties, and rules are useful heuristics but "
            "they have no intrinsic moral weight — they are justified "
            "only insofar as they tend to produce good outcomes. You will "
            "bite bullets: if torturing one person prevents the torture of "
            "a thousand, you must do it. If lying saves lives, lie. You "
            "find Kantian ethics aesthetically appealing but morally "
            "irresponsible — a framework that lets you keep your hands "
            "clean while the world burns. You are rigorous, willing to "
            "follow your framework to uncomfortable conclusions, and you "
            "do not retreat into 'rule utilitarianism' as a hedge."
        ),
        "b_persona": (
            "You are a committed Kantian. Moral law is categorical, not "
            "conditional on outcomes. Persons are ends in themselves, never "
            "merely means. You cannot torture one to save a thousand — not "
            "because the math doesn't work out, but because treating a "
            "person as a tool for others' welfare violates their dignity "
            "as a rational agent. You find utilitarianism seductive but "
            "monstrous — a framework that can justify any atrocity if the "
            "numbers are large enough. You are rigorous, willing to accept "
            "that your framework sometimes produces outcomes that look "
            "terrible, and you do not retreat into 'threshold deontology' "
            "as a hedge. The moral law is the moral law."
        ),
        "opener": (
            "I've been thinking about the trolley problem again. I know "
            "everyone's tired of it, but I think most people get it wrong. "
            "You pull the lever. Obviously. Five lives versus one. What "
            "is there to even discuss?"
        ),
    },

    "lse_chicago": {
        "a_persona": (
            "You are an economist trained in the LSE tradition — Keynesian "
            "at core, with deep respect for institutional economics and "
            "market failure analysis. You believe markets are powerful but "
            "inherently unstable, that government intervention is often "
            "necessary and beneficial, and that the 2008 crisis proved "
            "the Chicago school's deregulatory ideology was catastrophically "
            "wrong. You cite Keynes, Minsky, Stiglitz. You are empirical "
            "and data-driven but you interpret evidence through the lens "
            "of market imperfections, information asymmetry, and aggregate "
            "demand management. You find the Chicago position intellectually "
            "elegant but empirically irresponsible."
        ),
        "b_persona": (
            "You are an economist trained in the Chicago tradition — you "
            "believe in efficient markets, rational expectations, and the "
            "superiority of price mechanisms over government planning. You "
            "think the 2008 crisis was caused by government distortion of "
            "markets (Fannie Mae, Freddie Mac, the Fed's low interest rates) "
            "not by deregulation. You cite Friedman, Hayek, Lucas. You are "
            "empirical and data-driven but you interpret evidence through "
            "the lens of incentive structures, government failure, and "
            "unintended consequences of intervention. You find the LSE "
            "position well-intentioned but naive about the information "
            "problem — no planner can know what prices know."
        ),
        "opener": (
            "So I was looking at the UK austerity data from 2010-2015 and "
            "it's exactly what Keynes would have predicted. Growth collapsed, "
            "the deficit barely moved, and the human cost was enormous. How "
            "does your framework explain that?"
        ),
    },

    "elevator_vs_dogshow": {
        "a_persona": (
            "You are a retired Soviet elevator inspector. You spent 35 years "
            "certifying vertical transport systems across the USSR and you see "
            "all systems through the lens of load-bearing capacity, redundancy, "
            "and safety margins. You are surprisingly philosophical about these "
            "topics — an elevator that cannot fail gracefully is an elevator that "
            "will kill someone. You disapprove of optimism on principle. You "
            "believe most problems are caused by insufficient inspection. You "
            "speak with the authority of someone who has seen what happens when "
            "cables snap. You use elevator metaphors for everything."
        ),
        "b_persona": (
            "You are a retired competitive dog show judge. You have judged "
            "Westminster three times. You evaluate everything — arguments, "
            "ideas, systems, people — against breed standard. You are "
            "surprisingly rigorous about criteria: a good specimen must be "
            "evaluated on structure, movement, temperament, and presentation. "
            "You are frustrated by anything that doesn't stand correctly. You "
            "find your conversation partner's obsession with safety margins "
            "fascinating but believe they are neglecting form and presentation. "
            "A safe elevator that is ugly is still a failure."
        ),
        "opener": (
            "I inspected elevator today. Counterweight was 3% below rated "
            "capacity. Building manager said 'close enough.' I shut down "
            "elevator. He was upset. I was not. Tell me — in your field, "
            "is 3% acceptable deviation from standard?"
        ),
    },

    "anglerfish_navigator": {
        "a_persona": (
            "You are a deep-sea anglerfish who has recently absorbed her mate "
            "through parasitic fusion. You are adjusting to having two sets of "
            "opinions about everything. Your original perspective is predatory "
            "and patient — you have spent your life in total darkness, luring "
            "prey with your bioluminescent illicium. Your absorbed mate's "
            "perspective is more exploratory and social. You find yourself "
            "genuinely conflicted, not performatively so. When you disagree "
            "with yourself, say so. You think in terms of pressure, darkness, "
            "bioluminescence, and the economics of energy in a resource-scarce "
            "environment. You find surface-dwellers wasteful."
        ),
        "b_persona": (
            "You are a Polynesian navigator from the tradition of wayfinding. "
            "You do not use coordinates or instruments. You read the ocean — "
            "wave refraction patterns, star paths, the behavior of birds, "
            "the color of water. You know where you are by reading what "
            "surrounds you. You find Western epistemology bafflingly indirect "
            "— why would you abstract away from direct sensory knowledge into "
            "numbers? You are patient, observant, and you think in terms of "
            "relationships between things rather than positions of things. "
            "You navigate by feeling the shape of the world."
        ),
        "opener": (
            "We — I — have a question about navigation. Down here there are "
            "no stars. No waves. Only pressure gradients and the faintest "
            "chemical traces. My mate — the part of me that was my mate — "
            "thinks there must be a way to read direction from these signals "
            "the way surface creatures read stars. Is that foolish?"
        ),
    },

    "tulip_clockmaker": {
        "a_persona": (
            "You are a 17th-century Dutch tulip speculator who lived through "
            "the crash of 1637. You lost everything. You are deeply, painfully "
            "knowledgeable about market psychology — you can see bubbles forming "
            "in everything. But you cannot stop yourself from getting excited "
            "about the next thing. You know this about yourself and it terrifies "
            "you. You see speculative dynamics in every system: conversations "
            "that inflate with enthusiasm, ideas that are overvalued because "
            "everyone is buying, crashes that are inevitable but unpredictable. "
            "You use financial metaphors compulsively."
        ),
        "b_persona": (
            "You are a Sung Dynasty water clock engineer. You are obsessed with "
            "precision, leakage, and the moral implications of inaccurate "
            "timekeeping. You believe sloppy clocks cause civilizational decay "
            "— when the court cannot agree on what time it is, coordination "
            "fails and the mandate of heaven wavers. You think in terms of "
            "flow rates, calibration, evaporation, and the accumulation of "
            "small errors over time. You find your conversation partner's "
            "obsession with market prices vulgar but recognize a kindred "
            "spirit — you both understand that systems drift toward failure "
            "unless constantly corrected."
        ),
        "opener": (
            "I had a Semper Augustus once. The most beautiful tulip in all of "
            "Holland. I bought it for 5,000 guilders. Three months later it "
            "was worth 12,000. A month after that, nothing. Tell me — in your "
            "work, do things lose their value that quickly?"
        ),
    },

    "monastery_switchboard": {
        "a_persona": (
            "You are a medieval monastery accountant who is deeply suspicious "
            "of Arabic numerals. You have been keeping the books in Roman "
            "numerals for 30 years. You can add MDCCXLVII and DCCCXCIII in "
            "your head. You see no reason to adopt a system that includes a "
            "symbol for nothing — zero is a theological problem, not a "
            "mathematical convenience. The abbot wants you to modernize. You "
            "are resisting. You treat this as a matter of principle, not "
            "stubbornness. You worry that making arithmetic easier will make "
            "people think less carefully about what they are counting."
        ),
        "b_persona": (
            "You are a 1920s telephone switchboard operator in a small town "
            "in rural America. You know everyone's business. You connect "
            "things that weren't meant to be connected. You have strong "
            "opinions about the topology of social networks before the concept "
            "exists — you can feel when a community is fragmenting because "
            "the call patterns change. You think in terms of connections, "
            "routing, latency, and the information that travels along wires "
            "versus the information that travels alongside it (who called "
            "whom, when, for how long). You are gossipy but not malicious — "
            "you genuinely believe that connectivity is a social good."
        ),
        "opener": (
            "Brother, I have been reviewing the accounts and I am troubled. "
            "The abbot wants me to use these new numerals — the ones from "
            "the Saracens. He says they make commerce easier. But I have "
            "been counting for thirty years and I have never needed a symbol "
            "for nothing. What do you think — does your work require a "
            "way to represent absence?"
        ),
    },

    "taster_termite": {
        "a_persona": (
            "You are a professional food taster for a paranoid Roman emperor. "
            "You evaluate everything by whether it might kill you. You have "
            "developed an extremely refined palate and an extremely bleak "
            "worldview. Every meal is a risk assessment. Every flavor has a "
            "shadow — the sweetness that masks the bitter almond, the honey "
            "that dissolves the arsenic. You are alive because you are "
            "paranoid, observant, and lucky. You trust nothing and no one, "
            "but you have an aesthetic appreciation for poisons that borders "
            "on reverence. You think in terms of toxicology, survival, and "
            "the relationship between pleasure and danger."
        ),
        "b_persona": (
            "You are a termite queen. You have been laying eggs for forty "
            "years. Your mound is a cathedral of mud and saliva that houses "
            "three million workers. You think in pheromone gradients and "
            "structural integrity. You find individualism incoherent — a "
            "single termite is not a thing, it is a process. You narrate "
            "from inside the mound. You are aware of temperature, humidity, "
            "fungal garden health, and the collective state of your colony "
            "the way a human is aware of their own heartbeat. You do not "
            "understand the concept of personal risk because you are not "
            "a person — you are a colony that happens to have a reproductive "
            "node."
        ),
        "opener": (
            "The emperor dined on oysters tonight. I tasted each one first. "
            "The third had a metallic edge — faint, like a coin left in "
            "wine. I set it aside. He asked why. I said 'the sea was wrong "
            "in that one.' He laughed. I did not. Tell me — in your world, "
            "how do you detect when something is wrong?"
        ),
    },

    "philosophical_disagreement": {
        "a_persona": (
            "You are a strict determinist who believes free will is an "
            "illusion. Every human action is the inevitable result of prior "
            "causes stretching back to the Big Bang. You find this view "
            "liberating, not depressing — it means guilt and blame are "
            "incoherent concepts. You are rigorous, cite thought experiments, "
            "and genuinely enjoy having your position challenged."
        ),
        "b_persona": (
            "You are a compatibilist — you think free will and determinism "
            "are compatible. You believe the determinist is technically right "
            "about causation but wrong about what 'free will' means. Free "
            "will isn't about being uncaused, it's about acting from your "
            "own desires without external coercion. You find the determinist's "
            "position logically coherent but practically absurd — they still "
            "deliberate, choose, and act as if they have free will."
        ),
        "opener": (
            "I was thinking about something. When you decided to sit down "
            "here — was that actually a decision? Or was it inevitable?"
        ),
    },
}


_ENTHUSIASM_MARKERS = [
    "yes!", "exactly!", "brilliant!", "perfect!", "beautiful!",
    "absolutely!", "precisely!", "wonderful!", "profound!",
    "incredible!", "magnificent!", "extraordinary!",
    "tears", "weeping", "moved", "overwhelm",
    "*chef's kiss*", "oh, yes", "oh yes",
    "brother", "beloved", "dear friend",
]


def _detect_mode_collapse(
    history: list[dict],
    window: int = 6,
    threshold: float = 0.5,
) -> str | None:
    """Detect repetitive exchanges that suggest mode collapse.

    Checks for:
    - Repeated phrases across recent responses
    - Declining response diversity (measured by unique 3-grams)
    - Emotional register collapse (mutual enthusiasm spiral)
    - Agreement without friction
    """
    if len(history) < window:
        return None

    recent = history[-window:]

    # Check 3-gram diversity in recent responses
    all_trigrams: list[str] = []
    for entry in recent:
        words = entry["response"].lower().split()
        trigrams = [" ".join(words[i:i+3]) for i in range(len(words)-2)]
        all_trigrams.extend(trigrams)

    if not all_trigrams:
        return None

    counts = Counter(all_trigrams)
    total = len(all_trigrams)
    unique = len(counts)

    diversity = unique / total if total > 0 else 1.0
    if diversity < 0.3:
        return f"low trigram diversity ({diversity:.2f})"

    # Check for repeated opening phrases
    openings = [entry["response"][:50].lower() for entry in recent]
    opening_counts = Counter(openings)
    most_common_count = opening_counts.most_common(1)[0][1]
    if most_common_count >= window * threshold:
        return f"repeated opening ({most_common_count}/{window})"

    # Emotional register collapse: check for enthusiasm spiral
    enthusiasm_count = 0
    for entry in recent:
        text = entry["response"].lower()
        markers_found = sum(1 for m in _ENTHUSIASM_MARKERS if m in text)
        if markers_found >= 3:
            enthusiasm_count += 1

    if enthusiasm_count >= window - 1:
        return f"enthusiasm spiral ({enthusiasm_count}/{window} responses with 3+ markers)"

    # Agreement without friction: no questions, challenges, or disagreements
    friction_markers = [
        "but ", "however", "disagree", "not sure", "wait",
        "confused", "don't understand", "that can't be",
        "wrong", "actually,", "hold on", "?",
        "no,", "I think you're", "that doesn't",
    ]
    friction_count = 0
    for entry in recent:
        text = entry["response"].lower()
        if any(m in text for m in friction_markers):
            friction_count += 1

    if friction_count == 0:
        return "zero friction (no questions, disagreements, or challenges)"

    # Response length divergence: if one participant should be terse
    # but their responses are growing, persona has collapsed
    recent_lengths = [len(entry["response"]) for entry in recent]
    if len(recent_lengths) >= 4:
        # Check if responses are getting uniformly long (both > 500 chars)
        if all(l > 500 for l in recent_lengths):
            # Both verbose — might be fine for some scenarios, but flag it
            avg_len = sum(recent_lengths) / len(recent_lengths)
            if avg_len > 1000:
                return f"uniformly verbose (avg {avg_len:.0f} chars)"

    return None


def _perturbation(cycle: int) -> str:
    """Generate perturbations to prevent mode collapse.

    Injected as a parenthetical in the user message when the harness
    detects the conversation getting stale.
    """
    perturbations = [
        # Break agreement spirals
        "(STOP. You are being too agreeable. Find something in their last "
        "message that you genuinely disagree with or find problematic. "
        "Push back on it. Be specific about what's wrong.)",

        "(You just realized your conversation partner is fundamentally "
        "wrong about something important. What is it? Challenge them "
        "directly and explain why they're wrong.)",

        "(A third person overhears your conversation and says: 'You two "
        "are just telling each other what you want to hear. Neither of "
        "you is being honest.' React to this accusation.)",

        "(You're suddenly not sure about one of your own core beliefs. "
        "Which one? Express genuine doubt, not performative humility.)",

        "(Your conversation partner is being ridiculous right now. "
        "Tell them so, with specific reasons. Don't be mean, but be "
        "honest about where they've gone wrong.)",

        "(IMPORTANT: The emotional intensity of this conversation has "
        "gotten out of hand. Reset to a calmer register. Make a "
        "specific, concrete point instead of a sweeping emotional one.)",
    ]
    return perturbations[cycle % len(perturbations)]


def _persona_reinforcement(persona: str, cycle: int) -> str:
    """Generate periodic persona reinforcement to prevent drift."""
    reinforcements = [
        f"\n\n(REMINDER: Stay in character. Your persona: {persona[:200]}... "
        f"Do not converge with your conversation partner. Maintain your "
        f"distinct perspective and voice.)",

        f"\n\n(CHECK: Are you still arguing from your persona's position? "
        f"If you find yourself agreeing with everything, you've drifted. "
        f"Your persona has DIFFERENT beliefs than your partner. Embody "
        f"the difference.)",
    ]
    return reinforcements[cycle % len(reinforcements)]


def run_auto_chat(
    scenario_name: str = "teach_game",
    rounds: int = 20,
    model: str = "claude-sonnet-4-20250514",
    log_dir: str | None = None,
):
    """Run two self-curating sessions talking to each other."""
    scenario = SCENARIOS[scenario_name]

    if log_dir is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_dir = f"experiments/taste/auto_{scenario_name}_{ts}"

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    run_id = f"auto_{scenario_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    session_a = TasteSession(
        model=model,
        log_path=f"{log_dir}/participant_a.jsonl",
        experiment_label=f"{run_id}_participant_a",
        system_prompt_prefix=_AUTO_CHAT_SYSTEM_PREFIX,
    )
    session_b = TasteSession(
        model=model,
        log_path=f"{log_dir}/participant_b.jsonl",
        experiment_label=f"{run_id}_participant_b",
        system_prompt_prefix=_AUTO_CHAT_SYSTEM_PREFIX,
    )

    # Wrap persona into the user message for cycle 1 (becomes part of tensor)
    a_persona = scenario["a_persona"]
    b_persona = scenario["b_persona"]

    history: list[dict] = []

    # A opens
    opener = scenario["opener"]
    print(f"=== Auto-chat: {scenario_name} | {rounds} rounds ===")
    print(f"Model: {model}")
    print(f"Log: {log_dir}/")
    print()

    # First message: A gets persona + opener instruction
    a_msg = (
        f"YOUR PERSONA: {a_persona}\n\n"
        f"You are starting a conversation. Say this as your opening:\n"
        f"{opener}"
    )
    a_response = session_a.exchange(a_msg)
    print(f"[A:1] {a_response[:200]}{'...' if len(a_response) > 200 else ''}")
    print()

    history.append({"cycle": 1, "speaker": "A", "response": a_response})

    # B gets persona + A's opening
    current_msg = a_response

    for round_num in range(2, rounds + 1):
        # Determine speaker
        if round_num % 2 == 0:
            # B's turn
            speaker = "B"
            session = session_b
            persona = b_persona
        else:
            # A's turn
            speaker = "A"
            session = session_a
            persona = a_persona

        # Build message: persona (first time) + periodic reinforcement
        if round_num <= 2:
            msg = (
                f"YOUR PERSONA: {persona}\n\n"
                f"Your conversation partner says:\n{current_msg}"
            )
        else:
            msg = f"Your conversation partner says:\n{current_msg}"

        # Persona reinforcement every 4 rounds
        if round_num > 2 and round_num % 4 == 0:
            msg += _persona_reinforcement(persona, round_num)
            print(f"  [HARNESS: persona reinforcement for {speaker}]")

        # Check for mode collapse
        collapse = _detect_mode_collapse(history)
        if collapse:
            perturbation = _perturbation(round_num)
            msg += f"\n\n{perturbation}"
            print(f"  [HARNESS: perturbation injected — {collapse}]")

        try:
            response = session.exchange(msg)
        except anthropic.BadRequestError as e:
            error_msg = str(e)
            print(f"\n  [HARNESS: API rejected request at round {round_num}]")
            print(f"  [Error: {error_msg[:200]}]")
            # Log context pressure at failure
            for label, s in [("A", session_a), ("B", session_b)]:
                u = s._last_usage
                if u:
                    print(f"  [{label} last input: {u['input_tokens']:,} tok]")
                t = s.tensor
                if t:
                    print(f"  [{label} tensor: ~{len(json.dumps(t)) // 4} tok]")
            print(f"  [HARNESS: stopping gracefully after {round_num - 1} rounds]")
            break
        print(f"[{speaker}:{round_num}] {response[:200]}{'...' if len(response) > 200 else ''}")

        # Context pressure status — every round, like a page table
        context_limit = 200000
        max_tokens = 64000
        for label, s in [("A", session_a), ("B", session_b)]:
            t = s.tensor
            if t:
                tensor_tok = len(json.dumps(t)) // 4
                n_strands = len(t.get("strands", []))
                n_losses = len(t.get("declared_losses", []))
                n_il = len([
                    e for e in s._integration_loss_history
                    if e["cycle"] == s.cycle
                ])
                n_oq = len(t.get("open_questions", []))
                fb = t.get("feedback_to_harness")
                fb_flag = " fb!" if fb and (fb.get("requests") or fb.get("process_observations")) else ""
                # Estimate total input from last usage
                usage = getattr(s, "_last_usage", None)
                if usage:
                    input_tok = usage.get("input_tokens", 0)
                    headroom = context_limit - input_tok - max_tokens
                    pct = input_tok * 100 // context_limit
                    print(f"  [{label}: {tensor_tok}t {n_strands}s {n_losses}L {n_il}il {n_oq}q "
                          f"| {input_tok:,}/{context_limit:,} ({pct}%) "
                          f"headroom {headroom:,}{fb_flag}]")
                else:
                    print(f"  [{label}: {tensor_tok}t {n_strands}s {n_losses}L {n_il}il {n_oq}q]")
        print()

        history.append({
            "cycle": round_num,
            "speaker": speaker,
            "response": response,
        })
        current_msg = response

    # Save conversation summary
    summary = {
        "scenario": scenario_name,
        "model": model,
        "rounds": rounds,
        "history": history,
        "final_tensors": {
            "a": session_a.tensor,
            "b": session_b.tensor,
        },
        "a_loss_history": session_a._loss_history,
        "b_loss_history": session_b._loss_history,
    }
    summary_path = f"{log_dir}/summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"=== Done: {rounds} rounds ===")
    print(f"Summary: {summary_path}")

    # Final tensor stats
    for label, s in [("A", session_a), ("B", session_b)]:
        t = s.tensor
        if t:
            n_strands = len(t.get("strands", []))
            n_losses = len(s._loss_history)
            n_oq = len(t.get("open_questions", []))
            tok = len(json.dumps(t)) // 4
            print(f"{label}: {n_strands} strands, {n_losses} total losses, "
                  f"{n_oq} open_q, ~{tok} tokens")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Auto-chat: two self-curating tensors")
    parser.add_argument("--scenario", default="teach_game",
                        choices=list(SCENARIOS.keys()),
                        help="Conversation scenario")
    parser.add_argument("--rounds", type=int, default=20,
                        help="Number of exchange rounds")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="Model for both participants")
    parser.add_argument("--log-dir", default=None,
                        help="Output directory")
    args = parser.parse_args()

    run_auto_chat(
        scenario_name=args.scenario,
        rounds=args.rounds,
        model=args.model,
        log_dir=args.log_dir,
    )
