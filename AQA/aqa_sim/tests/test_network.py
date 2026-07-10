"""
Tests for the Network module: latency generation, packet drops,
partitions, and churn behavior.
"""
from __future__ import annotations

import numpy as np
import pytest

from simulator.node import Node
from simulator.network import Network


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture
def rng():
    """Deterministic RNG for reproducibility."""
    return np.random.default_rng(42)


@pytest.fixture
def sample_msg():
    """A standard PREPARE message used across tests."""
    return {
        "type": "PREPARE",
        "block": 1,
        "vote": True,
        "sender": 0,
        "receiver": 1,
    }


def _make_node(node_id: int, group_id: int = 0, latency: float = 50.0) -> Node:
    """Small helper to build honest nodes for network tests."""
    return Node(
        id=node_id,
        group_id=group_id,
        ground_truth_trust=0.9,
        behavior_type="honest",
        availability_prob=1.0,
        base_latency_ms=latency,
    )


@pytest.fixture
def sender_node():
    return _make_node(node_id=0, group_id=0, latency=50.0)


@pytest.fixture
def receiver_node():
    return _make_node(node_id=1, group_id=0, latency=80.0)


@pytest.fixture
def four_nodes():
    """Four nodes in two logical groups, for partition tests."""
    return [
        _make_node(0, group_id=0),
        _make_node(1, group_id=0),
        _make_node(2, group_id=1),
        _make_node(3, group_id=1),
    ]


# -------------------------------------------------------------------
# Latency tests
# -------------------------------------------------------------------

def test_latency_never_negative(rng, sender_node, receiver_node, sample_msg):
    """Latency must be clamped to a positive floor (≥5ms) across many draws."""
    net = Network(rng=rng, drop_prob=0.0)
    for _ in range(1000):
        delivered, latency = net.send(sender_node, receiver_node, sample_msg)
        assert delivered is True, "With drop_prob=0.0, every message must be delivered"
        assert latency >= 5.0, f"Latency floor violated: {latency}"


def test_latency_centered_on_base(rng, sender_node, receiver_node, sample_msg):
    """Mean observed latency should be near receiver.base_latency_ms."""
    net = Network(rng=rng, drop_prob=0.0)
    samples = []
    for _ in range(2000):
        _, latency = net.send(sender_node, receiver_node, sample_msg)
        samples.append(latency)

    mean = float(np.mean(samples))
    # Receiver base latency is 80ms; allow ±10ms tolerance for sample variance
    assert 70.0 <= mean <= 90.0, f"Mean latency {mean:.1f}ms not near 80ms"


# -------------------------------------------------------------------
# Drop probability tests
# -------------------------------------------------------------------

def test_drop_probability_correct(sender_node, receiver_node, sample_msg):
    """Empirical drop rate should be ~5% over 10 000 sends (95% CI: ~4–6%)."""
    rng = np.random.default_rng(42)
    net = Network(rng=rng, drop_prob=0.05)

    drops = 0
    for _ in range(10_000):
        delivered, _ = net.send(sender_node, receiver_node, sample_msg)
        if not delivered:
            drops += 1

    # Binomial 95% CI: 500 ± 1.96*sqrt(10000*0.05*0.95) ≈ 500 ± 43
    assert 400 < drops < 600, f"Drop count {drops} outside expected 95% CI"


def test_zero_drop_probability_never_drops(rng, sender_node, receiver_node, sample_msg):
    """With drop_prob=0, no message should ever be dropped."""
    net = Network(rng=rng, drop_prob=0.0)
    for _ in range(500):
        delivered, _ = net.send(sender_node, receiver_node, sample_msg)
        assert delivered is True


def test_full_drop_probability_always_drops(rng, sender_node, receiver_node, sample_msg):
    """With drop_prob=1.0, no message should ever be delivered."""
    net = Network(rng=rng, drop_prob=1.0)
    for _ in range(500):
        delivered, _ = net.send(sender_node, receiver_node, sample_msg)
        assert delivered is False


# -------------------------------------------------------------------
# Partition tests
# -------------------------------------------------------------------

def test_partition_isolates_across_groups(rng, four_nodes, sample_msg):
    """Nodes on opposite sides of a partition cannot communicate."""
    net = Network(
        rng=rng,
        drop_prob=0.0,
        partition_config={"group_a": [0, 1], "group_b": [2, 3]},
    )
    # Sender in group_a (id=0) → receiver in group_b (id=2): must be dropped
    delivered, _ = net.send(four_nodes[0], four_nodes[2], sample_msg)
    assert delivered is False, "Cross-partition send should be dropped"


def test_partition_allows_intra_group(rng, four_nodes, sample_msg):
    """Nodes within the same partition side should communicate normally."""
    net = Network(
        rng=rng,
        drop_prob=0.0,
        partition_config={"group_a": [0, 1], "group_b": [2, 3]},
    )
    # Both nodes in group_a
    delivered, latency = net.send(four_nodes[0], four_nodes[1], sample_msg)
    assert delivered is True, "Intra-partition send should succeed"
    assert latency >= 5.0


def test_partition_can_be_enabled_and_disabled(rng, four_nodes, sample_msg):
    """A partition activated mid-run can be lifted and traffic resumes."""
    net = Network(rng=rng, drop_prob=0.0)

    # Before partition: cross-group send works
    delivered_before, _ = net.send(four_nodes[0], four_nodes[2], sample_msg)
    assert delivered_before is True

    # Enable partition
    net.enable_partition({"group_a": [0, 1], "group_b": [2, 3]})
    delivered_during, _ = net.send(four_nodes[0], four_nodes[2], sample_msg)
    assert delivered_during is False

    # Disable partition
    net.disable_partition()
    delivered_after, _ = net.send(four_nodes[0], four_nodes[2], sample_msg)
    assert delivered_after is True


# -------------------------------------------------------------------
# Churn tests
# -------------------------------------------------------------------

def test_churn_toggles_availability(rng, four_nodes):
    """After many churn steps with p_leave=1.0, all nodes should be offline."""
    net = Network(rng=rng, drop_prob=0.0)
    for _ in range(5):
        net.churn_step(four_nodes, p_leave=1.0, p_join=0.0, rng=rng)
    assert all(not n.is_online for n in four_nodes), \
        "All nodes should be offline after forced leave"


def test_churn_rejoin(rng, four_nodes):
    """After forcing offline then p_join=1.0, all nodes should be back online."""
    net = Network(rng=rng, drop_prob=0.0)
    # Force everyone offline
    for n in four_nodes:
        n.is_online = False
    # Force everyone to rejoin
    net.churn_step(four_nodes, p_leave=0.0, p_join=1.0, rng=rng)
    assert all(n.is_online for n in four_nodes)


def test_offline_node_cannot_send(rng, sender_node, receiver_node, sample_msg):
    """A message from an offline sender should be dropped."""
    net = Network(rng=rng, drop_prob=0.0)
    sender_node.is_online = False
    delivered, _ = net.send(sender_node, receiver_node, sample_msg)
    assert delivered is False