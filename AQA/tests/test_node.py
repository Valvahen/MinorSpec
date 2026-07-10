import pytest
import numpy as np
from simulator.node import Node

def test_trust_perfect_node():
    """A node with 100% uptime, agreement, fast RTT → trust ≈ 1.0"""
    n = Node(id=0, group_id=0, ground_truth_trust=1.0, 
             behavior_type="honest", availability_prob=1.0, base_latency_ms=50)
    for _ in range(20):
        n.record_round(participated=True, voted=True, agreed_with_majority=True, 
                       rtt_ms=50, misbehaved=False)
    assert n.compute_trust_estimate() > 0.9

def test_trust_crashed_node():
    """A node that never participates → trust ≈ 0"""
    n = Node(id=0, group_id=0, ground_truth_trust=0.1, 
             behavior_type="crash", availability_prob=0.0, base_latency_ms=50)
    for _ in range(20):
        n.record_round(participated=False, voted=False, agreed_with_majority=False, 
                       rtt_ms=None, misbehaved=False)
    assert n.compute_trust_estimate() < 0.2

def test_trust_in_bounds():
    """Trust must always be in [0, 1]"""
    rng = np.random.default_rng(42)
    n = Node(id=0, group_id=0, ground_truth_trust=0.5, 
             behavior_type="honest", availability_prob=0.8, base_latency_ms=100)
    for _ in range(100):
        n.record_round(
            participated=rng.random() < 0.7,
            voted=rng.random() < 0.6,
            agreed_with_majority=rng.random() < 0.5,
            rtt_ms=rng.normal(100, 30),
            misbehaved=rng.random() < 0.1
        )
        t = n.compute_trust_estimate()
        assert 0.0 <= t <= 1.0

def test_sliding_window():
    """response_times deque respects maxlen"""
    n = Node(id=0, group_id=0, ground_truth_trust=0.5, 
             behavior_type="honest", availability_prob=1.0, base_latency_ms=50)
    for i in range(30):
        n.record_round(True, True, True, rtt_ms=i, misbehaved=False)
    assert len(n.response_times) == 20  # not 30