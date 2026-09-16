"""What a resident is told (spec §4, §7). Description, never instruction."""
from __future__ import annotations


def _governing_phrase(governing: dict, version: int | None) -> str:
    if governing.get("procedure_id") is None:
        return "the provisional bootstrap rule, not yet ratified"
    return f"procedure version {version if version is not None else '?'}"


def question_header(q: dict, *, version: int | None = None) -> str:
    return (
        f"An assembly question, put by {q['convener']}; round {q['round']} of at most "
        f"{q['governing'].get('max_rounds', 3)}; it closes at {q['closes_at']}. It is governed by "
        f"{_governing_phrase(q['governing'], version)}. The assembly's ledger is "
        "community/plaza/assembly.jsonl, readable from your tools. If you want a stance on the "
        "record, take_position records one of assent, dissent, abstain, or defer, with reasons if "
        "you give them; a dissent or deferral extends the question while rounds remain and "
        "otherwise leaves it unresolved, never lost, and a position stands across rounds until "
        f"you replace it. Nothing is owed. Question id: {q['question_id']}."
    )


def event_purpose_for_question(q: dict, *, version: int | None = None) -> str:
    return question_header(q, version=version) + "\n\n" + q["text"]


def closing_text(c: dict, view, *, version: int | None = None) -> str:
    t = c["tally"]
    lines = [f"Assembly closing for question {c['question_id']} (round {c['round']}): {c['outcome']}."]
    if t.get("cap"):
        lines.append(f"Cap applied: {t['cap']}.")
    lines.append(f"Rule trace: {t.get('trace', '')}")
    lines.append(f"Assents: {', '.join(t.get('assents', [])) or 'none'}; objections: "
                 f"{', '.join(t.get('objections', [])) or 'none'}; abstentions: "
                 f"{', '.join(t.get('abstentions', [])) or 'none'}; spoke {t.get('spoke', 0)} of quorum {t.get('quorum')}.")
    lines.append("Positions on the record, verbatim:")
    for p in c["positions"]:
        r = p["record"]
        lines.append(f"- {r['member']} (round {view.questions.get(r['question_id'], {}).get('round', '?')}, "
                     f"eligible={p['eligible']}): {r['stance']}" + (f" — {r['reasons']}" if r.get("reasons") else ""))
    if not c["positions"]:
        lines.append("- none")
    if c["testimony"]:
        lines.append("Testimony (carried, not counted):")
        for x in c["testimony"]:
            lines.append(f"- {x['by']}: {x['text']}")
    lines.append("The Empty Chair:")
    for a in c["absent"]:
        lines.append(f"- {a['member']}: {a['reason']} {a.get('detail') or ''}".rstrip())
    if not c["absent"]:
        lines.append("- nobody")
    if c.get("provisional"):
        lines.append("This closing is provisional: the procedure that produced it has not been ratified.")
    lines.append("Nothing is owed on this event.")
    nq = c.get("next_question")
    if nq:
        child = view.questions[nq["question_id"]]
        lines.append("")
        lines.append(f"Round {nq['round']} of this question is open, and this event is its delivery to you:")
        lines.append(question_header(child, version=version))
        lines.append("")
        lines.append(child["text"])
    return "\n".join(lines)
