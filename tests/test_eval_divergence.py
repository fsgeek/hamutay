"""Tests for the tensor evaluation framework."""

from hamutay.tensor import (
    Tensor,
    Strand,
    KeyClaim,
    DeclaredLoss,
    EpistemicState,
    LossCategory,
)
from hamutay.eval.divergence import (
    strand_alignment,
    content_similarity,
    capacity_allocation,
    loss_distribution,
    loss_distribution_distance,
    component_divergence,
    divergence_profile,
)
from hamutay.eval.trajectory import trajectory_stats, compare_trajectories


def _make_tensor(
    cycle: int = 1,
    strand_titles: list[str] | None = None,
    strand_contents: list[str] | None = None,
    n_losses: int = 0,
    loss_categories: list[LossCategory] | None = None,
    ifn: str = "",
    questions: list[str] | None = None,
    truth: float = 0.8,
) -> Tensor:
    """Helper to build test tensors."""
    titles = strand_titles or ["Strand A"]
    contents = strand_contents or ["Some content about topic A."]
    if len(contents) < len(titles):
        contents.extend(["Default content."] * (len(titles) - len(contents)))

    strands = tuple(
        Strand(
            title=t,
            content=c,
            key_claims=(KeyClaim(text=f"Claim for {t}", epistemic=EpistemicState(truth=0.9)),),
        )
        for t, c in zip(titles, contents)
    )

    cats = loss_categories or [LossCategory.PRACTICAL_CONSTRAINT] * n_losses
    losses = tuple(
        DeclaredLoss(what_was_lost=f"Lost item {i}", why="reasons", category=cats[i])
        for i in range(n_losses)
    )

    return Tensor(
        cycle=cycle,
        strands=strands,
        declared_losses=losses,
        open_questions=tuple(questions or []),
        instructions_for_next=ifn,
        epistemic=EpistemicState(truth=truth, indeterminacy=0.1, falsity=0.1),
    )


class TestStrandAlignment:
    def test_identical_tensors(self):
        t = _make_tensor(strand_titles=["Alpha", "Beta"])
        result = strand_alignment(t, t)
        assert result.alignment_ratio == 1.0
        assert result.mean_title_similarity == 1.0
        assert len(result.unmatched_a) == 0
        assert len(result.unmatched_b) == 0

    def test_completely_different_strands(self):
        a = _make_tensor(strand_titles=["Quantum mechanics fundamentals"])
        b = _make_tensor(strand_titles=["Medieval cooking techniques"])
        result = strand_alignment(a, b)
        # These should not match — completely different topics
        assert result.alignment_ratio < 1.0

    def test_empty_tensors(self):
        a = Tensor(cycle=1)
        b = Tensor(cycle=2)
        result = strand_alignment(a, b)
        assert result.alignment_ratio == 1.0  # both empty = aligned

    def test_partial_overlap(self):
        a = _make_tensor(strand_titles=["Alpha strand", "Beta strand", "Gamma strand"])
        b = _make_tensor(strand_titles=["Alpha strand", "Delta strand"])
        result = strand_alignment(a, b)
        # "Alpha strand" should match, others shouldn't
        assert len(result.matches) >= 1
        assert any(m.title_a == "Alpha strand" for m in result.matches)


class TestContentSimilarity:
    def test_identical_content(self):
        t = _make_tensor(strand_contents=["The quick brown fox jumps over the lazy dog."])
        assert content_similarity(t, t) > 0.99

    def test_different_content(self):
        a = _make_tensor(strand_contents=["Machine learning uses gradient descent for optimization."])
        b = _make_tensor(strand_contents=["The ancient Romans built aqueducts for water transport."])
        sim = content_similarity(a, b)
        # BoW cosine shares function words — threshold is generous
        assert sim < 0.8  # different topics, but BoW sees shared words


class TestCapacityAllocation:
    def test_content_heavy_tensor(self):
        t = _make_tensor(
            strand_contents=["A very long strand content. " * 50],
            ifn="short",
        )
        cap = capacity_allocation(t)
        assert cap.content_frac > cap.meta_frac

    def test_meta_heavy_tensor(self):
        t = _make_tensor(
            strand_contents=["Brief."],
            n_losses=5,
            ifn="Very detailed instructions for next cycle. " * 20,
            questions=["Question " + str(i) for i in range(10)],
        )
        cap = capacity_allocation(t)
        assert cap.meta_frac > 0.3  # significant meta allocation

    def test_fractions_sum_to_one(self):
        t = _make_tensor(n_losses=3, ifn="some instructions", questions=["q1", "q2"])
        cap = capacity_allocation(t)
        total = cap.strand_frac + cap.loss_frac + cap.ifn_frac + cap.question_frac + cap.claim_frac
        assert abs(total - 1.0) < 0.01


class TestLossDistribution:
    def test_empty_losses(self):
        t = _make_tensor(n_losses=0)
        ld = loss_distribution(t)
        assert ld.is_empty
        assert ld.total_losses == 0

    def test_single_category(self):
        t = _make_tensor(n_losses=3, loss_categories=[LossCategory.CONTEXT_PRESSURE] * 3)
        ld = loss_distribution(t)
        assert ld.total_losses == 3
        assert ld.dominant_category == "context_pressure"
        assert ld.fractions["context_pressure"] == 1.0

    def test_distance_identical(self):
        t = _make_tensor(n_losses=2)
        ld = loss_distribution(t)
        assert loss_distribution_distance(ld, ld) == 0.0

    def test_distance_different(self):
        a = _make_tensor(n_losses=3, loss_categories=[LossCategory.CONTEXT_PRESSURE] * 3)
        b = _make_tensor(n_losses=3, loss_categories=[LossCategory.AUTHORIAL_CHOICE] * 3)
        ld_a = loss_distribution(a)
        ld_b = loss_distribution(b)
        dist = loss_distribution_distance(ld_a, ld_b)
        assert dist > 0.5  # very different distributions


class TestComponentDivergence:
    def test_identical_tensors(self):
        t = _make_tensor(n_losses=2, ifn="do the thing", questions=["why?"])
        div = component_divergence(t, t)
        assert div.overall < 0.05  # near-zero divergence

    def test_overall_range(self):
        a = _make_tensor(strand_titles=["Topic A"], ifn="plan A", n_losses=2)
        b = _make_tensor(strand_titles=["Topic B"], ifn="plan B", n_losses=5)
        div = component_divergence(a, b)
        assert 0.0 <= div.overall <= 1.0


class TestTrajectory:
    def test_basic_trajectory(self):
        tensors = [
            _make_tensor(cycle=1, strand_titles=["A", "B"], n_losses=2),
            _make_tensor(cycle=2, strand_titles=["A", "C"], n_losses=3),
            _make_tensor(cycle=3, strand_titles=["C", "D"], n_losses=1),
        ]
        stats = trajectory_stats(tensors)
        assert stats.cycles == 3
        assert stats.strand_counts == [2, 2, 2]
        assert stats.loss_counts == [2, 3, 1]
        assert len(stats.consecutive_divergence) == 2

    def test_compare_trajectories(self):
        a = [_make_tensor(cycle=i, strand_titles=[f"A{i}"]) for i in range(1, 6)]
        b = [_make_tensor(cycle=i, strand_titles=[f"B{i}"]) for i in range(1, 6)]
        comp = compare_trajectories(a, b)
        assert len(comp.cross_divergence) == 5
        assert 0.0 <= comp.mean_cross_divergence <= 1.0

    def test_empty_trajectory(self):
        stats = trajectory_stats([])
        assert stats.cycles == 0
        assert stats.strand_counts == []
