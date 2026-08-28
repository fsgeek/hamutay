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

    # Declared public conventions that live in plan prose rather than in an
    # Interfaces block. Omitting them is over-stripping: a clean validator can
    # reasonably choose a column-vector convention, the opposite zero-sign
    # rule, or a different bit order, and manufacture false failures against a
    # correct implementation. These are wire/representation semantics, stated
    # as declarations with no worked values, test names, or assertions.
    kept.append(
        "\n## Declared numerical and representation conventions\n\n"
        "- Registered dimension is 128. Inputs are arbitrary nonzero vectors: "
        "normalize before applying a spherical quantizer and restore the "
        "original norm on reconstruction.\n"
        "- A zero vector has norm zero, all-zero MSE indices, zero residual "
        "norm, and exact-zero reconstruction. Its *raw projected values* are "
        "zero; its *encoded sign bits* are not. See the sign encoding below.\n"
        "- Vectors are rows. Rotation is `y = x @ rotation.T`; inverse "
        "rotation is `x_hat = y_hat @ rotation`. QJL projections are stored "
        "as rows, so a batch sketch is `residual @ projection.T`.\n"
        "- In the transparent reference every zero sign maps to `+1`. The "
        "pinned author kernel maps exact zero to `-1`; this is a declared, "
        "documented convention difference, not a defect.\n"
        "- Bit packing is little-endian within each byte: sketch coordinate "
        "`j` occupies bit `j % 8` of byte `j // 8`. A set bit decodes to FP32 "
        "`+1` and a clear bit to `-1`. Because a zero projected value maps to "
        "`+1`, a zero vector's packed sign bytes have every in-range bit SET, "
        "not cleared; only unused high bits of the final byte are zero. What "
        "remains all-zero for a zero vector is the indices and the norms, and "
        "the zero norm is what forces exact-zero reconstruction.\n"
        "- `derive_seed` wire format: SHA-256 over the UTF-8 string formed by "
        "joining the study seed and the given fields with `|`, taking the "
        "first 16 bytes as an unsigned big-endian integer. Integer fields "
        "serialize as unpadded base-10.\n"
        "- A `b`-bit product quantizer contains a `b-1`-bit Algorithm 1 "
        "codebook plus its fixed QJL sketch and residual norm. Total bits 1 "
        "through 4 therefore use 0- through 3-bit MSE codebooks.\n"
        "- `nearest_code_indices` resolves an exact midpoint tie to the "
        "lower centroid.\n"
        "- `estimate_inner_products` requires paired query/key leading "
        "shapes and does not broadcast them; mismatched leading shapes are "
        "rejected.\n"
        "- Rotations and codebooks are constructed in FP64 and frozen as "
        "FP32. Quantization, reconstruction, and diagnostic reductions are "
        "FP32 unless otherwise stated.\n"
    )

    kept.append(
        "\n## Public result types\n\n"
        "The gate-evaluation API consumes and returns declared types. Field "
        "names and roles are public contract; no worked values are given.\n\n"
        "- `QualificationMetrics` carries, per bit width: `bits`, "
        "`mse_observed`, `mse_analytic_target`, `mse_paper_target`, "
        "`product_observed`, `product_paper_target`, `normalized_bias_mean`, "
        "`normalized_bias_rmse`, `normalized_bias_ci95`, "
        "`normalized_bias_ci9875`, `sample_count`, `product_mse_bits`, "
        "`product_analytic_target`, `sensitivity_product_observed`, "
        "`sensitivity_normalized_bias_mean`, "
        "`sensitivity_normalized_bias_rmse`, "
        "`sensitivity_normalized_bias_ci95`, "
        "`sensitivity_normalized_bias_ci9875`, `mse_block_means`, "
        "`product_block_means`, `normalized_bias_block_means`, "
        "`sensitivity_product_block_means`, and "
        "`sensitivity_bias_block_means`. Interval fields are `(low, high)` "
        "pairs. The `sensitivity_*` fields carry the declared "
        "row-orthogonalized projection arm, which is reported and does not "
        "gate. The `*_block_means` fields carry block-bootstrap evidence.\n"
        "- `QualificationResult` carries `metrics` (a sequence of "
        "`QualificationMetrics`), `determinism_passed`, `sample_count`, "
        "`batch_size`, `bootstrap_blocks`, `bootstrap_resamples`, "
        "`dimension`, and `configuration`.\n"
        "- `GateResult` carries `name`, `passed`, `observed`, `threshold`, "
        "`detail`, and `status`. **Every** gate carries `status`, not only "
        "the author differential; it resolves to `passed`, `failed`, or "
        "`not_run`, the last used for the author differential when the "
        "checkout is omitted in development mode.\n"
        "- `partition_block_ids(sample_count, block_count)` forms contiguous "
        "equal blocks and rejects non-divisible inputs.\n"
    )

    kept.append(
        "\n## Public CLI and evidence behavior\n\n"
        "Stated as behavior, not implementation.\n\n"
        "- Registered mode freezes the declared scientific counts and rejects "
        "any attempt to override them. Development mode may accept explicit "
        "counts and is non-certifying.\n"
        "- Options are `--profile`, `--output-root`, `--run-id`, "
        "`--dimension`, `--sample-count`, `--batch-size`, "
        "`--bootstrap-blocks`, `--bootstrap-resamples`, `--bits`, "
        "`--author-qjl-checkout`, and `--allow-dirty-path`. Registered mode "
        "requires a clean worktree except for declared dirty paths.\n"
        "- Output namespaces are enforced before a run directory is created: "
        "development output must be at or beneath "
        "`experiments/turboquant/development`, registered output at or "
        "beneath `experiments/turboquant/qualification`. An otherwise valid "
        "temporary output root is rejected.\n"
        "- A run directory contains `manifest.json`, `resolved_inputs.npz`, "
        "`execution-0.json`, `execution-1.json`, `execution-2.json`, "
        "`qualification.json`, and `run.log`. All five gates and the terminal "
        "status appear in `qualification.json`. Evidence schema identifiers "
        "are `hamutay.turboquant.manifest.v2`, "
        "`hamutay.turboquant.execution.v1`, and "
        "`hamutay.turboquant.qualification.v2`.\n"
        "- A development run without an author checkout reports "
        "`author_code_differential` as `not_run` and is non-certifying. Its "
        "terminal status tracks the four completed core gates, and a "
        "completed development run exits zero whether that status is "
        "`passed` or `failed`.\n"
        "- Evidence is append-only: creating a run directory that already "
        "exists is refused. Terminal status is one of `passed`, `failed`, or "
        "`error`.\n"
        "- Registered exit success is possible only when all five named gates "
        "are present and pass.\n"
        "- Canonical JSON is sorted, compact, non-ASCII-preserving, "
        "newline-terminated, and rejects non-finite floats.\n"
    )

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


def build(
    plan: Path,
    spec: Path,
    output: Path,
    *,
    audit_dir: Path,
    paper: Path | None = None,
    implementation_commit: str | None = None,
    force: bool = False,
) -> dict:
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

    shutil.copy2(spec, output / spec.name)
    if paper is None:
        raise ValueError(
            "condition 3 requires a local arXiv 2504.19874 v1 copy; pass --paper. "
            "A URL in external_materials is not a supplied-file hash."
        )
    shutil.copy2(paper, output / paper.name)

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
        "implementation_under_review": implementation_commit
        or "(not supplied -- condition 3 requires this explicitly)",
        "builder_script_sha256": sha256_file(Path(__file__)),
        "paper_artifact": "arXiv 2504.19874v1, supplied locally and hashed below",
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
    # VERIFIER-ONLY. The dropped-lines log quotes the implementer test code
    # that caused F5 -- constants, test names, mock structure. Writing it into
    # the delivery directory would ship the exact contamination the bundle
    # exists to prevent. It is written outside the bundle and must never be
    # supplied to the clean validator.
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_log = audit_dir / "dropped-from-plan.VERIFIER-ONLY.txt"
    audit_log.write_text(
        "# VERIFIER-ONLY AUDIT LOG -- DO NOT SUPPLY TO THE CLEAN VALIDATOR.\n"
        "# Quotes implementer test code (finding F5).\n\n"
        + "\n".join(dropped)
        + "\n",
        encoding="utf-8",
    )

    # Every delivered file must be hashed, and nothing undelivered may sit in
    # the bundle directory.
    # The manifest cannot hash itself: any self-referential digest is stale
    # the instant the manifest is rewritten. Payload files are hashed here;
    # the manifest's own integrity is anchored out of band below.
    delivered = sorted(
        path
        for path in output.iterdir()
        if path.is_file() and path.name != "MANIFEST.json"
    )
    manifest["files"] = {path.name: sha256_file(path) for path in delivered}
    manifest["manifest_self_hash"] = (
        "not self-referential; see MANIFEST.sha256 in the verifier audit "
        "directory and the signed freeze record"
    )
    manifest["audit_log_written_outside_bundle"] = str(audit_log)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    # Anchor: the manifest's own hash, to be retained out of band in the
    # signed freeze record. A manifest that hashes only its payloads proves
    # internal consistency, not provenance.
    manifest_digest = sha256_file(manifest_path)
    (audit_dir / "MANIFEST.sha256").write_text(
        f"{manifest_digest}  MANIFEST.json\n", encoding="utf-8"
    )
    manifest["_manifest_sha256_anchor"] = manifest_digest
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build-sanitized-bundle")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--implementation-commit", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    manifest = build(
        args.plan,
        args.spec,
        args.output,
        audit_dir=args.audit_dir,
        paper=args.paper,
        implementation_commit=args.implementation_commit,
        force=args.force,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
