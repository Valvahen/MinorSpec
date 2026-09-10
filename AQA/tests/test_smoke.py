"""Smoke tests for core protocol execution paths."""

from __future__ import annotations

from typing import Any

import numpy as np

from aqa_sim.simulator.network import Network
from aqa_sim.simulator.node import Node
from aqa_sim.simulator.protocol_aqa import AQASplitBFTProtocol
from aqa_sim.simulator.protocol_splitbft import SplitBFTProtocol


def make_nodes(n_nodes: int) -> list[Node]:
    """Create deterministic honest nodes for smoke-test protocol runs."""
    nodes: list[Node] = []
    for node_id in range(n_nodes):
        nodes.append(
            Node(
                id=node_id,
                group_id=0,
                ground_truth_trust=0.9,
                behavior_type="honest",
                availability_prob=0.99,
                base_latency_ms=20.0,
            )
        )
    return nodes


def run_short_protocol(protocol_name: str) -> dict[str, int | float]:
    """Execute a short fixed-length simulation for one protocol and collect key counts."""
    rng = np.random.default_rng(20260708)
    nodes = make_nodes(n_nodes=5)
    network = Network(rng=rng, drop_prob=0.0, partition_config=None)

    config: dict[str, Any] = {"n_miners": 5, "q_min": 3, "q_max": 5}
    if protocol_name == "splitbft":
        protocol = SplitBFTProtocol(nodes=nodes, network=network, rng=rng, config=config)
    elif protocol_name == "aqa":
        protocol = AQASplitBFTProtocol(nodes=nodes, network=network, rng=rng, config=config)
    else:
        raise ValueError(f"Unknown protocol_name: {protocol_name}")

    blocks_finalized = 0
    total_messages = 0
    for round_no in range(3):
        result = protocol.run_round(round_no=round_no)
        blocks_finalized += int(result.finalized)
        total_messages += int(result.msgs)

    safety_violations = sum(1 for line in getattr(protocol, "logs", []) if "unsafe_quorum" in line)
    return {
        "blocks_finalized": blocks_finalized,
        "total_messages": total_messages,
        "safety_violations": safety_violations,
    }


def test_splitbft_smoke() -> None:
    """Assert baseline SplitBFT completes short runs without safety violations."""
    stats = run_short_protocol(protocol_name="splitbft")
    assert int(stats["blocks_finalized"]) > 0
    assert int(stats["total_messages"]) > 0
    assert int(stats["safety_violations"]) == 0


def test_aqa_smoke() -> None:
    """Assert AQA protocol completes short runs and emits communication."""
    stats = run_short_protocol(protocol_name="aqa")
    assert int(stats["blocks_finalized"]) > 0
    assert int(stats["total_messages"]) > 0
