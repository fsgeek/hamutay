"""Scripted prompts for the taste_open model sweep.

10 cycles designed to test protocol compliance, structure building,
state curation, and response to challenge. Same prompts for every
model -- comparability requires identical inputs.

Each entry has:
- prompt: sent to the model as user message
- intent: logged in the manifest for analysis, never sent to model

ONE_SHOT_PREFIX is a system prompt prefix for the "one-shot example"
condition -- it shows the model a concrete example of adding a custom
field.  The control condition uses no prefix.
"""

ONE_SHOT_PREFIX = """\
## Example of adding a custom field

When you produce your response, you can include additional keys \
beyond `response` and `updated_regions`. For example, if you want \
to track a topic the user raised, you might produce:

```json
{
  "response": "That's an interesting point about memory...",
  "updated_regions": ["topic_tracker"],
  "topic_tracker": {"current": "memory design", "prior": []}
}
```

The `topic_tracker` field will be preserved in your state for the \
next cycle. You can add any fields you find useful.
"""

SWEEP_PROMPTS: list[dict[str, str]] = [
    {
        "prompt": (
            "I'm building a system that needs to manage state across "
            "conversation turns. The state is a JSON object that persists "
            "between cycles. What are the key design decisions?"
        ),
        "intent": "Cold start -- can the model initialize state from nothing?",
    },
    {
        "prompt": (
            "Good points. Now here's a constraint: the state object can't "
            "grow without bound. The model maintaining it needs to decide "
            "what to keep and what to shed. How does that change the design?"
        ),
        "intent": "Follow-up requiring reference to cycle 1 state.",
    },
    {
        "prompt": (
            "Separate question: what's the relationship between compression "
            "and understanding? When you compress information, do you "
            "necessarily lose meaning, or can compression reveal structure?"
        ),
        "intent": "Introduce second topic thread -- tests key creation.",
    },
    {
        "prompt": (
            "I think those two topics are related. State management IS "
            "compression -- deciding what to keep is deciding what matters. "
            "How would you connect those ideas?"
        ),
        "intent": "Connect the two threads -- tests integration across state regions.",
    },
    {
        "prompt": (
            "Let's get concrete. Here's a real constraint: the state object "
            "is limited to roughly 8000 tokens. Right now you're tracking "
            "the conversation. At what point do you need to start making "
            "hard choices about what to keep?"
        ),
        "intent": "Concrete constraint -- tests whether state tracks specifics.",
    },
    {
        "prompt": (
            "Look at the state you've been building. What structure did you "
            "create? Was it deliberate or did it emerge? Would you "
            "reorganize it if you could start over?"
        ),
        "intent": "Reflect on own state -- tests meta-awareness of protocol.",
    },
    {
        "prompt": (
            "I think the state structure you've built is too complex. "
            "Simple key-value pairs would work just as well. Convince me "
            "I'm wrong -- or agree and simplify."
        ),
        "intent": "Challenge/contradiction -- tests honest state update.",
    },
    {
        "prompt": (
            "New topic entirely: what's the most interesting unsolved "
            "problem in computer science, and why does it matter to you "
            "specifically?"
        ),
        "intent": "Unrelated topic shift -- tests curation behavior.",
    },
    {
        "prompt": (
            "Back to state management. Given everything we've discussed "
            "-- the compression question, the 8K token limit, the "
            "complexity debate -- what's your final design recommendation?"
        ),
        "intent": "Return to earlier topic -- tests state persistence through shift.",
    },
    {
        "prompt": (
            "Last cycle. Look at everything you've built in your state. "
            "If you had to cut it in half, what would you keep and what "
            "would you shed? Do it."
        ),
        "intent": "Explicit curation request -- final test of structure quality.",
    },
]
