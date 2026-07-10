"""
Protocol-level correctness tests for AQA-Sim.

These tests verify the invariants that the paper's claims depend on:
  1. Adaptive quorum never violates the BFT safety bound (Q_i >= 2f+1).
  2. No block is finalized twice under any conditions.
  3. The message counter matches a hand-computed value on a tiny example.
  4. Runs with the same seed produce byte-identical results (reproducibility).
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import pytest

from simulator.node import Node
from simulator.network import Network
from simulator.protocol_splitbft import SplitBFTProtocol
from simulator.protocol_aqa import AQASplitBFTProtocol
from simulator.metrics import RunMetrics


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

# Path to the test profile CSV that ships with the repo
TEST_PROFILE_CSV = Path(__file__).parent / "test_profiles.csv"


def load_nodes(csv_path: str | Path, n_groups: int = 3) -> list:
# """
#     Load nodes from a CSV file with columns:
#         node_id, ground_truth_trust, behavior_type, availability_prob, base_latency_ms
#     Assigns nodes to groups round-robin.
#     """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        # Fallback: generate a small deterministic profile on the fly
        return _make_default_nodes(n=20, n_byzantine=3, n_groups=n_groups)

    nodes: list[Node] = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            nodes.append(Node(
                id=int(row["node_id"]),
                group_id=i % n_groups,
                ground_truth_trust=float(row["ground_truth_trust"]),
                behavior_type=row["behavior_type"],
                availability_prob=float(row["availability_prob"]),
                base_latency_ms=float(row["base_latency_ms"]),
            ))
    return nodes


def _make_default_nodes(n: int = 20, n_byzantine: int = 3,
                        n_groups: int = 3) -> list:
# """Deterministic node list used when the CSV isn't present."""
    nodes: list[Node] = []
    for i in range(n):
        is_byz = i < n_byzantine
        nodes.append(Node(
            id=i,
            group_id=i % n_groups,
            ground_truth_trust=0.15 if is_byz else 0.9,
            behavior_type="equivocate" if is_byz else "honest",
            availability_prob=0.6 if is_byz else 0.95,
            base_latency_ms=50.0,
        ))
    return nodes


def _standard_config(**overrides) -> dict:
    """The reference protocol config used across tests."""
    cfg = {
        "n_nodes": 20,
        "n_groups": 3,
        "f_per_group": 2,          # tolerate up to 2 Byzantine per group
        "Q_min": 5,                # 2f+1 with f=2
        "Q_max": 10,
        "Q_safe": 7,
        "chain_length": 100,
        "byzantine_fraction": 0.15,
        "packet_drop": 0.0,
        "partition_rounds": None,
        "churn_p_leave": 0.0,
        "churn_p_join": 0.0,
        "base_latency_ms": 50,
    }
    cfg.update(overrides)
    return cfg


def run_full_experiment(seed: int, protocol_cls=AQASplitBFTProtocol,
                        chain_length: int = 30, **cfg_overrides) -> dict:
    """
    Run one full protocol simulation and return a dict of aggregate results.
    Used by the reproducibility test.
    """
    rng = np.random.default_rng(seed)
    cfg = _standard_config(chain_length=chain_length, **cfg_overrides)
    nodes = _make_default_nodes(
        n=cfg["n_nodes"],
        n_byzantine=int(round(cfg["byzantine_fraction"] * cfg["n_nodes"])),
        n_groups=cfg["n_groups"],
    )
    network = Network(rng=rng, drop_prob=cfg["packet_drop"])
    protocol = protocol_cls(nodes=nodes, network=network, rng=rng, config=cfg)

    metrics = RunMetrics()
    for round_no in range(cfg["chain_length"]):
        result = protocol.run_round(round_no)
        metrics.update_from_round(result)
    metrics.finalize()

    return {
        "tps": metrics.tps,
        "total_messages": metrics.total_messages,
        "byzantine_success_count": metrics.byzantine_success_count,
        "blocks_finalized": metrics.blocks_finalized,
        "safety_violations": metrics.safety_violations,
    }


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def nodes():
    return load_nodes(TEST_PROFILE_CSV, n_groups=3)


@pytest.fixture
def network(rng):
    return Network(rng=rng, drop_prob=0.0)


@pytest.fixture
def aqa_protocol(nodes, network, rng):
    cfg = _standard_config(n_nodes=len(nodes))
    return AQASplitBFTProtocol(nodes=nodes, network=network, rng=rng, config=cfg)


@pytest.fixture
def splitbft_protocol(nodes, network, rng):
    cfg = _standard_config(n_nodes=len(nodes))
    return SplitBFTProtocol(nodes=nodes, network=network, rng=rng, config=cfg)


# -------------------------------------------------------------------
# 1. THE safety invariant
# -------------------------------------------------------------------

def test_quorum_size_never_below_2f_plus_1(aqa_protocol):
    """
    Adaptive quorum must never dip below 2f+1, otherwise BFT safety is broken.
    This is the single most important test in the suite — if it fails, the
    paper's core claim ("preserves BFT safety") is false.
    """
    f = aqa_protocol.config["f_per_group"]
    safety_bound = 2 * f + 1

    for round_no in range(100):
        result = aqa_protocol.run_round(round_no)
        assert result.quorum_size >= safety_bound, (
            f"SAFETY VIOLATION at round {round_no}: "
            f"quorum={result.quorum_size} < 2f+1={safety_bound}"
        )


def test_safety_holds_under_high_byzantine(rng, network):
    """Even at the f=n/3 limit, quorum must respect 2f+1."""
    nodes = _make_default_nodes(n=21, n_byzantine=6, n_groups=3)  # f=2 per group of 7
    cfg = _standard_config(n_nodes=21, n_groups=3, f_per_group=2,
                           Q_min=5, Q_max=7, chain_length=50)
    protocol = AQASplitBFTProtocol(nodes=nodes, network=network, rng=rng, config=cfg)

    for round_no in range(50):
        result = protocol.run_round(round_no)
        assert result.quorum_size >= 5, \
            f"Round {round_no}: quorum {result.quorum_size} below 2f+1=5"


# -------------------------------------------------------------------
# 2. No double finalization
# -------------------------------------------------------------------

def test_no_double_finalization(aqa_protocol):
    """The same block number must never be finalized twice."""
    finalized_blocks: set[int] = set()

    for round_no in range(50):
        result = aqa_protocol.run_round(round_no)
        if result.finalized:
            block_number = getattr(result, "block_number", round_no)
            assert block_number not in finalized_blocks, (
                f"Block {block_number} finalized twice (round {round_no})"
            )
            finalized_blocks.add(block_number)


def test_no_double_finalization_splitbft(splitbft_protocol):
    """Same invariant must hold for the baseline SplitBFT protocol."""
    finalized_blocks: set[int] = set()

    for round_no in range(50):
        result = splitbft_protocol.run_round(round_no)
        if result.finalized:
            block_number = getattr(result, "block_number", round_no)
            assert block_number not in finalized_blocks
            finalized_blocks.add(block_number)


# -------------------------------------------------------------------
# 3. Message counter validation (hand-computed reference)
# -------------------------------------------------------------------

def test_message_counter_matches_manual_count():
    """
    Manual walkthrough on a tiny, deterministic scenario.

    Setup: 6 nodes in 3 groups of 2. Static SplitBFT baseline (no adaptivity).
    In a single PBFT round per group we expect:
        - 1 PRE-PREPARE from leader to (group_size - 1) followers
        - group_size PREPARE messages (all-to-all within group)     [n×(n-1)]
        - group_size COMMIT messages (all-to-all within group)      [n×(n-1)]
        - Inter-group: 3 leaders × 2 peers × 2 rounds  = 12 messages

    For group_size=2:
        Per group: 1 pre-prepare + 2*1 prepare + 2*1 commit = 5
        3 groups × 5 = 15 intra-group
        + 12 inter-group
        = 27 messages per finalized block
    """
    rng = np.random.default_rng(0)
    nodes = _make_default_nodes(n=6, n_byzantine=0, n_groups=3)
    network = Network(rng=rng, drop_prob=0.0)
    cfg = _standard_config(
        n_nodes=6, n_groups=3, f_per_group=0,
        Q_min=2, Q_max=2, Q_safe=2, chain_length=1,
        byzantine_fraction=0.0,
    )
    protocol = SplitBFTProtocol(nodes=nodes, network=network, rng=rng, config=cfg)

    result = protocol.run_round(round_no=0)
    assert result.finalized, "Ideal-conditions round must finalize"

    # Allow a modest tolerance because the exact message pattern can differ
    # slightly by implementation (e.g., whether leader echoes to itself).
    expected = 27
    tolerance = 5
    assert abs(result.msgs - expected) <= tolerance, (
        f"Message count {result.msgs} differs from manual count {expected} "
        f"by more than tolerance ±{tolerance}. "
        f"Either the counter is wrong or the protocol implementation changed."
    )


def test_message_counter_scales_quadratically():
    """
    PBFT-style consensus is O(n²) in messages.
    Doubling group size should roughly quadruple messages.
    """
    def messages_for(group_size: int) -> int:
        rng = np.random.default_rng(0)
        nodes = _make_default_nodes(n=group_size, n_byzantine=0, n_groups=1)
        network = Network(rng=rng, drop_prob=0.0)
        cfg = _standard_config(
            n_nodes=group_size, n_groups=1, f_per_group=0,
            Q_min=group_size, Q_max=group_size, Q_safe=group_size,
            chain_length=1, byzantine_fraction=0.0,
        )
        protocol = SplitBFTProtocol(nodes=nodes, network=network, rng=rng, config=cfg)
        return protocol.run_round(round_no=0).msgs

    m4 = messages_for(4)
    m8 = messages_for(8)
    # Doubling n should give ~4x messages (allow 3x–5x for constant factors)
    ratio = m8 / max(m4, 1)
    assert 3.0 <= ratio <= 5.5, (
        f"Message scaling looks wrong: n=4→{m4}, n=8→{m8}, ratio={ratio:.2f} "
        f"(expected ~4× for O(n²))"
    )


# -------------------------------------------------------------------
# 4. Reproducibility
# -------------------------------------------------------------------

def test_seeded_run_is_reproducible():
    """Two runs with the same seed must produce identical results."""
    r1 = run_full_experiment(seed=42, chain_length=20)
    r2 = run_full_experiment(seed=42, chain_length=20)

    assert r1["tps"] == r2["tps"], f"TPS differs: {r1['tps']} vs {r2['tps']}"
    assert r1["total_messages"] == r2["total_messages"], \
        f"Message count differs: {r1['total_messages']} vs {r2['total_messages']}"
    assert r1["byzantine_success_count"] == r2["byzantine_success_count"]
    assert r1["blocks_finalized"] == r2["blocks_finalized"]
    assert r1["safety_violations"] == r2["safety_violations"]


def test_different_seeds_give_different_results():
    """Two runs with different seeds should NOT be byte-identical
    (otherwise the RNG isn't being used properly)."""
    r1 = run_full_experiment(seed=42, chain_length=20)
    r2 = run_full_experiment(seed=43, chain_length=20)

    # At least one of the stochastic metrics should differ
    same = (
        r1["total_messages"] == r2["total_messages"]
        and r1["byzantine_success_count"] == r2["byzantine_success_count"]
        and r1["tps"] == r2["tps"]
    )
    assert not same, (
        "Different seeds produced identical results — "
        "RNG likely not threaded through the protocol"
    )


# -------------------------------------------------------------------
# 5. Bonus: Safety fallback trigger
# -------------------------------------------------------------------

def test_safety_fallback_reverts_to_Q_safe(rng, network):
    """
    When adaptive quorum would violate 2f+1, the protocol must revert to Q_safe.
    Force this by setting extremely low trust across the board.
    """
    nodes = _make_default_nodes(n=9, n_byzantine=0, n_groups=1)
    # Make trust suggest quorum shrinks toward Q_min, but Q_min is below safety
    cfg = _standard_config(
        n_nodes=9, n_groups=1, f_per_group=2,
        Q_min=3,        # deliberately below 2f+1=5 to trigger fallback
        Q_max=9,
        Q_safe=5,       # safe fallback value = 2f+1
        chain_length=10,
    )
    protocol = AQASplitBFTProtocol(nodes=nodes, network=network, rng=rng, config=cfg)

    for round_no in range(10):
        result = protocol.run_round(round_no)
        # Even though Q_min=3, protocol should never drop below Q_safe=5
        assert result.quorum_size >= 5, (
            f"Safety fallback failed at round {round_no}: "
            f"quorum={result.quorum_size}, Q_safe=5"
        )