"""Tests for unscoped read/write/edit perception tools."""

from hamutay.tools.perception import tool_edit, tool_read, tool_write
from hamutay.tools.schemas import TOOL_SCHEMAS


# ---------------------------------------------------------------------------
# Schema registration
# ---------------------------------------------------------------------------


def test_write_schema_registered():
    schema = TOOL_SCHEMAS["write"]
    assert schema["name"] == "write"
    required = schema["input_schema"]["required"]
    assert "path" in required
    assert "content" in required
    assert "reason" not in required


def test_edit_schema_registered():
    schema = TOOL_SCHEMAS["edit"]
    assert schema["name"] == "edit"
    required = schema["input_schema"]["required"]
    assert "path" in required
    assert "old_string" in required
    assert "new_string" in required
    assert "reason" not in required
    assert "replace_all" not in required


def test_edit_schema_has_replace_all():
    props = TOOL_SCHEMAS["edit"]["input_schema"]["properties"]
    assert "replace_all" in props
    assert props["replace_all"]["type"] == "boolean"


# ---------------------------------------------------------------------------
# tool_read: unscoped — absolute paths now accepted
# ---------------------------------------------------------------------------


def test_read_relative_path_resolves_against_project_root(tmp_path):
    (tmp_path / "hello.txt").write_text("contents\n")
    result = tool_read({"path": "hello.txt"}, project_root=tmp_path)
    assert result["content"] == "contents\n"
    assert result["line_count"] == 1


def test_read_absolute_path_accepted(tmp_path):
    """Absolute paths are no longer scoped to project_root."""
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "file.txt"
    target.write_text("outside content\n")

    project = tmp_path / "project"
    project.mkdir()

    result = tool_read({"path": str(target)}, project_root=project)
    assert "error" not in result
    assert result["content"] == "outside content\n"


def test_read_relative_parent_traversal_now_resolves(tmp_path):
    """Relative ../escape paths resolve to whatever they point at.

    Under the old scoped read, ../secret.txt returned an error.
    Under the new unscoped read, it resolves and succeeds if the file exists.
    This test documents the intentional behavior change.
    """
    project = tmp_path / "proj"
    project.mkdir()
    sibling = tmp_path / "secret.txt"
    sibling.write_text("reachable\n")

    result = tool_read({"path": "../secret.txt"}, project_root=project)
    assert "error" not in result
    assert result["content"] == "reachable\n"


def test_read_nonexistent_file_returns_error(tmp_path):
    result = tool_read({"path": "no_such_file.txt"}, project_root=tmp_path)
    assert "error" in result


def test_read_limit_zero_returns_no_lines(tmp_path):
    (tmp_path / "many.txt").write_text("line1\nline2\n")
    result = tool_read(
        {"path": "many.txt", "limit": 0},
        project_root=tmp_path,
    )
    assert "error" not in result
    assert result["content"] == ""
    assert result["line_count"] == 0


def test_read_negative_limit_returns_error(tmp_path):
    (tmp_path / "many.txt").write_text("line1\nline2\n")
    result = tool_read(
        {"path": "many.txt", "limit": -1},
        project_root=tmp_path,
    )
    assert "error" in result
    assert "limit" in result["error"]


# ---------------------------------------------------------------------------
# tool_write
# ---------------------------------------------------------------------------


def test_write_creates_file(tmp_path):
    result = tool_write(
        {"path": "new_file.txt", "content": "hello\n"},
        project_root=tmp_path,
    )
    assert "error" not in result
    assert result["path"] == "new_file.txt"
    assert result["bytes_written"] == len("hello\n".encode())
    assert (tmp_path / "new_file.txt").read_text() == "hello\n"


def test_write_overwrites_existing_file(tmp_path):
    f = tmp_path / "existing.txt"
    f.write_text("old content\n")
    result = tool_write(
        {"path": "existing.txt", "content": "new content\n"},
        project_root=tmp_path,
    )
    assert "error" not in result
    assert f.read_text() == "new content\n"


def test_write_creates_parent_directories(tmp_path):
    result = tool_write(
        {"path": "a/b/c/deep.txt", "content": "deep\n"},
        project_root=tmp_path,
    )
    assert "error" not in result
    assert (tmp_path / "a" / "b" / "c" / "deep.txt").read_text() == "deep\n"


def test_write_absolute_path(tmp_path):
    target = tmp_path / "abs_target.txt"
    project = tmp_path / "project"
    project.mkdir()
    result = tool_write(
        {"path": str(target), "content": "absolute\n"},
        project_root=project,
    )
    assert "error" not in result
    assert target.read_text() == "absolute\n"


def test_write_parent_traversal_path_is_unscoped(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    result = tool_write(
        {"path": "../sibling.txt", "content": "outside\n"},
        project_root=project,
    )
    assert "error" not in result
    assert (tmp_path / "sibling.txt").read_text() == "outside\n"


def test_write_returns_error_when_target_is_directory(tmp_path):
    (tmp_path / "dir_target").mkdir()
    result = tool_write(
        {"path": "dir_target", "content": "not a file\n"},
        project_root=tmp_path,
    )
    assert "error" in result


def test_write_empty_content(tmp_path):
    result = tool_write(
        {"path": "empty.txt", "content": ""},
        project_root=tmp_path,
    )
    assert "error" not in result
    assert result["bytes_written"] == 0
    assert (tmp_path / "empty.txt").read_text() == ""


def test_write_returns_bytes_written(tmp_path):
    content = "café\n"  # non-ASCII — bytes != len(str)
    result = tool_write(
        {"path": "unicode.txt", "content": content},
        project_root=tmp_path,
    )
    assert result["bytes_written"] == len(content.encode("utf-8"))


# ---------------------------------------------------------------------------
# tool_edit
# ---------------------------------------------------------------------------


def test_edit_replaces_unique_string(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("def hello():\n    return 'world'\n")
    result = tool_edit(
        {"path": "code.py", "old_string": "world", "new_string": "earth"},
        project_root=tmp_path,
    )
    assert "error" not in result
    assert result["path"] == "code.py"
    assert result["replacements"] == 1
    assert f.read_text() == "def hello():\n    return 'earth'\n"


def test_edit_fails_if_old_string_not_found(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("def hello():\n    return 'world'\n")
    result = tool_edit(
        {"path": "code.py", "old_string": "not_present", "new_string": "x"},
        project_root=tmp_path,
    )
    assert "error" in result
    assert f.read_text() == "def hello():\n    return 'world'\n"


def test_edit_fails_if_old_string_not_unique(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("x = 1\nx = 2\n")
    result = tool_edit(
        {"path": "code.py", "old_string": "x", "new_string": "y"},
        project_root=tmp_path,
    )
    assert "error" in result
    assert result.get("occurrence_count") == 2
    # File must be unchanged
    assert f.read_text() == "x = 1\nx = 2\n"


def test_edit_replace_all_replaces_every_occurrence(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("x = 1\nx = 2\n")
    result = tool_edit(
        {
            "path": "code.py",
            "old_string": "x",
            "new_string": "y",
            "replace_all": True,
        },
        project_root=tmp_path,
    )
    assert "error" not in result
    assert result["replacements"] == 2
    assert f.read_text() == "y = 1\ny = 2\n"


def test_edit_fails_on_nonexistent_file(tmp_path):
    result = tool_edit(
        {"path": "no_such.py", "old_string": "x", "new_string": "y"},
        project_root=tmp_path,
    )
    assert "error" in result


def test_edit_rejects_empty_old_string_even_with_replace_all(tmp_path):
    f = tmp_path / "code.py"
    original = "abc\n"
    f.write_text(original)
    result = tool_edit(
        {
            "path": "code.py",
            "old_string": "",
            "new_string": "X",
            "replace_all": True,
        },
        project_root=tmp_path,
    )
    assert "error" in result
    assert "empty" in result["error"]
    assert f.read_text() == original


def test_edit_absolute_path(tmp_path):
    target = tmp_path / "abs.txt"
    target.write_text("alpha beta\n")
    project = tmp_path / "project"
    project.mkdir()
    result = tool_edit(
        {"path": str(target), "old_string": "alpha", "new_string": "gamma"},
        project_root=project,
    )
    assert "error" not in result
    assert target.read_text() == "gamma beta\n"


def test_edit_parent_traversal_path_is_unscoped(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("alpha\n")
    result = tool_edit(
        {"path": "../outside.txt", "old_string": "alpha", "new_string": "beta"},
        project_root=project,
    )
    assert "error" not in result
    assert target.read_text() == "beta\n"


def test_edit_returns_error_when_target_is_directory(tmp_path):
    (tmp_path / "dir_target").mkdir()
    result = tool_edit(
        {"path": "dir_target", "old_string": "a", "new_string": "b"},
        project_root=tmp_path,
    )
    assert "error" in result


def test_edit_preserves_file_on_non_unique_without_replace_all(tmp_path):
    """Atomicity of the uniqueness guard: file must be unchanged on failure."""
    original = "foo bar foo\n"
    f = tmp_path / "f.txt"
    f.write_text(original)
    tool_edit(
        {"path": "f.txt", "old_string": "foo", "new_string": "baz"},
        project_root=tmp_path,
    )
    assert f.read_text() == original
