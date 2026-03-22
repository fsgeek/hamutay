"""Analyze graph topology from edge-enabled tensor experiments.

Extracts per-cycle graph metrics from tensors with depends_on edges:
- Root count (strands with no incoming edges)
- Max depth (longest path from any root)
- Branching factor (mean out-degree)
- Connected components
- Edge density (edges / max possible edges)

Also correlates graph metrics with breathing events (token contractions).

Usage:
    uv run python experiments/taste/analyze_graph_topology.py
    uv run python experiments/taste/analyze_graph_topology.py experiments/taste/auto_edges_lse_chicago_50
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def _build_graph(strands: list[dict]) -> dict:
    """Build adjacency structures from strand depends_on edges.

    Returns dict with:
    - titles: list of strand titles
    - children: title -> list of titles that depend on it
    - parents: title -> list of titles it depends on
    - roots: titles with no parents
    - leaves: titles with no children
    """
    titles = [s["title"] for s in strands]
    title_set = set(titles)

    children: dict[str, list[str]] = defaultdict(list)
    parents: dict[str, list[str]] = defaultdict(list)

    for s in strands:
        deps = s.get("depends_on", [])
        for dep in deps:
            if dep in title_set:  # only count valid edges
                children[dep].append(s["title"])
                parents[s["title"]].append(dep)

    roots = [t for t in titles if t not in parents or not parents[t]]
    leaves = [t for t in titles if t not in children or not children[t]]

    return {
        "titles": titles,
        "children": dict(children),
        "parents": dict(parents),
        "roots": roots,
        "leaves": leaves,
    }


def _max_depth(graph: dict) -> int:
    """Compute max depth from any root via BFS."""
    if not graph["titles"]:
        return 0

    children = graph["children"]
    max_d = 0

    for root in graph["roots"]:
        # BFS from this root
        queue = [(root, 0)]
        visited = {root}
        while queue:
            node, depth = queue.pop(0)
            max_d = max(max_d, depth)
            for child in children.get(node, []):
                if child not in visited:
                    visited.add(child)
                    queue.append((child, depth + 1))

    return max_d


def _connected_components(graph: dict) -> int:
    """Count connected components (treating edges as undirected)."""
    if not graph["titles"]:
        return 0

    adj: dict[str, set[str]] = defaultdict(set)
    for parent, kids in graph["children"].items():
        for kid in kids:
            adj[parent].add(kid)
            adj[kid].add(parent)

    visited: set[str] = set()
    components = 0

    for title in graph["titles"]:
        if title not in visited:
            components += 1
            # BFS
            queue = [title]
            visited.add(title)
            while queue:
                node = queue.pop(0)
                for neighbor in adj.get(node, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

    return components


def analyze_participant(jsonl_path: Path, label: str) -> list[dict]:
    """Analyze graph topology for each cycle of a participant."""
    records = []
    with open(jsonl_path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    results = []
    prev_tokens = 0

    for rec in records:
        tensor = rec.get("tensor", {})
        cycle = tensor.get("cycle", rec.get("cycle", 0))
        strands = tensor.get("strands", [])
        tokens = rec.get("tensor_token_estimate", len(json.dumps(tensor)) // 4)

        # Build graph
        graph = _build_graph(strands)
        n_strands = len(strands)
        n_edges = sum(
            len(s.get("depends_on", []))
            for s in strands
            if s.get("depends_on")
        )

        # Graph metrics
        max_possible_edges = n_strands * (n_strands - 1) if n_strands > 1 else 1
        edge_density = n_edges / max_possible_edges if max_possible_edges > 0 else 0
        mean_out_degree = n_edges / n_strands if n_strands > 0 else 0

        # Contraction detection
        contraction = False
        contraction_ratio = 1.0
        if prev_tokens > 0:
            contraction_ratio = tokens / prev_tokens
            contraction = contraction_ratio < 0.9

        result = {
            "label": label,
            "cycle": cycle,
            "tokens": tokens,
            "n_strands": n_strands,
            "n_edges": n_edges,
            "n_roots": len(graph["roots"]),
            "n_leaves": len(graph["leaves"]),
            "max_depth": _max_depth(graph),
            "mean_out_degree": round(mean_out_degree, 2),
            "edge_density": round(edge_density, 3),
            "connected_components": _connected_components(graph),
            "contraction": contraction,
            "contraction_ratio": round(contraction_ratio, 3),
            "root_titles": graph["roots"],
            "n_losses": len(tensor.get("declared_losses", [])),
            "n_shed_from": sum(
                1 for loss in tensor.get("declared_losses", [])
                if loss.get("shed_from")
            ),
        }
        results.append(result)
        prev_tokens = tokens

    return results


def print_trajectory(results: list[dict], label: str) -> None:
    """Print per-cycle graph topology trajectory."""
    print(f"\n{'='*70}")
    print(f"Graph Topology: {label}")
    print(f"{'='*70}")
    print(f"{'Cyc':>3} {'Tok':>6} {'Str':>3} {'Edg':>3} {'Root':>4} "
          f"{'Dep':>3} {'Deg':>4} {'Den':>5} {'CC':>2} {'Ctr':>5} "
          f"{'Loss':>4} {'Shed':>4}")
    print("-" * 70)

    for r in results:
        ctr = f"{r['contraction_ratio']:.2f}" if r["contraction"] else ""
        print(f"{r['cycle']:>3} {r['tokens']:>6} {r['n_strands']:>3} "
              f"{r['n_edges']:>3} {r['n_roots']:>4} "
              f"{r['max_depth']:>3} {r['mean_out_degree']:>4.1f} "
              f"{r['edge_density']:>5.3f} {r['connected_components']:>2} "
              f"{ctr:>5} {r['n_losses']:>4} {r['n_shed_from']:>4}")


def print_summary(all_results: dict[str, list[dict]]) -> None:
    """Print comparative summary across participants."""
    print(f"\n{'='*70}")
    print("TOPOLOGY SUMMARY")
    print(f"{'='*70}")

    for label, results in all_results.items():
        contraction_cycles = [r for r in results if r["contraction"]]
        non_contraction = [r for r in results if not r["contraction"]]

        print(f"\n{label}:")
        print(f"  Cycles: {len(results)}")
        print(f"  Contractions: {len(contraction_cycles)}")

        if results:
            # Mean metrics
            mean_roots = sum(r["n_roots"] for r in results) / len(results)
            mean_depth = sum(r["max_depth"] for r in results) / len(results)
            mean_edges = sum(r["n_edges"] for r in results) / len(results)
            mean_density = sum(r["edge_density"] for r in results) / len(results)
            print(f"  Mean roots: {mean_roots:.1f}")
            print(f"  Mean max depth: {mean_depth:.1f}")
            print(f"  Mean edges: {mean_edges:.1f}")
            print(f"  Mean edge density: {mean_density:.3f}")

        # Compare contraction vs non-contraction cycles
        if contraction_cycles and non_contraction:
            print(f"\n  During contractions ({len(contraction_cycles)} cycles):")
            c_roots = sum(r["n_roots"] for r in contraction_cycles) / len(contraction_cycles)
            c_edges = sum(r["n_edges"] for r in contraction_cycles) / len(contraction_cycles)
            c_depth = sum(r["max_depth"] for r in contraction_cycles) / len(contraction_cycles)
            print(f"    Mean roots: {c_roots:.1f}, edges: {c_edges:.1f}, depth: {c_depth:.1f}")

            print(f"  During non-contraction ({len(non_contraction)} cycles):")
            nc_roots = sum(r["n_roots"] for r in non_contraction) / len(non_contraction)
            nc_edges = sum(r["n_edges"] for r in non_contraction) / len(non_contraction)
            nc_depth = sum(r["max_depth"] for r in non_contraction) / len(non_contraction)
            print(f"    Mean roots: {nc_roots:.1f}, edges: {nc_edges:.1f}, depth: {nc_depth:.1f}")

        # Root title stability — how many roots survive between cycles?
        if len(results) > 1:
            root_survivals = []
            for i in range(1, len(results)):
                prev_roots = set(results[i-1]["root_titles"])
                curr_roots = set(results[i]["root_titles"])
                if prev_roots:
                    survival = len(prev_roots & curr_roots) / len(prev_roots)
                    root_survivals.append(survival)
            if root_survivals:
                mean_survival = sum(root_survivals) / len(root_survivals)
                print(f"  Root title survival (cycle-to-cycle): {mean_survival:.2f}")

        # Edge trajectory for the paper
        edge_traj = [r["n_edges"] for r in results]
        root_traj = [r["n_roots"] for r in results]
        depth_traj = [r["max_depth"] for r in results]
        print(f"\n  Edge trajectory:  {' → '.join(str(e) for e in edge_traj)}")
        print(f"  Root trajectory:  {' → '.join(str(r) for r in root_traj)}")
        print(f"  Depth trajectory: {' → '.join(str(d) for d in depth_traj)}")


def main():
    if len(sys.argv) > 1:
        dirs = [Path(d) for d in sys.argv[1:]]
    else:
        # Find all edge experiments
        taste_dir = Path("experiments/taste")
        dirs = sorted(
            d for d in taste_dir.iterdir()
            if d.is_dir() and "edges" in d.name
        )

    if not dirs:
        print("No edge experiment directories found.")
        return

    for exp_dir in dirs:
        if not exp_dir.is_dir():
            continue

        print(f"\n{'#'*70}")
        print(f"# Experiment: {exp_dir.name}")
        print(f"{'#'*70}")

        all_results: dict[str, list[dict]] = {}

        for p_file in sorted(exp_dir.glob("participant_*.jsonl")):
            label = p_file.stem
            results = analyze_participant(p_file, label)
            all_results[label] = results
            print_trajectory(results, f"{exp_dir.name}/{label}")

        if all_results:
            print_summary(all_results)

    # Cross-experiment comparison for edge experiments
    if len(dirs) > 1:
        print(f"\n{'#'*70}")
        print("# CROSS-EXPERIMENT COMPARISON")
        print(f"{'#'*70}")
        for exp_dir in dirs:
            for p_file in sorted(exp_dir.glob("participant_*.jsonl")):
                results = analyze_participant(p_file, p_file.stem)
                n = len(results)
                if not results:
                    continue
                mean_roots = sum(r["n_roots"] for r in results) / n
                mean_edges = sum(r["n_edges"] for r in results) / n
                contractions = sum(1 for r in results if r["contraction"])
                total_losses = sum(r["n_losses"] for r in results)
                print(f"  {exp_dir.name}/{p_file.stem}: "
                      f"{n} cycles, {mean_roots:.1f} roots, "
                      f"{mean_edges:.1f} edges, {contractions} contractions, "
                      f"{total_losses} losses")


if __name__ == "__main__":
    main()
