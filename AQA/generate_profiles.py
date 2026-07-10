"""Generate synthetic node trust profiles for AQA-Sim experiments."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

BEHAVIORS: tuple[str, ...] = ("honest", "crash", "equivocate", "lie_trust", "slow")
PROFILES: tuple[str, ...] = ("uniform", "bimodal", "10pct_byz", "20pct_byz", "30pct_byz")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for profile generation."""
    parser = argparse.ArgumentParser(
        description="Generate trust_profiles.csv for AQA-Sim"
    )
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default="uniform",
        help="Profile template to generate",
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=100,
        help="Number of nodes to generate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("trust_profiles.csv"),
        help="Output CSV path",
    )
    return parser.parse_args()


def clamp_trust(values: np.ndarray) -> np.ndarray:
    """Clamp trust scores into the valid [0.0, 1.0] interval."""
    return np.clip(values, 0.0, 1.0)


def _sample_behavior_counts(n_nodes: int, profile: str) -> Dict[str, int]:
    """Return exact behavior counts for a selected profile."""
    if n_nodes < 1:
        raise ValueError("--nodes must be >= 1")

    if profile == "uniform":
        raw = {
            "honest": int(round(0.70 * n_nodes)),
            "crash": int(round(0.10 * n_nodes)),
            "equivocate": int(round(0.07 * n_nodes)),
            "lie_trust": int(round(0.06 * n_nodes)),
            "slow": int(round(0.07 * n_nodes)),
        }
    elif profile == "bimodal":
        raw = {
            "honest": int(round(0.60 * n_nodes)),
            "crash": int(round(0.08 * n_nodes)),
            "equivocate": int(round(0.12 * n_nodes)),
            "lie_trust": int(round(0.10 * n_nodes)),
            "slow": int(round(0.10 * n_nodes)),
        }
    else:
        byz_pct = int(profile.split("pct")[0]) / 100.0
        byz_count = int(round(n_nodes * byz_pct))
        equivocate_count = byz_count // 2
        lie_count = byz_count - equivocate_count

        crash_count = int(round(0.08 * n_nodes))
        slow_count = int(round(0.12 * n_nodes))
        honest_count = n_nodes - (equivocate_count + lie_count + crash_count + slow_count)
        if honest_count < 0:
            deficit = -honest_count
            reduce_slow = min(deficit, slow_count)
            slow_count -= reduce_slow
            deficit -= reduce_slow
            crash_count = max(crash_count - deficit, 0)
            honest_count = 0

        raw = {
            "honest": honest_count,
            "crash": crash_count,
            "equivocate": equivocate_count,
            "lie_trust": lie_count,
            "slow": slow_count,
        }

    total = sum(raw.values())
    if total != n_nodes:
        raw["honest"] += n_nodes - total

    return raw


def _sample_metric_arrays(
    behaviors: np.ndarray,
    profile: str,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sample trust, availability, and latency arrays conditioned on behavior."""
    n_nodes = behaviors.shape[0]
    trust = np.empty(n_nodes, dtype=float)
    availability = np.empty(n_nodes, dtype=float)
    latency = np.empty(n_nodes, dtype=float)

    for behavior in BEHAVIORS:
        idx = np.flatnonzero(behaviors == behavior)
        if idx.size == 0:
            continue

        if behavior == "honest":
            trust[idx] = rng.normal(0.88, 0.08, idx.size)
            availability[idx] = rng.uniform(0.94, 1.00, idx.size)
            latency[idx] = rng.normal(45.0, 10.0, idx.size)
        elif behavior == "crash":
            trust[idx] = rng.normal(0.28, 0.15, idx.size)
            availability[idx] = rng.uniform(0.05, 0.55, idx.size)
            latency[idx] = rng.normal(85.0, 20.0, idx.size)
        elif behavior == "equivocate":
            trust[idx] = rng.normal(0.15, 0.10, idx.size)
            availability[idx] = rng.uniform(0.80, 1.00, idx.size)
            latency[idx] = rng.normal(60.0, 18.0, idx.size)
        elif behavior == "lie_trust":
            trust[idx] = rng.normal(0.20, 0.12, idx.size)
            availability[idx] = rng.uniform(0.85, 1.00, idx.size)
            latency[idx] = rng.normal(58.0, 15.0, idx.size)
        else:
            trust[idx] = rng.normal(0.58, 0.12, idx.size)
            availability[idx] = rng.uniform(0.65, 0.95, idx.size)
            latency[idx] = rng.normal(170.0, 25.0, idx.size)

    if profile == "bimodal":
        modal_offsets = rng.choice(np.array([-0.22, 0.22]), size=n_nodes, p=[0.50, 0.50])
        trust = trust + modal_offsets

    trust = clamp_trust(trust)
    availability = np.clip(availability, 0.0, 1.0)
    latency = np.clip(latency, 5.0, None)

    return trust, availability, latency


def generate_profiles(
    n_nodes: int,
    profile: str,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Generate a DataFrame of node trust profiles for simulations."""
    counts = _sample_behavior_counts(n_nodes=n_nodes, profile=profile)

    behavior_labels: List[str] = []
    for behavior in BEHAVIORS:
        behavior_labels.extend([behavior] * counts[behavior])

    behaviors = np.array(behavior_labels, dtype=object)
    rng.shuffle(behaviors)

    trust, availability, latency = _sample_metric_arrays(
        behaviors=behaviors,
        profile=profile,
        rng=rng,
    )

    data = pd.DataFrame(
        {
            "node_id": np.arange(n_nodes, dtype=int),
            "ground_truth_trust": np.round(trust, 4),
            "behavior_type": behaviors,
            "availability_prob": np.round(availability, 4),
            "base_latency_ms": np.round(latency, 2),
        }
    )
    return data


def main() -> None:
    """Generate and save trust profiles based on command-line options."""
    args = parse_args()
    rng = np.random.default_rng(args.seed)

    df = generate_profiles(n_nodes=args.nodes, profile=args.profile, rng=rng)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)

    behavior_counts = df["behavior_type"].value_counts().to_dict()
    print(f"Wrote {len(df)} rows to {args.output}")
    print(f"Profile: {args.profile} | Seed: {args.seed}")
    print(f"Behavior counts: {behavior_counts}")


if __name__ == "__main__":
    main()
