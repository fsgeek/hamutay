"""Independent tests of the append-only evidence contract and the CLI.

The scientific value of this package rests on evidence that cannot be
retroactively edited and on a registered profile whose scientific counts
cannot be overridden from the command line. These tests attack both.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from hamutay.turboquant.artifacts import (
    canonical_json_bytes,
    create_run_directory,
    sha256_file,
)
from hamutay.turboquant.qualify import build_parser, run_registered_workers


class TestCanonicalJson:
    def test_is_sorted_compact_and_newline_terminated(self):
        assert canonical_json_bytes({"z": 1, "a": [2, 3]}) == b'{"a":[2,3],"z":1}\n'

    def test_key_order_of_the_input_does_not_change_the_bytes(self):
        """Otherwise an artifact hash depends on dict construction order."""
        assert canonical_json_bytes({"b": 1, "a": 2, "c": 3}) == canonical_json_bytes(
            {"c": 3, "a": 2, "b": 1}
        )

    def test_nested_structures_are_sorted_at_every_depth(self):
        encoded = canonical_json_bytes({"outer": {"z": 1, "a": {"y": 2, "b": 3}}})
        assert encoded == b'{"outer":{"a":{"b":3,"y":2},"z":1}}\n'

    def test_no_insignificant_whitespace_is_emitted(self):
        encoded = canonical_json_bytes({"a": 1, "b": [1, 2], "c": {"d": 4}})
        assert b" " not in encoded
        assert encoded.count(b"\n") == 1
        assert encoded.endswith(b"\n")

    def test_output_is_valid_json_that_round_trips(self):
        value = {"gate": "mse_distortion", "passed": True, "observed": 0.36089}
        assert json.loads(canonical_json_bytes(value).decode("utf-8")) == value

    def test_non_finite_floats_are_rejected(self):
        """allow_nan=False: NaN/Infinity are not valid JSON and would make an
        evidence artifact unparseable by conforming readers."""
        for bad in (float("nan"), float("inf"), float("-inf")):
            with pytest.raises(ValueError):
                canonical_json_bytes({"value": bad})

    def test_unicode_is_preserved_rather_than_escaped(self):
        encoded = canonical_json_bytes({"note": "Hamut'ay é"})
        assert "é".encode("utf-8") in encoded

    def test_encoding_is_deterministic_across_calls(self):
        value = {"b": [3, 2, 1], "a": {"n": 1.5}}
        assert canonical_json_bytes(value) == canonical_json_bytes(value)


class TestRunDirectory:
    def test_creates_the_directory(self, tmp_path):
        created = create_run_directory(tmp_path, "registered-001")
        assert created.is_dir()

    def test_refuses_to_overwrite_an_existing_run(self, tmp_path):
        """Append-only evidence: a second run under the same ID must fail."""
        create_run_directory(tmp_path, "registered-001")
        with pytest.raises(FileExistsError):
            create_run_directory(tmp_path, "registered-001")

    def test_refuses_even_when_the_existing_run_is_empty(self, tmp_path):
        target = tmp_path / "r1-initial"
        target.mkdir(parents=True)
        with pytest.raises(FileExistsError):
            create_run_directory(tmp_path, "r1-initial")

    def test_refusal_does_not_disturb_existing_contents(self, tmp_path):
        created = create_run_directory(tmp_path, "r1-initial")
        evidence = created / "qualification.json"
        evidence.write_bytes(b'{"status":"passed"}\n')

        with pytest.raises(FileExistsError):
            create_run_directory(tmp_path, "r1-initial")
        assert evidence.read_bytes() == b'{"status":"passed"}\n'

    def test_distinct_run_ids_coexist(self, tmp_path):
        first = create_run_directory(tmp_path, "r1-initial")
        second = create_run_directory(tmp_path, "r1-repair")
        assert first.is_dir() and second.is_dir()
        assert first != second


class TestFileHashing:
    def test_matches_hashlib_over_the_same_bytes(self, tmp_path):
        import hashlib

        target = tmp_path / "artifact.bin"
        payload = b"turboquant evidence \x00\x01\x02"
        target.write_bytes(payload)
        assert sha256_file(target) == hashlib.sha256(payload).hexdigest()

    def test_is_lowercase_hex_of_the_expected_length(self, tmp_path):
        target = tmp_path / "a.json"
        target.write_bytes(b"{}\n")
        digest = sha256_file(target)
        assert len(digest) == 64
        assert digest == digest.lower()
        int(digest, 16)

    def test_detects_a_single_byte_change(self, tmp_path):
        target = tmp_path / "a.json"
        target.write_bytes(b'{"a":1}\n')
        before = sha256_file(target)
        target.write_bytes(b'{"a":2}\n')
        assert sha256_file(target) != before

    def test_empty_file_hashes_to_the_known_constant(self, tmp_path):
        target = tmp_path / "empty"
        target.write_bytes(b"")
        assert sha256_file(target) == (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )


class TestRegisteredProfile:
    """Corrected 2026-08-28.

    The frozen suite invoked the registered profile without
    `--author-qjl-checkout`. Task 7 makes that argument required for
    registered runs ("Extend the registered qualification CLI with required
    `--author-qjl-checkout`"), so the original two tests asserted a CLI that
    would accept a registered run with no author differential -- a weaker
    contract than the plan specifies. The refusal is the correct behavior and
    is now asserted directly in
    test_registered_profile_requires_the_author_checkout.
    """

    REGISTERED_ARGV = [
        "--profile",
        "registered",
        "--output-root",
        "out",
        "--run-id",
        "r1",
        "--author-qjl-checkout",
        "/tmp/hamutay-turboquant-author/QJL",
    ]

    def test_registered_profile_freezes_all_scientific_counts(self):
        args = build_parser().parse_args(list(self.REGISTERED_ARGV))
        assert args.dimension == 128
        assert args.sample_count == 1_000_000
        assert args.bootstrap_resamples == 10_000
        assert tuple(args.bits) == (1, 2, 3, 4)

    def test_registered_profile_uses_a_divisible_batch_size(self):
        args = build_parser().parse_args(list(self.REGISTERED_ARGV))
        assert args.batch_size == 4000
        assert args.sample_count % args.batch_size == 0
        assert args.sample_count % 1000 == 0

    def test_registered_profile_requires_the_author_checkout(self):
        """A registered run with no differential oracle must be refused.

        This is the assertion the two corrected tests should have carried:
        certifying R1 without the author comparison is exactly the silent
        weakening the fifth gate exists to prevent.
        """
        with pytest.raises(SystemExit) as raised:
            build_parser().parse_args(
                ["--profile", "registered", "--output-root", "out", "--run-id", "r1"]
            )
        assert raised.value.code != 0

    def test_development_profile_does_not_require_the_author_checkout(self):
        args = build_parser().parse_args(
            ["--profile", "development", "--output-root", "dev", "--run-id", "smoke"]
        )
        assert args.author_qjl_checkout is None

    @pytest.mark.parametrize(
        "override",
        [
            ["--sample-count", "10"],
            ["--dimension", "64"],
            ["--bootstrap-resamples", "10"],
            ["--bootstrap-blocks", "10"],
            ["--batch-size", "7"],
        ],
    )
    def test_registered_profile_rejects_scientific_count_overrides(self, override):
        """Any of these would silently produce a weaker registered result.

        Corrected 2026-08-28: the frozen version omitted
        `--author-qjl-checkout`, so the parser rejected the command for the
        missing checkout and this test passed without ever exercising the
        override guard. It now supplies a valid checkout so the only remaining
        reason to exit is the forbidden override.
        """
        parser = build_parser()
        with pytest.raises(SystemExit) as raised:
            parser.parse_args([*self.REGISTERED_ARGV, *override])
        assert raised.value.code != 0

    def test_development_profile_permits_explicit_counts(self):
        args = build_parser().parse_args(
            [
                "--profile",
                "development",
                "--output-root",
                "dev",
                "--run-id",
                "smoke",
                "--sample-count",
                "20000",
                "--batch-size",
                "1000",
                "--bootstrap-blocks",
                "100",
                "--bootstrap-resamples",
                "200",
            ]
        )
        assert args.sample_count == 20000
        assert args.batch_size == 1000

    def test_an_unknown_profile_is_rejected(self):
        with pytest.raises(SystemExit):
            build_parser().parse_args(
                ["--profile", "certified", "--output-root", "o", "--run-id", "r"]
            )

    def test_run_id_and_output_root_are_required(self):
        for argv in (
            ["--profile", "registered"],
            ["--profile", "registered", "--output-root", "out"],
            ["--profile", "registered", "--run-id", "r1"],
        ):
            with pytest.raises(SystemExit):
                build_parser().parse_args(argv)


class TestProcessLevelDeterminism:
    def test_registered_workers_are_three_fresh_processes(self, monkeypatch, tmp_path):
        """Determinism must be measured across separate interpreters, not
        three loops inside one already-initialized process."""
        calls: list[list[str]] = []

        def fake_run(command, *, check, env):
            assert check is True
            calls.append(command)
            output = Path(command[command.index("--output") + 1])
            output.write_text("{}\n", encoding="utf-8")

        monkeypatch.setattr(subprocess, "run", fake_run)
        outputs = run_registered_workers(
            tmp_path,
            tmp_path / "worker-config.json",
            tmp_path / "resolved_inputs.npz",
        )

        assert len(calls) == 3
        assert [
            command[command.index("--execution-index") + 1] for command in calls
        ] == ["0", "1", "2"]
        assert all(
            command[:3] == [sys.executable, "-m", "hamutay.turboquant.qualify_worker"]
            for command in calls
        )
        assert outputs == tuple(
            tmp_path / f"execution-{index}.json" for index in range(3)
        )

    def test_each_worker_receives_the_same_frozen_inputs(self, monkeypatch, tmp_path):
        """All three executions must read one frozen resolved_inputs.npz
        rather than regenerating arrays independently."""
        calls: list[list[str]] = []

        def fake_run(command, *, check, env):
            calls.append(command)
            Path(command[command.index("--output") + 1]).write_text(
                "{}\n", encoding="utf-8"
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        resolved = tmp_path / "resolved_inputs.npz"
        run_registered_workers(tmp_path, tmp_path / "worker-config.json", resolved)

        resolved_arguments = {
            command[command.index("--resolved-inputs") + 1]
            for command in calls
            if "--resolved-inputs" in command
        }
        assert len(resolved_arguments) <= 1
        assert len(calls) == 3

    def test_a_failing_worker_propagates_rather_than_being_swallowed(
        self, monkeypatch, tmp_path
    ):
        def fake_run(command, *, check, env):
            raise subprocess.CalledProcessError(1, command)

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(subprocess.CalledProcessError):
            run_registered_workers(
                tmp_path,
                tmp_path / "worker-config.json",
                tmp_path / "resolved_inputs.npz",
            )
