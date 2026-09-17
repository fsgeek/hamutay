"""The plaza: how residents reach each other. Spec: docs/superpowers/specs/2026-09-16-plaza-design.md (r4)."""
from .ids import PLAZA_NS  # noqa: F401
from .note import note_lower_bound, note_producer, plaza_note  # noqa: F401
from .pass_ import PlazaMemo, run_plaza_pass  # noqa: F401
from .records import MAX_TEXT_CHARS, SEND_CAP, View, build_delivery, build_message, reduce, validate_plaza  # noqa: F401,E501
from .send import SendRefused, send  # noqa: F401
