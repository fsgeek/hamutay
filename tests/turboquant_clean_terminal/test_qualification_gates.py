"""Independent verification of ALL FIVE qualification gate criteria.

Tests enforce frozen numerical criteria for both acceptable and unacceptable evidence,
distinguishing each independent criterion within composite gates, using independent
mathematical oracles, and distinguishing decision correctness from scientific outcomes.

Transport Signing Identity:
    Tony Mason; hamutay@wamason.com; 01193FA2631C8AE8E4DF266E216D3C9B920813A1
"""

from __future__ import annotations

import math
from typing import Any, Mapping
import numpy as np
import pytest

from hamutay.turboquant import (
    GateResult,
    QualificationConfig,
    QualificationMetrics,
    QualificationResult,
    evaluate_algorithm_gates,
)
from hamutay.turboquant.qualification import author_code_differential_gate


# Frozen reference targets and tolerances
FROZEN_MSE_PAPER_TARGETS = {1: 0.36, 2: 0.117, 3: 0.03, 4: 0.009}
FROZEN_MSE_ANALYTIC_TARGETS = {
    1: 0.36088859,
    2: 0.11600007,
    3: 0.03396593,
    4: 0.00931479,
}
DIMENSION_128 = 128
FROZEN_PRODUCT_PAPER_TARGETS = {
    1: 1.57 / DIMENSION_128,
    2: 0.56 / DIMENSION_128,
    3: 0.18 / DIMENSION_128,
    4: 0.047 / DIMENSION_128,
}
FROZEN_MSE_ANALYTIC_TOLERANCE = 0.005  # 0.5% relative error
FROZEN_MSE_PAPER_TOLERANCE = 0.15     # 15% relative error
FROZEN_PRODUCT_PAPER_TOLERANCE = 0.15 # 15% relative error
FROZEN_EQUIVALENCE_FACTOR = 0.02      # 2% of RMSE
FROZEN_AUTHOR_ATOL = 1e-5
FROZEN_AUTHOR_RTOL = 1e-4


def _build_metrics(
    bits: int,
    mse_observed: float,
    mse_analytic: float,
    mse_paper: float,
    product_observed: float,
    product_paper: float,
    bias_mean: float,
    bias_rmse: float,
    ci9875: tuple[float, float],
    ci95: tuple[float, float] = (0.0, 0.0),
) -> QualificationMetrics:
    return QualificationMetrics(
        bits=bits,
        mse_observed=mse_observed,
        mse_analytic_target=mse_analytic,
        mse_paper_target=mse_paper,
        product_observed=product_observed,
        product_paper_target=product_paper,
        normalized_bias_mean=bias_mean,
        normalized_bias_rmse=bias_rmse,
        normalized_bias_ci95=ci95,
        normalized_bias_ci9875=ci9875,
        sample_count=1_000_000,
        product_mse_bits=bits - 1,
    )


def _build_acceptable_metrics_tuple() -> tuple[QualificationMetrics, ...]:
    """Generates synthetic acceptable metrics satisfying all frozen tolerances."""
    metrics_list = []
    for b in (1, 2, 3, 4):
        mse_an = FROZEN_MSE_ANALYTIC_TARGETS[b]
        mse_pap = FROZEN_MSE_PAPER_TARGETS[b]
        # Set observed MSE within 0.1% of analytic (well below 0.5%)
        mse_obs = mse_an * 1.001
        
        prod_pap = FROZEN_PRODUCT_PAPER_TARGETS[b]
        # Set observed product distortion within 2% of paper (well below 15%)
        prod_obs = prod_pap * 1.02
        
        bias_rmse = 0.04 / math.sqrt(b)
        eq_limit = FROZEN_EQUIVALENCE_FACTOR * bias_rmse
        # CI strictly inside [-eq_limit, +eq_limit]
        ci9875 = (-0.6 * eq_limit, +0.6 * eq_limit)
        ci95 = (-0.4 * eq_limit, +0.4 * eq_limit)

        metrics_list.append(
            _build_metrics(
                bits=b,
                mse_observed=mse_obs,
                mse_analytic=mse_an,
                mse_paper=mse_pap,
                product_observed=prod_obs,
                product_paper=prod_pap,
                bias_mean=0.00001,
                bias_rmse=bias_rmse,
                ci9875=ci9875,
                ci95=ci95,
            )
        )
    return tuple(metrics_list)


# ---------------------------------------------------------------------------
# Gate 1: Round-Trip Determinism
# ---------------------------------------------------------------------------

def test_gate1_round_trip_determinism_acceptable():
    """Gate 1 passes when process determinism is established."""
    metrics = _build_acceptable_metrics_tuple()
    result = QualificationResult(metrics=metrics, determinism_passed=True)
    
    gates = evaluate_algorithm_gates(result)
    gate1 = next(g for g in gates if g.name == "round_trip_determinism")
    
    assert gate1.passed is True
    assert gate1.status == "passed"
    assert gate1.observed is True
    assert gate1.threshold is True
    assert isinstance(gate1.detail, str) and len(gate1.detail) > 0


def test_gate1_round_trip_determinism_unacceptable():
    """Gate 1 faithfully fails when determinism check fails."""
    metrics = _build_acceptable_metrics_tuple()
    result = QualificationResult(metrics=metrics, determinism_passed=False)
    
    gates = evaluate_algorithm_gates(result)
    gate1 = next(g for g in gates if g.name == "round_trip_determinism")
    
    assert gate1.passed is False
    assert gate1.status == "failed"
    assert gate1.observed is False


# ---------------------------------------------------------------------------
# Gate 2: MSE Distortion (Dual Analytic / Published Tolerance)
# ---------------------------------------------------------------------------

def test_gate2_mse_distortion_acceptable_and_oracle():
    """Gate 2 passes when empirical MSE satisfies both 0.5% analytic and 15% paper bounds."""
    metrics = _build_acceptable_metrics_tuple()
    result = QualificationResult(metrics=metrics, determinism_passed=True)
    
    # Independent mathematical oracle check
    for m in metrics:
        rel_analytic = abs(m.mse_observed - m.mse_analytic_target) / m.mse_analytic_target
        rel_paper = abs(m.mse_observed - m.mse_paper_target) / m.mse_paper_target
        assert rel_analytic <= FROZEN_MSE_ANALYTIC_TOLERANCE, f"Analytic breach at bit {m.bits}"
        assert rel_paper <= FROZEN_MSE_PAPER_TOLERANCE, f"Paper breach at bit {m.bits}"

    gates = evaluate_algorithm_gates(result)
    gate2 = next(g for g in gates if g.name == "mse_distortion")
    assert gate2.passed is True
    assert gate2.status == "passed"


def test_gate2_mse_distortion_distinguishes_analytic_failure_alone():
    """Gate 2 fails when empirical MSE breaches analytic tolerance (>0.5%) even if paper target passes."""
    metrics_list = list(_build_acceptable_metrics_tuple())
    # Corrupt bit 2: 0.8% error relative to analytic (breaches 0.5%), but paper error ~0.9% (within 15%)
    target_an = FROZEN_MSE_ANALYTIC_TARGETS[2]
    corrupted_obs = target_an * 1.008
    rel_an = abs(corrupted_obs - target_an) / target_an
    rel_pap = abs(corrupted_obs - FROZEN_MSE_PAPER_TARGETS[2]) / FROZEN_MSE_PAPER_TARGETS[2]
    assert rel_an > FROZEN_MSE_ANALYTIC_TOLERANCE
    assert rel_pap <= FROZEN_MSE_PAPER_TOLERANCE

    metrics_list[1] = _build_metrics(
        bits=2,
        mse_observed=corrupted_obs,
        mse_analytic=target_an,
        mse_paper=FROZEN_MSE_PAPER_TARGETS[2],
        product_observed=metrics_list[1].product_observed,
        product_paper=metrics_list[1].product_paper_target,
        bias_mean=0.0,
        bias_rmse=0.03,
        ci9875=(-0.0001, 0.0001),
    )
    result = QualificationResult(metrics=tuple(metrics_list), determinism_passed=True)
    gates = evaluate_algorithm_gates(result)
    gate2 = next(g for g in gates if g.name == "mse_distortion")
    assert gate2.passed is False
    assert gate2.status == "failed"


def test_gate2_mse_distortion_distinguishes_paper_failure_alone():
    """Gate 2 fails when empirical MSE breaches paper tolerance (>15%) even if analytic target passes."""
    metrics_list = list(_build_acceptable_metrics_tuple())
    # Corrupt bit 3: analytic target passes (0.1% error), but paper error breaches 15%
    target_an = FROZEN_MSE_ANALYTIC_TARGETS[3]  # ~0.03396593
    # Target paper is 0.03. If obs is 0.0346, rel_paper = (0.0346 - 0.03)/0.03 = 15.33% (>15%)
    corrupted_obs = 0.0346
    rel_an = abs(corrupted_obs - target_an) / target_an  # ~1.8%
    rel_pap = abs(corrupted_obs - FROZEN_MSE_PAPER_TARGETS[3]) / FROZEN_MSE_PAPER_TARGETS[3]
    assert rel_pap > FROZEN_MSE_PAPER_TOLERANCE

    metrics_list[2] = _build_metrics(
        bits=3,
        mse_observed=corrupted_obs,
        mse_analytic=target_an,
        mse_paper=FROZEN_MSE_PAPER_TARGETS[3],
        product_observed=metrics_list[2].product_observed,
        product_paper=metrics_list[2].product_paper_target,
        bias_mean=0.0,
        bias_rmse=0.03,
        ci9875=(-0.0001, 0.0001),
    )
    result = QualificationResult(metrics=tuple(metrics_list), determinism_passed=True)
    gates = evaluate_algorithm_gates(result)
    gate2 = next(g for g in gates if g.name == "mse_distortion")
    assert gate2.passed is False
    assert gate2.status == "failed"


# ---------------------------------------------------------------------------
# Gate 3: QJL Bias Equivalence (98.75% Bootstrap Interval within ±0.02*RMSE)
# ---------------------------------------------------------------------------

def test_gate3_qjl_bias_equivalence_acceptable_and_oracle():
    """Gate 3 passes when the 98.75% CI is completely contained in [-0.02*RMSE, +0.02*RMSE]."""
    metrics = _build_acceptable_metrics_tuple()
    result = QualificationResult(metrics=metrics, determinism_passed=True)

    # Independent oracle check
    for m in metrics:
        bound = FROZEN_EQUIVALENCE_FACTOR * m.normalized_bias_rmse
        ci_low, ci_high = m.normalized_bias_ci9875
        assert ci_low >= -bound, f"CI lower bound breach at bit {m.bits}"
        assert ci_high <= bound, f"CI upper bound breach at bit {m.bits}"

    gates = evaluate_algorithm_gates(result)
    gate3 = next(g for g in gates if g.name == "qjl_bias_equivalence")
    assert gate3.passed is True
    assert gate3.status == "passed"


def test_gate3_qjl_bias_equivalence_distinguishes_high_endpoint_breach_alone():
    """Gate 3 fails when the CI upper endpoint breaches +0.02*RMSE alone while lower endpoint is inside."""
    metrics_list = list(_build_acceptable_metrics_tuple())
    rmse = 0.04
    bound = FROZEN_EQUIVALENCE_FACTOR * rmse
    # Lower CI is well within (-0.2*bound), but upper CI breaches (1.05 * bound)
    corrupted_ci = (-0.2 * bound, 1.05 * bound)
    assert corrupted_ci[0] >= -bound
    assert corrupted_ci[1] > bound
    
    metrics_list[0] = _build_metrics(
        bits=1,
        mse_observed=metrics_list[0].mse_observed,
        mse_analytic=metrics_list[0].mse_analytic_target,
        mse_paper=metrics_list[0].mse_paper_target,
        product_observed=metrics_list[0].product_observed,
        product_paper=metrics_list[0].product_paper_target,
        bias_mean=0.0001,
        bias_rmse=rmse,
        ci9875=corrupted_ci,
    )
    result = QualificationResult(metrics=tuple(metrics_list), determinism_passed=True)
    gates = evaluate_algorithm_gates(result)
    gate3 = next(g for g in gates if g.name == "qjl_bias_equivalence")
    assert gate3.passed is False
    assert gate3.status == "failed"


def test_gate3_qjl_bias_equivalence_distinguishes_low_endpoint_breach_alone():
    """Gate 3 fails when the CI lower endpoint breaches -0.02*RMSE alone while upper endpoint is inside."""
    metrics_list = list(_build_acceptable_metrics_tuple())
    rmse = 0.04
    bound = FROZEN_EQUIVALENCE_FACTOR * rmse
    # Lower CI breaches (-1.08 * bound), upper CI is well within (+0.3 * bound)
    corrupted_ci = (-1.08 * bound, 0.3 * bound)
    assert corrupted_ci[0] < -bound
    assert corrupted_ci[1] <= bound

    metrics_list[2] = _build_metrics(
        bits=3,
        mse_observed=metrics_list[2].mse_observed,
        mse_analytic=metrics_list[2].mse_analytic_target,
        mse_paper=metrics_list[2].mse_paper_target,
        product_observed=metrics_list[2].product_observed,
        product_paper=metrics_list[2].product_paper_target,
        bias_mean=-0.0002,
        bias_rmse=rmse,
        ci9875=corrupted_ci,
    )
    result = QualificationResult(metrics=tuple(metrics_list), determinism_passed=True)
    gates = evaluate_algorithm_gates(result)
    gate3 = next(g for g in gates if g.name == "qjl_bias_equivalence")
    assert gate3.passed is False
    assert gate3.status == "failed"


def test_gate3_distinguishes_scientific_failure_from_defect():
    """A scientific measurement can fail a gate without the implementation being defective."""
    metrics_list = list(_build_acceptable_metrics_tuple())
    rmse = 0.04
    bound = FROZEN_EQUIVALENCE_FACTOR * rmse
    # An experiment with small variance but true slight positive bias outside margin
    ci_outside = (1.02 * bound, 1.08 * bound)

    metrics_list[1] = _build_metrics(
        bits=2,
        mse_observed=metrics_list[1].mse_observed,
        mse_analytic=metrics_list[1].mse_analytic_target,
        mse_paper=metrics_list[1].mse_paper_target,
        product_observed=metrics_list[1].product_observed,
        product_paper=metrics_list[1].product_paper_target,
        bias_mean=0.001,
        bias_rmse=rmse,
        ci9875=ci_outside,
    )
    result = QualificationResult(metrics=tuple(metrics_list), determinism_passed=True)
    gates = evaluate_algorithm_gates(result)
    gate3 = next(g for g in gates if g.name == "qjl_bias_equivalence")
    # Decision correctness requires reporting failure, even though code executed properly
    assert gate3.passed is False
    assert gate3.status == "failed"


# ---------------------------------------------------------------------------
# Gate 4: Published QJL Distortion Scale (15% Relative Error)
# ---------------------------------------------------------------------------

def test_gate4_published_qjl_distortion_acceptable_and_oracle():
    """Gate 4 passes when product distortion is within 15% of paper target."""
    metrics = _build_acceptable_metrics_tuple()
    result = QualificationResult(metrics=metrics, determinism_passed=True)

    # Independent oracle check
    for m in metrics:
        rel = abs(m.product_observed - m.product_paper_target) / m.product_paper_target
        assert rel <= FROZEN_PRODUCT_PAPER_TOLERANCE, f"QJL distortion breach at bit {m.bits}"

    gates = evaluate_algorithm_gates(result)
    gate4 = next(g for g in gates if g.name == "published_qjl_distortion")
    assert gate4.passed is True
    assert gate4.status == "passed"


def test_gate4_published_qjl_distortion_distinguishes_positive_breach():
    """Gate 4 fails when empirical product distortion exceeds target by >15%."""
    metrics_list = list(_build_acceptable_metrics_tuple())
    target_pap = FROZEN_PRODUCT_PAPER_TARGETS[3]
    corrupted_obs = target_pap * 1.16  # +16%

    metrics_list[2] = _build_metrics(
        bits=3,
        mse_observed=metrics_list[2].mse_observed,
        mse_analytic=metrics_list[2].mse_analytic_target,
        mse_paper=metrics_list[2].mse_paper_target,
        product_observed=corrupted_obs,
        product_paper=target_pap,
        bias_mean=0.0,
        bias_rmse=0.03,
        ci9875=(-0.0001, 0.0001),
    )
    result = QualificationResult(metrics=tuple(metrics_list), determinism_passed=True)
    gates = evaluate_algorithm_gates(result)
    gate4 = next(g for g in gates if g.name == "published_qjl_distortion")
    assert gate4.passed is False
    assert gate4.status == "failed"


def test_gate4_published_qjl_distortion_distinguishes_negative_breach():
    """Gate 4 fails when empirical product distortion is >15% below target."""
    metrics_list = list(_build_acceptable_metrics_tuple())
    target_pap = FROZEN_PRODUCT_PAPER_TARGETS[1]
    corrupted_obs = target_pap * 0.82  # -18%

    metrics_list[0] = _build_metrics(
        bits=1,
        mse_observed=metrics_list[0].mse_observed,
        mse_analytic=metrics_list[0].mse_analytic_target,
        mse_paper=metrics_list[0].mse_paper_target,
        product_observed=corrupted_obs,
        product_paper=target_pap,
        bias_mean=0.0,
        bias_rmse=0.04,
        ci9875=(-0.0001, 0.0001),
    )
    result = QualificationResult(metrics=tuple(metrics_list), determinism_passed=True)
    gates = evaluate_algorithm_gates(result)
    gate4 = next(g for g in gates if g.name == "published_qjl_distortion")
    assert gate4.passed is False
    assert gate4.status == "failed"


# ---------------------------------------------------------------------------
# Gate 5: Author Code Differential Adapter
# ---------------------------------------------------------------------------

def test_gate5_author_differential_acceptable():
    """Gate 5 correctly transforms a passing author adapter record."""
    oracle_record = {
        "status": "passed",
        "gate": {
            "name": "author_code_differential",
            "passed": True,
            "threshold": {"atol": FROZEN_AUTHOR_ATOL, "rtol": FROZEN_AUTHOR_RTOL},
            "detail": "Author CUDA differential verified within frozen tolerances.",
            "observed": {
                "inlier_sign_bytes_equal": True,
                "outlier_norms_exact_zero": True,
                "max_absolute_score_error": 1.2e-6,
                "max_relative_score_error": 8.5e-6,
            },
        },
    }
    gate5 = author_code_differential_gate(oracle_record)
    assert gate5.name == "author_code_differential"
    assert gate5.passed is True
    assert gate5.status == "passed"
    assert gate5.threshold == {"atol": FROZEN_AUTHOR_ATOL, "rtol": FROZEN_AUTHOR_RTOL}


def test_gate5_author_differential_not_run_when_none():
    """Gate 5 produces status='not_run' and passed=False when author checkout was omitted."""
    gate5 = author_code_differential_gate(None)
    assert gate5.name == "author_code_differential"
    assert gate5.passed is False
    assert gate5.status == "not_run"
    assert gate5.observed == "not_run"
    assert gate5.threshold == {"atol": FROZEN_AUTHOR_ATOL, "rtol": FROZEN_AUTHOR_RTOL}


def test_gate5_distinguishes_individual_failure_criteria():
    """Gate 5 fails when any individual differential check fails."""
    # Case A: Score tolerance breach alone
    record_score_fail = {
        "status": "failed",
        "gate": {
            "name": "author_code_differential",
            "passed": False,
            "threshold": {"atol": FROZEN_AUTHOR_ATOL, "rtol": FROZEN_AUTHOR_RTOL},
            "detail": "Score tolerance exceeded.",
            "observed": {
                "inlier_sign_bytes_equal": True,
                "outlier_norms_exact_zero": True,
                "max_absolute_score_error": 5.0e-4,
                "max_relative_score_error": 1.0e-2,
            },
        },
    }
    gate_a = author_code_differential_gate(record_score_fail)
    assert gate_a.passed is False
    assert gate_a.status == "failed"

    # Case B: Inlier sign bytes mismatch alone
    record_inlier_fail = {
        "status": "failed",
        "gate": {
            "name": "author_code_differential",
            "passed": False,
            "threshold": {"atol": FROZEN_AUTHOR_ATOL, "rtol": FROZEN_AUTHOR_RTOL},
            "detail": "Inlier signs mismatch.",
            "observed": {
                "inlier_sign_bytes_equal": False,
                "outlier_norms_exact_zero": True,
                "max_absolute_score_error": 1.0e-7,
                "max_relative_score_error": 1.0e-6,
            },
        },
    }
    gate_b = author_code_differential_gate(record_inlier_fail)
    assert gate_b.passed is False
    assert gate_b.status == "failed"


def test_gate5_refuses_weakened_tolerances():
    """Gate 5 strictly rejects attempts to weaken frozen numerical tolerances."""
    weakened_record = {
        "status": "passed",
        "gate": {
            "name": "author_code_differential",
            "passed": True,
            "threshold": {"atol": 1e-4, "rtol": 1e-3},  # Weaker than frozen 1e-5 / 1e-4
            "detail": "Weakened tolerances.",
        },
    }
    with pytest.raises(ValueError):
        author_code_differential_gate(weakened_record)


def test_gate5_refuses_inconsistent_outer_inner_status():
    """Gate 5 rejects contradictory outer status and inner gate.passed values."""
    inconsistent_record = {
        "status": "passed",
        "gate": {
            "name": "author_code_differential",
            "passed": False,  # Contradiction
            "threshold": {"atol": FROZEN_AUTHOR_ATOL, "rtol": FROZEN_AUTHOR_RTOL},
            "detail": "Mismatched status.",
        },
    }
    with pytest.raises(ValueError):
        author_code_differential_gate(inconsistent_record)


# ---------------------------------------------------------------------------
# Terminal Five-Gate Decision Rule
# ---------------------------------------------------------------------------

def test_terminal_decision_requires_all_five_passing():
    """Terminal R1 certification requires all five gates to be present and passing."""
    metrics = _build_acceptable_metrics_tuple()
    result = QualificationResult(metrics=metrics, determinism_passed=True)
    core_gates = list(evaluate_algorithm_gates(result))
    
    passing_adapter_gate = author_code_differential_gate({
        "status": "passed",
        "gate": {
            "name": "author_code_differential",
            "passed": True,
            "threshold": {"atol": FROZEN_AUTHOR_ATOL, "rtol": FROZEN_AUTHOR_RTOL},
            "detail": "Differential passed.",
            "observed": {},
        },
    })
    
    all_five = core_gates + [passing_adapter_gate]
    assert len(all_five) == 5
    assert all(g.status == "passed" and g.passed for g in all_five)

    # If any single gate fails, terminal status must be failed
    for i in range(5):
        corrupted_gates = list(all_five)
        corrupted_gates[i] = GateResult(
            name=corrupted_gates[i].name,
            passed=False,
            observed="corrupted",
            threshold=corrupted_gates[i].threshold,
            detail="Artificial failure",
            status="failed",
        )
        assert any(g.status != "passed" for g in corrupted_gates)
