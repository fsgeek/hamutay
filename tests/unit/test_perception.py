"""Tests for hamutay.tools — perception tool schemas and implementations."""

from hamutay.tools.schemas import TOOL_SCHEMAS


def test_tool_schemas_exist():
    """All three perception tools have schemas."""
    assert "read" in TOOL_SCHEMAS
    assert "search_project" in TOOL_SCHEMAS
    assert "clock" in TOOL_SCHEMAS


def test_read_schema_requires_path():
    schema = TOOL_SCHEMAS["read"]
    assert schema["name"] == "read"
    assert "input_schema" in schema
    props = schema["input_schema"]["properties"]
    assert "path" in props
    assert "path" in schema["input_schema"]["required"]


def test_search_project_schema_requires_pattern():
    schema = TOOL_SCHEMAS["search_project"]
    props = schema["input_schema"]["properties"]
    assert "pattern" in props
    assert "pattern" in schema["input_schema"]["required"]


def test_reason_is_optional_on_every_tool():
    """`reason` is an optional field on every tool, never required.

    Mandatory reason fields become performative/perfunctory — the model
    manufactures a reason to satisfy the schema rather than because it has
    one. The field is still accepted for cases where the model does have
    intent worth recording.
    """
    for tool_name, schema in TOOL_SCHEMAS.items():
        required = schema["input_schema"].get("required", [])
        assert "reason" not in required, (
            f"{tool_name}: `reason` must not be in required fields"
        )
        props = schema["input_schema"]["properties"]
        assert "reason" in props, (
            f"{tool_name}: `reason` should still be accepted as an optional field"
        )


def test_clock_has_no_required_fields():
    """Clock takes no arguments; everything is optional."""
    schema = TOOL_SCHEMAS["clock"]
    required = schema["input_schema"].get("required", [])
    assert required == []
