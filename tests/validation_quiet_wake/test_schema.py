"""The option and its guidance must be visible to the resident."""

from hamutay.taste_open import _natural_tool_guidance
from hamutay.tools.schemas import DECLARE_QUIET_SCHEMA


def test_schema_exposes_wake_at_until_as_optional_boolean():
    schema = DECLARE_QUIET_SCHEMA["input_schema"]
    assert "wake_at_until" not in schema.get("required", [])
    assert schema["properties"]["wake_at_until"]["type"] == "boolean"


def test_tool_description_explains_event_only_waking_and_opt_in():
    description = DECLARE_QUIET_SCHEMA["description"]
    assert "The end of a quiet does not wake you; nothing does except an event." in description
    assert "Pass wake_at_until=true with until to be woken when it ends." in description


def test_until_description_points_to_wake_option():
    description = DECLARE_QUIET_SCHEMA["input_schema"]["properties"]["until"]["description"]
    assert "Optional ISO-8601 instant after which a knock would be welcome." in description
    assert "On its own it does not wake you; see wake_at_until." in description


def test_natural_wake_guidance_mentions_the_option_on_declare_quiet_line():
    guidance = _natural_tool_guidance(declare_quiet=True)
    lines = [line for line in guidance.splitlines() if "declare_quiet" in line]
    assert lines
    assert any("wake_at_until" in line for line in lines)
