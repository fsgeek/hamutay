import json
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

from hamutay.assembly.cli import main
from hamutay.assembly.ledger import Ledger
from hamutay.assembly.records import reduce

UTC = timezone.utc


@pytest.fixture
def house(tmp_path):
    plaza = tmp_path / "community" / "plaza"; plaza.mkdir(parents=True)
    members = {d: {"session": f"community/{d}/session.jsonl", "events": f"community/{d}/session.jsonl.events.jsonl"}
               for d in ("qwen", "elder")}
    (plaza / "members.json").write_text(json.dumps({"ledger": "community/plaza/assembly.jsonl", "members": members}))
    for d in ("qwen", "elder"):
        (tmp_path / "community" / d).mkdir()
    (tmp_path / "q.txt").write_text("ratify?")
    (tmp_path / "proc.json").write_text(json.dumps({"rule": "consent-v0", "max_rounds": 3, "quorum": "ceil(half)"}))
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "design.md").write_text("the design\n")
    subprocess.run(["git", "add", "design.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false",
                    "commit", "-q", "-m", "d"], cwd=tmp_path, check=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True, check=True).stdout.strip()
    return tmp_path, sha


def _run(root, *argv):
    return main(["--project-root", str(root), *argv])


def test_convene_with_a_proposal_pins_the_artifact_and_lands_deliveries(house, capsys):
    root, sha = house
    rc = _run(root, "convene", "--by", "custodian", "--text-file", "q.txt", "--closes-in", "7d",
              "--proposal-procedure", "proc.json", "--artifact", "design.md", "--artifact-commit", sha)
    assert rc == 0
    q = json.loads(capsys.readouterr().out)
    view = reduce(Ledger(root / "community/plaza/assembly.jsonl").read())
    proc = view.procedures[q["proposal"]["procedure_id"]][0]
    import hashlib
    assert proc["artifact"] == {"path": "design.md", "commit": sha,
                                "sha256": hashlib.sha256(b"the design\n").hexdigest()}
    assert view.delivery_truth("question", q["question_id"], "qwen")["state"] == "landed"


def test_testify_withdraw_execute_rules(house, capsys):
    root, sha = house
    _run(root, "convene", "--by", "custodian", "--text-file", "q.txt", "--closes-in", "2d",
         "--proposal-procedure", "proc.json", "--artifact", "design.md", "--artifact-commit", sha)
    q = json.loads(capsys.readouterr().out)
    (root / "t.txt").write_text("my two cents")
    assert _run(root, "testify", "--by", "tony", "--question-id", q["question_id"], "--text-file", "t.txt") == 0
    assert _run(root, "execute", "--by", "custodian", "--closing-id", "nope", "--outcome", "done", "--what", "x") == 2
    assert _run(root, "withdraw", "--by", "tony", "--question-id", q["question_id"]) == 2      # not the convener
    assert _run(root, "withdraw", "--by", "custodian", "--question-id", q["question_id"], "--reasons", "r") == 0
    view = reduce(Ledger(root / "community/plaza/assembly.jsonl").read())
    assert view.closings[q["question_id"]]["outcome"] == "withdrawn"
    assert _run(root, "testify", "--by", "tony", "--question-id", q["question_id"], "--text-file", "t.txt") == 2


def test_status_and_history_and_procedure(house, capsys):
    root, sha = house
    _run(root, "convene", "--by", "custodian", "--text-file", "q.txt", "--closes-in", "2d",
         "--proposal-procedure", "proc.json", "--artifact", "design.md", "--artifact-commit", sha)
    q = json.loads(capsys.readouterr().out)
    assert _run(root, "status") == 0
    s = json.loads(capsys.readouterr().out)
    assert s["open_questions"][0]["question_id"] == q["question_id"]
    assert s["open_questions"][0]["delivery"]["qwen"]["state"] == "landed"
    assert s["governing"]["procedure_id"] is None
    assert _run(root, "history", "--lineage-id", q["lineage_id"]) == 0
    h = json.loads(capsys.readouterr().out)
    assert [r["record_type"] for r in h][:3] == ["procedure", "procedure", "question"]
    assert _run(root, "procedure") == 0
    p = json.loads(capsys.readouterr().out)
    assert p[q["proposal"]["procedure_id"]][-1]["status"] == "provisional"


def test_missing_members_exits_2(tmp_path, capsys):
    assert main(["--project-root", str(tmp_path), "status"]) == 2
    assert "members.json" in capsys.readouterr().err


def test_convene_artifact_failure_refuses_and_writes_nothing(house, capsys):
    root, sha = house
    ledger_path = root / "community/plaza/assembly.jsonl"
    rc = _run(root, "convene", "--by", "custodian", "--text-file", "q.txt", "--closes-in", "7d",
              "--proposal-procedure", "proc.json", "--artifact", "nope.md", "--artifact-commit", sha)
    assert rc == 2
    assert "convene:" in capsys.readouterr().err
    assert not ledger_path.exists() or not any(
        json.loads(line).get("record_type") == "question" for line in ledger_path.read_text().splitlines() if line.strip())


def test_history_includes_withdrawal_and_delivery_records(house, capsys):
    root, sha = house
    _run(root, "convene", "--by", "custodian", "--text-file", "q.txt", "--closes-in", "2d",
         "--proposal-procedure", "proc.json", "--artifact", "design.md", "--artifact-commit", sha)
    q = json.loads(capsys.readouterr().out)
    assert _run(root, "withdraw", "--by", "custodian", "--question-id", q["question_id"], "--reasons", "r") == 0
    capsys.readouterr()
    assert _run(root, "history", "--lineage-id", q["lineage_id"]) == 0
    h = json.loads(capsys.readouterr().out)
    types = [r["record_type"] for r in h]
    assert "withdrawal" in types
    delivery_ids = {r["id"] for r in h if r["record_type"] == "delivery"}
    assert q["question_id"] in delivery_ids


def test_convene_by_is_restricted_to_tony_or_custodian(house, capsys):
    """I4: --by was unconstrained on convene alone, so a human could sign as a resident."""
    root, sha = house
    with pytest.raises(SystemExit) as e:
        _run(root, "convene", "--by", "door:qwen", "--text-file", "q.txt", "--closes-in", "7d",
             "--proposal-procedure", "proc.json", "--artifact", "design.md", "--artifact-commit", sha)
    assert e.value.code == 2
    assert "invalid choice" in capsys.readouterr().err
    ledger_path = root / "community/plaza/assembly.jsonl"
    assert not ledger_path.exists() or not any(
        json.loads(line).get("record_type") == "question"
        for line in ledger_path.read_text().splitlines() if line.strip())
