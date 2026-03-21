"""Tensor evaluation framework.

Instruments for understanding what tensors are, how they behave,
and how they change under different conditions. Not optimization —
measurement. The goal is to see clearly before we try to improve.

Three kinds of instruments:
  - Divergence: How do tensors differ from each other?
  - Trajectory: How does a tensor sequence evolve over time?
  - Profile: What is this tensor's internal structure?
"""

from hamutay.eval.divergence import (
    DivergenceProfile,
    strand_alignment,
    content_similarity,
    capacity_allocation,
    loss_distribution,
    component_divergence,
)
from hamutay.eval.trajectory import (
    TrajectoryStats,
    ProcessHealth,
    trajectory_stats,
    process_health,
    compare_trajectories,
)

__all__ = [
    "DivergenceProfile",
    "strand_alignment",
    "content_similarity",
    "capacity_allocation",
    "loss_distribution",
    "component_divergence",
    "TrajectoryStats",
    "ProcessHealth",
    "trajectory_stats",
    "process_health",
    "compare_trajectories",
]
