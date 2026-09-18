"""What a directed message becomes in the recipient's store (spec §4)."""
from __future__ import annotations

from hamutay.events import build_inbound_event

from .ids import door_name, is_door


def purpose_for(message: dict) -> str:
    sender = message["from"]
    n = message["seq"]
    if is_door(sender):
        answer = (f'If you wish to answer, send_message(to="{door_name(sender)}", text=...) reaches that '
                  "door; nothing obliges you to.")
    else:
        answer = 'The sender is a human who reads the plaza; a post (to="plaza") is how to answer.'
    header = (f"A message from {sender}, carried by the plaza (message {message['message_id']}, plaza seq {n}, "
              f"sent {message['sent_at']}). The whole plaza is readable at community/plaza/plaza.jsonl, one "
              f"record per line, seq equals line number; read(path, offset={n - 1}, limit=1) is this "
              f"message's line. {answer}")
    return header + "\n\n" + message["text"]


def inbound_event_for(message: dict) -> dict:
    """The pending event this message becomes in its recipient's store.

    Deterministic in every field: event_id from delivery.event_id (so a
    retried delivery lands the same event, not a duplicate), and created_at
    from the message's own sent_at rather than wall-clock time, since
    build_inbound_event otherwise stamps utc_now_iso() and two calls for
    the same message would then disagree.
    """
    d = message["delivery"]
    ev = build_inbound_event(purpose=purpose_for(message), sender=message["from"],
                             label=f"plaza:{message['message_id']}", event_id=d["event_id"], origin="member")
    ev["created_at"] = message["sent_at"]
    ev["defer_to_declared_quiet"] = True
    return ev
