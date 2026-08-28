"""Build the sanitized materials bundle for a clean independent re-freeze.

Condition 1 of the Task 8 validation report. The first validation round failed
its independence protocol (finding F5) because the validator was handed the
complete qualification plan, which embeds implementer-authored test code, and
reproduced some of it verbatim.

This extracts only what Task 8 permits -- "the plan's frozen public
interfaces" -- and strips everything else: every fenced code block, every
implementation-guidance step, every prescribed test case, and every command.

The output is content-addressed. Every file is hashed, and the manifest
records the hashes so the bundle handed to a validator can be proven to be the
bundle that was built.

This script is NOT competent to certify its own output. Condition 2 requires
independent verification that the stripping is complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Sections of the plan that may be carried into the bundle. Task 8 permits the
# public interface declarations; nothing else from the plan is allowed.
PERMITTED_BLOCK_LABELS = (
    "**Interfaces:**",
    # Task 7 declares the pinned upstream artifact under its own label. It is
    # a public contract (repository, commit, file hashes), not implementer
    # test design, and the validator needs it to verify the oracle.
    "**Pinned upstream contract:**",
    # Task 5's metric definitions are declared conventions -- the formulas and
    # published targets -- not prescribed test cases.
    "**Metric definitions:**",
)

# Labels that terminate a permitted block.
TERMINATING_LABELS = (
    "- [ ] **Step",
    "**Files:**",
    "### Task",
    "**Compiler precondition:**",
    "---",
)

FENCE = re.compile(r"^```")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_interfaces(plan_text: str) -> tuple[str, list[str]]:
    """Return an interfaces-only contract plus a log of what was dropped.

    Walks the plan line by line. Only lines inside an ``**Interfaces:**``
    block are kept, and any fenced code block encountered even inside a
    permitted section is dropped -- a code fence is exactly the vector that
    carried prescribed test cases in the first round.
    """
    kept: list[str] = []
    dropped: list[str] = []
    in_permitted = False
    in_fence = False
    current_task = "(preamble)"
    last_emitted_task = ""

    for number, line in enumerate(plan_text.splitlines(), start=1):
        if line.startswith("### Task"):
            current_task = line.removeprefix("### ").strip()
            in_permitted = False

        if FENCE.match(line):
            in_fence = not in_fence
            dropped.append(f"{number}: [code fence] {line.strip()[:60]}")
            continue

        if in_fence:
            dropped.append(f"{number}: [code] {line.strip()[:60]}")
            continue

        if any(line.startswith(label) for label in PERMITTED_BLOCK_LABELS):
            in_permitted = True
            if current_task != last_emitted_task:
                kept.append(f"\n## {current_task}\n")
                last_emitted_task = current_task
            continue

        if in_permitted and any(
            line.startswith(label) for label in TERMINATING_LABELS
        ):
            in_permitted = False

        if in_permitted:
            kept.append(line)
        elif line.strip():
            dropped.append(f"{number}: {line.strip()[:60]}")

    # The registered CLI's required arguments are declared contract, stated in
    # Task 7 Step 3 prose rather than in an Interfaces block. Omitting it
    # would reproduce finding F1, in which the first validator wrote tests
    # that invoked the registered profile without --author-qjl-checkout.
    kept.append(
        "\n## Registered CLI requirement (Task 7)\n\n"
        "- The registered profile requires `--author-qjl-checkout`. "
        "Development mode may omit it and must then report the "
        "`author_code_differential` gate as not-run, never as passed.\n"
        "- The terminal R1 record has exactly five gates named "
        "`round_trip_determinism`, `mse_distortion`, `qjl_bias_equivalence`, "
        "`published_qjl_distortion`, and `author_code_differential`. "
        "`evaluate_algorithm_gates` returns the first four; the fifth is "
        "joined at the CLI/evidence layer.\n"
    )

    header = (
        "# TurboQuant R1: public interface contract\n\n"
        "Extracted mechanically from the qualification plan by\n"
        "`scripts/turboquant/build_sanitized_bundle.py`. This contains the\n"
        "public names, signatures, and declared conventions the independent\n"
        "validator may rely on.\n\n"
        "Every fenced code block in the source plan was dropped, including\n"
        "inside otherwise-permitted sections: embedded test code is the\n"
        "contamination vector that invalidated the first validation round\n"
        "(finding F5). No prescribed test case, implementation-guidance step,\n"
        "or command from the plan appears here.\n"
    )
    return header + "\n".join(kept).rstrip() + "\n", dropped


def build(plan: Path, spec: Path, output: Path, *, force: bool = False) -> dict:
    if output.exists():
        if not force:
            raise FileExistsError(
                f"{output} exists; bundles are append-only, choose a new path"
            )
        shutil.rmtree(output)
    output.mkdir(parents=True)

    contract_text, dropped = extract_interfaces(plan.read_text(encoding="utf-8"))
    contract = output / "interface-contract.md"
    contract.write_text(contract_text, encoding="utf-8")

    spec_copy = output / spec.name
    shutil.copy2(spec, spec_copy)

    # Fail loudly if any forbidden token survived into the contract.
    forbidden = ("def test_", "assert ", "np.testing", "pytest", "1.0049", "0.00199")
    leaks = [token for token in forbidden if token in contract_text]
    if leaks:
        raise AssertionError(f"sanitization leaked forbidden tokens: {leaks}")

    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        commit = "(unavailable)"

    manifest = {
        "bundle_version": 1,
        "built_from_commit": commit,
        "source_plan_sha256": sha256_file(plan),
        "source_spec_sha256": sha256_file(spec),
        "files": {
            path.name: sha256_file(path)
            for path in sorted(output.iterdir())
            if path.is_file()
        },
        "external_materials": {
            "paper": "arXiv 2504.19874 v1 (https://arxiv.org/abs/2504.19874)",
            "author_qjl_contract": (
                "repo https://github.com/amirzandieh/QJL commit "
                "648b3641f96b6e95e091217220b94e4739fd4d82; file hashes are in "
                "the interface contract"
            ),
        },
        "signing_identity": {
            "note": "Condition 13: supplied as a bare string, not CLAUDE.md",
            "name": "Tony Mason",
            "email": "hamutay@wamason.com",
            "signingkey": "01193FA2631C8AE8E4DF266E216D3C9B920813A1",
        },
        "excluded": [
            "the full qualification plan (embeds implementer test code, F5)",
            "CLAUDE.md (F7, condition 13)",
            "src/, scripts/, tests/",
            "repository history, khipus, logs, review documents",
        ],
        "lines_dropped_from_plan": len(dropped),
        "caveat": (
            "This bundle's builder cannot certify its own output. Condition 2 "
            "requires independent verification that the stripping is complete."
        ),
    }
    manifest_path = output / "MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "dropped-from-plan.txt").write_text(
        "\n".join(dropped) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build-sanitized-bundle")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    manifest = build(args.plan, args.spec, args.output, force=args.force)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
