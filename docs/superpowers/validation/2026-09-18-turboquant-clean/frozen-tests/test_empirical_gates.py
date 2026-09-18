import pytest
from hamutay.turboquant.qualification import (
    QualificationConfig, 
    run_synthetic_qualification, 
    evaluate_algorithm_gates
)

@pytest.mark.slow
def test_scientific_gates_pass():
    config = QualificationConfig(
        dimension=128, 
        sample_count=1_000_000, 
        batch_size=4000, 
        bootstrap_blocks=1000, 
        bootstrap_resamples=10_000, 
        bits=(1, 2, 3, 4)
    )
    result = run_synthetic_qualification(config)
    
    gates = evaluate_algorithm_gates(result)
    
    assert len(gates) == 4
    
    gate_names = [g.name for g in gates]
    expected_gates = [
        "round_trip_determinism",
        "mse_distortion",
        "qjl_bias_equivalence",
        "published_qjl_distortion"
    ]
    for eg in expected_gates:
        assert eg in gate_names
    
    for gate in gates:
        assert gate.passed is True, f"Gate {gate.name} failed. Detail: {gate.detail}"
        assert gate.status == "passed"
