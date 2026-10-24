"""Independent contract tests using only synthetic environment values.

Probes report presence and equality as booleans, never environment values.
The two explicitly named exceptions are exact, case-sensitive names; the
underscore-separated secret parts are case-insensitive.
"""

import json
import os
import shlex
import sys

import pytest

from hamutay.tools.bash import command_env, tool_bash


REMOVED_NAMES = (
    "OPENROUTER_API_KEY",
    "HAMUTAY_ANTHROPIC_API_KEY",
    "PYPI_DEPLOY_KEY_REAL",
    "TOGETHER_OBSERVABILITY_PROJECT_KEY",
    "GITHUB_TOKEN",
    "my_api_key",
    "DB_PASSWORD",
    "GIT_ASKPASS",
    "SSH_AUTH_SOCK",
    "HAMUTAY_ANTHROPIC_WORKSPACE_ID",
    "SERVICE_SECRET_VALUE",
    "SERVICE_PASSWD_VALUE",
    "SERVICE_CREDENTIAL_VALUE",
    "SERVICE_CREDENTIALS_VALUE",
    "MiXeD_ToKeN_Value",
    "_KEY_",
    "KEY",
)

KEPT_NAMES = (
    "PATH",
    "HOME",
    "LANG",
    "KEYBOARD_LAYOUT",
    "MONKEY",
    "TOKENIZERS_PARALLELISM",
    "APIKEY",
    "TOKENS",
    "SECRETS",
    "PASSWORDLESS",
    "CREDENTIALSTORE",
    "NOTASKPASS",
    "X_SSH_AUTH_SOCK",
    "SSH_AUTH_SOCK_EXTRA",
    "X_HAMUTAY_ANTHROPIC_WORKSPACE_ID",
    "HAMUTAY_ANTHROPIC_WORKSPACE_ID_EXTRA",
    "NORMAL_SETTING",
    "EMPTY_VALUE",
)

CASE_VARIANTS = (
    "ssh_auth_sock",
    "Ssh_Auth_Sock",
    "hamutay_anthropic_workspace_id",
    "Hamutay_Anthropic_Workspace_Id",
)


@pytest.fixture(autouse=True)
def fake_environment(monkeypatch, tmp_path):
    # Replace the mapping without reading or copying any inherited credentials.
    monkeypatch.setattr(os, "environ", {})
    values = {name: f"fake-value-{name}" for name in REMOVED_NAMES + KEPT_NAMES}
    values.update(
        PATH=os.defpath,
        HOME=str(tmp_path),
        LANG="C",
        EMPTY_VALUE="",
    )
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return values


def _probe(tmp_path, expected):
    """Run the real tool; return only boolean observations for specified names."""
    script = (
        "import json, os; "
        f"expected = {expected!r}; "
        "print(json.dumps({name: [name in os.environ, "
        "os.environ.get(name) == value] for name, value in expected.items()}))"
    )
    result = tool_bash(
        {"command": shlex.join([sys.executable, "-I", "-S", "-c", script])},
        project_root=tmp_path,
    )
    assert "error" not in result
    assert result["exit_code"] == 0
    assert result["stderr"] == ""
    return json.loads(result["stdout"])


@pytest.mark.parametrize("name", REMOVED_NAMES)
def test_tool_bash_removes_secret_names(fake_environment, tmp_path, name):
    observed = _probe(tmp_path, {name: fake_environment[name]})
    assert observed[name] == [False, False]


@pytest.mark.parametrize("name", KEPT_NAMES)
def test_tool_bash_preserves_values_and_lookalikes(fake_environment, tmp_path, name):
    observed = _probe(tmp_path, {name: fake_environment[name]})
    assert observed[name] == [True, True]


@pytest.mark.parametrize("name", CASE_VARIANTS)
def test_tool_bash_special_names_are_case_insensitive(
    fake_environment, monkeypatch, tmp_path, name
):
    monkeypatch.setenv(name, "fake-case-variant")
    observed = _probe(tmp_path, {name: "fake-case-variant"})
    assert observed[name] == [False, False]


def test_tool_bash_does_not_mutate_parent_environment(fake_environment, tmp_path):
    parent_mapping = os.environ
    before = dict(parent_mapping)  # This mapping contains only fixture values.
    observed = _probe(tmp_path, fake_environment)
    assert os.environ is parent_mapping
    # Report only a boolean if this invariant fails, never the mapping values.
    assert (dict(os.environ) == before) is True
    assert observed["OPENROUTER_API_KEY"] == [False, False]
    assert observed["HOME"] == [True, True]


def test_tool_bash_does_not_gate_commands(fake_environment, tmp_path):
    marker = tmp_path / "command-ran"
    command = (
        'test "${OPENROUTER_API_KEY+x}" != x && '
        f"printf ran > {shlex.quote(str(marker))}; "
        "printf stdout-marker; printf stderr-marker >&2; exit 23"
    )
    result = tool_bash({"command": command}, project_root=tmp_path)
    assert result == {
        "stdout": "stdout-marker",
        "stderr": "stderr-marker",
        "exit_code": 23,
    }
    assert marker.read_text() == "ran"


@pytest.mark.parametrize(
    "part",
    ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL", "CREDENTIALS", "ASKPASS"),
)
@pytest.mark.parametrize("pattern", ("{}_TAIL", "HEAD_{}_TAIL", "HEAD_{}"))
def test_command_env_removes_parts_in_any_position(part, pattern):
    name = pattern.format(part.swapcase())
    source = {name: "fake-secret", "MONKEY": "fake-kept"}
    filtered = command_env(source)
    assert filtered == {"MONKEY": "fake-kept"}
    assert source == {name: "fake-secret", "MONKEY": "fake-kept"}


def test_command_env_explicit_dict_is_authoritative(fake_environment, monkeypatch):
    monkeypatch.setenv("PARENT_ONLY", "fake-parent-only")
    source = {"ONLY_EXPLICIT": "fake-explicit", "EMPTY": "", "GITHUB_TOKEN": "fake-token"}
    filtered = command_env(source)
    assert filtered == {"ONLY_EXPLICIT": "fake-explicit", "EMPTY": ""}
    assert source == {
        "ONLY_EXPLICIT": "fake-explicit",
        "EMPTY": "",
        "GITHUB_TOKEN": "fake-token",
    }
    filtered["ONLY_EXPLICIT"] = "fake-changed"
    assert source["ONLY_EXPLICIT"] == "fake-explicit"


def test_command_env_explicit_empty_dict_does_not_fall_back(fake_environment):
    assert command_env({}) == {}


def test_command_env_explicit_dict_special_names_are_case_insensitive():
    source = {
        "SSH_AUTH_SOCK": "fake-socket",
        "HAMUTAY_ANTHROPIC_WORKSPACE_ID": "fake-workspace",
        **{name: "fake-case-variant" for name in CASE_VARIANTS},
    }
    assert command_env(source) == {}
