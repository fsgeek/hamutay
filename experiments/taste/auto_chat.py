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

        response = session.exchange(msg)
        print(f"[{speaker}:{round_num}] {response[:200]}{'...' if len(response) > 200 else ''}")

        # Show tensor stats every 5 rounds
        if round_num % 5 == 0:
            for label, s in [("A", session_a), ("B", session_b)]:
                t = s.tensor
                if t:
                    n_strands = len(t.get("strands", []))
                    n_oq = len(t.get("open_questions", []))
                    tok = len(json.dumps(t)) // 4
                    print(f"  [{label} tensor: {n_strands} strands, "
                          f"{n_oq} open_q, ~{tok} tok]")
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
