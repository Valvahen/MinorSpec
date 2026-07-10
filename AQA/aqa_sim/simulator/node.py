"""Node model for AQA-Sim protocol simulations."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque, Mapping

import numpy as np
import pandas as pd

RTT_MAX_MS: float = 500.0


@dataclass
class Node:
    """Represents a simulation node with static attributes and dynamic trust state."""

    id: int
    group_id: int
    ground_truth_trust: float
    behavior_type: str
    availability_prob: float
    base_latency_ms: float

    uptime_rounds: int = 0
    total_rounds: int = 0
    votes_agreed: int = 0
    votes_total: int = 0
    response_times: Deque[float] = field(default_factory=lambda: deque(maxlen=20))
    malicious_flags: int = 0
    trust_estimate: float = 0.5
    is_online: bool=True

    def record_round(
        self,
        participated: bool,
        voted: bool,
        agreed_with_majority: bool,
        rtt_ms: float | None,
        misbehaved: bool,
    ) -> None:
        """Update node telemetry from one consensus round and refresh trust estimate."""
        self.total_rounds += 1

        if participated:
            self.uptime_rounds += 1
            if rtt_ms is not None:
                self.response_times.append(float(rtt_ms))

        if voted:
            self.votes_total += 1
            if agreed_with_majority:
                self.votes_agreed += 1

        if misbehaved:
            self.malicious_flags += 1

        self.compute_trust_estimate()

    def compute_trust_estimate(self) -> float:
        """Compute weighted trust estimate and clamp output to the [0, 1] range."""
        uptime = self.uptime_rounds / self.total_rounds if self.total_rounds > 0 else 0.0
        vote_agreement = (
            self.votes_agreed / self.votes_total if self.votes_total > 0 else 0.0
        )

        avg_rtt_ms = (
            float(np.mean(np.asarray(self.response_times, dtype=float)))
            if len(self.response_times) > 0
            else RTT_MAX_MS
        )
        rtt_norm = min(avg_rtt_ms / RTT_MAX_MS, 1.0)

        denominator = max(self.uptime_rounds, 1)
        honesty = max(0.0, 1.0 - (self.malicious_flags / denominator))

        trust_score = (
            0.35 * uptime
            + 0.30 * vote_agreement
            + 0.20 * (1.0 - rtt_norm)
            + 0.15 * honesty
        )

        self.trust_estimate = float(np.clip(trust_score, 0.0, 1.0))
        return self.trust_estimate

    @classmethod
    def from_csv_row(cls, row: Mapping[str, Any]) -> Node:
        """Build a node from one trust profile CSV row."""
        node_id = int(row["node_id"])
        group_id = int(row.get("group_id", node_id % 4))
        return cls(
            id=node_id,
            group_id=group_id,
            ground_truth_trust=float(row["ground_truth_trust"]),
            behavior_type=str(row["behavior_type"]),
            availability_prob=float(row["availability_prob"]),
            base_latency_ms=float(row["base_latency_ms"]),
        )


def _load_nodes_from_csv(csv_path: Path) -> list[Node]:
    """Load all nodes from a trust profile CSV file."""
    frame = pd.read_csv(csv_path)
    return [Node.from_csv_row(row) for row in frame.to_dict(orient="records")]


def _smoke_test(csv_path: Path) -> None:
    """Run a simple smoke test by loading and printing three sample nodes."""
    nodes = _load_nodes_from_csv(csv_path)
    print(f"Loaded {len(nodes)} nodes from {csv_path}")
    print("Sample nodes:")
    for node in nodes[:3]:
        print(node)


def main() -> None:
    """Entry point for running the Node smoke test from the command line."""
    default_path = Path("trust_profiles.csv")
    if not default_path.exists():
        raise FileNotFoundError(
            "trust_profiles.csv not found. Run generate_profiles.py first."
        )
    _smoke_test(default_path)


if __name__ == "__main__":
    main()
