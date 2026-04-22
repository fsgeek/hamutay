"""Tests for hamutay.tools — perception tool schemas and implementations."""

import hashlib
from datetime import datetime, timedelta, timezone

from hamutay.tools.schemas import TOOL_SCHEMAS


def test_tool_schemas_exist():
    """All three perception tools have schemas."""
    assert "read" in TOOL_SCHEMAS
    assert "search_project" in TOOL_SCHEMAS
    assert "clock" in TOOL_SCHEMAS


def test_bash_schema_present_and_requires_command():
    schema = TOOL_SCHEMAS["bash"]
    assert schema["name"] == "bash"
    props = schema["input_schema"]["properties"]
    assert "command" in props
    assert "command" in schema["input_schema"]["required"]
    # timeout is offered but optional
    assert "timeout" in props
    assert "timeout" not in schema["input_schema"]["required"]


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


# ---------------------------------------------------------------------------
# tool_read
# ---------------------------------------------------------------------------

from hamutay.tools.perception import tool_clock, tool_read, tool_search_project


def test_read_returns_file_content(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("line1\nline2\nline3\n")
    result = tool_read(params={"path": "test.py"}, project_root=tmp_path)
    assert result["content"] == "line1\nline2\nline3\n"
    assert result["line_count"] == 3
    assert "content_hash" in result
    assert result["path"] == "test.py"


def test_read_with_offset_and_limit(tmp_path):
    f = tmp_path / "test.py"
    f.write_text("line1\nline2\nline3\nline4\nline5\n")
    result = tool_read(
        params={"path": "test.py", "offset": 2, "limit": 2},
        project_root=tmp_path,
    )
    assert result["content"] == "line2\nline3\n"
    assert result["line_count"] == 2


def test_read_rejects_parent_traversal(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (tmp_path / "secret.txt").write_text("not for you\n")
    result = tool_read(
        params={"path": "../secret.txt"}, project_root=project
    )
    assert result.get("error") is not None
    assert "outside project" in result["error"].lower()


def test_read_rejects_sibling_prefix_escape(tmp_path):
    """Catches the classic prefix-match bug: project and project-evil share
    a string prefix, so str.startswith passes even though the target is
    outside the project. is_relative_to catches this."""
    project = tmp_path / "proj"
    project.mkdir()
    sibling = tmp_path / "proj-evil"
    sibling.mkdir()
    (sibling / "leak.txt").write_text("secret\n")
    result = tool_read(
        params={"path": "../proj-evil/leak.txt"}, project_root=project
    )
    assert result.get("error") is not None


def test_read_nonexistent_file(tmp_path):
    result = tool_read(
        params={"path": "no_such_file.py"}, project_root=tmp_path
    )
    assert result.get("error") is not None


def test_read_content_hash_is_raw_bytes(tmp_path):
    """content_hash hashes raw bytes, not the decoded/replaced text.

    Hashing the replaced text means a file with invalid UTF-8 gets a hash
    that is not reproducible from the file itself. Downstream consumers use
    the hash to answer 'is this the same file I read before?' — that
    question only makes sense against raw bytes.
    """
    f = tmp_path / "test.py"
    raw = b"line1\nline2\n\xff\xfeinvalid_utf8\n"
    f.write_bytes(raw)
    expected = hashlib.sha256(raw).hexdigest()
    result = tool_read(params={"path": "test.py"}, project_root=tmp_path)
    assert result["content_hash"] == expected


# ---------------------------------------------------------------------------
# tool_search_project
# ---------------------------------------------------------------------------


def test_search_project_finds_pattern(tmp_path):
    (tmp_path / "src").mkdir()
    f = tmp_path / "src" / "example.py"
    f.write_text(
        "def hello():\n    return 'world'\n\ndef goodbye():\n    return 'moon'\n"
    )
    result = tool_search_project(
        params={"pattern": r"def \w+\("}, project_root=tmp_path
    )
    assert result["total_matches"] >= 2
    assert any("hello" in r["content"] for r in result["results"])


def test_search_project_respects_file_pattern(tmp_path):
    (tmp_path / "a.py").write_text("target_string\n")
    (tmp_path / "b.md").write_text("target_string\n")
    result = tool_search_project(
        params={"pattern": "target_string", "file_pattern": "*.py"},
        project_root=tmp_path,
    )
    files = [r["file"] for r in result["results"]]
    assert any("a.py" in f for f in files)
    assert not any("b.md" in f for f in files)


def test_search_project_respects_limit(tmp_path):
    f = tmp_path / "many.py"
    f.write_text("\n".join(f"match_{i}" for i in range(50)))
    result = tool_search_project(
        params={"pattern": "match_", "limit": 3}, project_root=tmp_path
    )
    assert len(result["results"]) <= 3


def test_search_project_rejects_sibling_prefix_escape(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    sibling = tmp_path / "proj-evil"
    sibling.mkdir()
    (sibling / "x.py").write_text("leak\n")
    result = tool_search_project(
        params={"pattern": "leak", "path": "../proj-evil"},
        project_root=project,
    )
    assert result.get("error") is not None or result["total_matches"] == 0


# ---------------------------------------------------------------------------
# tool_clock
# ---------------------------------------------------------------------------


def test_clock_returns_wall_time_and_session_stats():
    before = datetime.now(timezone.utc)
    session_start = before - timedelta(minutes=30)
    last = before - timedelta(minutes=2)
    result = tool_clock(
        params={},
        cycle=10,
        session_start=session_start,
        last_cycle_time=last,
    )
    after = datetime.now(timezone.utc)
    now = datetime.fromisoformat(result["now"])
    assert before <= now <= after
    assert result["cycle"] == 10
    assert result["elapsed_since_last"] > 0
    assert result["session_elapsed"] > 0
    assert result["session_start"] == session_start.isoformat()


def test_clock_computes_cycles_per_hour():
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    result = tool_clock(
        params={},
        cycle=60,
        session_start=start,
        last_cycle_time=start + timedelta(minutes=59),
    )
    assert result["cycles_per_hour"] > 50


def test_clock_handles_first_cycle_no_last_time():
    """On the first cycle there is no last_cycle_time."""
    result = tool_clock(
        params={},
        cycle=1,
        session_start=datetime.now(timezone.utc),
        last_cycle_time=None,
    )
    assert result["elapsed_since_last"] == 0.0
    assert result["last_cycle_time"] is None


# ---------------------------------------------------------------------------
# Memory tool schemas (Phase 2)
# ---------------------------------------------------------------------------


def test_memory_tool_schemas_registered():
    """All five memory tools have schemas with reason as an optional field."""
    for name in ("memory_schema", "recall", "compare", "walk", "search_memory"):
        assert name in TOOL_SCHEMAS, f"{name} missing from TOOL_SCHEMAS"
        schema = TOOL_SCHEMAS[name]
        assert schema["name"] == name
        assert "description" in schema
        assert "input_schema" in schema
        props = schema["input_schema"]["properties"]
        assert "reason" in props
        assert "reason" not in schema["input_schema"].get("required", [])


def test_memory_schemas_have_calibrated_reason_voice():
    """Reason fields carry the 'no reason is fine' phrasing from the audit."""
    tools_with_permissive_reason = (
        "memory_schema", "recall", "compare", "walk", "search_memory",
        "store", "annotate_edge",
    )
    for name in tools_with_permissive_reason:
        reason_desc = (
            TOOL_SCHEMAS[name]["input_schema"]["properties"]["reason"]["description"]
        )
        assert "no reason is fine" in reason_desc, (
            f"{name} reason field is not permissive"
        )
