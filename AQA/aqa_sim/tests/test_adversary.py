"""Tests for adversarial node behaviors."""
import numpy as np
import pytest
from simulator.node import Node
from simulator.adversary import apply_behavior, get_reported_trust


@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def sample_msg():
    return {
        "type": "PREPARE",
        "block": 1,
        "vote": True,
        "sender": 0,
        "latency_ms": 100,
    }


def make_node(**overrides):
    """Build a Node with sensible defaults; override any field via kwargs."""
    defaults = dict(
        id=0,
        group_id=0,
        ground_truth_trust=0.8,
        behavior_type="honest",
        availability_prob=0.95,
        base_latency_ms=50,
    )
    defaults.update(overrides)
    return Node(**defaults)


def test_crash_drops_all_messages(rng, sample_msg):
    node = make_node(behavior_type="crash", availability_prob=0.0)
    for _ in range(100):
        assert apply_behavior(node, sample_msg, rng) is None


def test_equivocator_sends_conflicting(rng, sample_msg):
    node = make_node(behavior_type="equivocate")
    result = apply_behavior(node, sample_msg, rng)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["vote"] != result[1]["vote"]


def test_lie_trust_returns_high():
    node = make_node(behavior_type="lie_trust", ground_truth_trust=0.05)
    assert get_reported_trust(node) >= 0.9


def test_slow_node_triples_latency(rng, sample_msg):
    node = make_node(behavior_type="slow", base_latency_ms=100)
    result = apply_behavior(node, sample_msg, rng)
    assert result["latency_ms"] >= 3 * sample_msg["latency_ms"] - 1