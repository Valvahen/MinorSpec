def test_latency_never_negative(rng):
    net = Network(rng, drop_prob=0.0)
    for _ in range(1000):
        _, latency = net.send(sender_node, receiver_node, msg)
        assert latency >= 5.0

def test_drop_probability_correct():
    """~5% drop rate over 10000 sends"""
    rng = np.random.default_rng(42)
    net = Network(rng, drop_prob=0.05)
    drops = sum(1 for _ in range(10000) if not net.send(a, b, msg)[0])
    assert 400 < drops < 600  # 95% CI around 500

def test_partition_isolates():
    """Nodes across partition can't communicate"""
    net = Network(rng, drop_prob=0.0, partition_config={"group_a": [0,1], "group_b": [2,3]})
    delivered, _ = net.send(nodes[0], nodes[2], msg)
    assert not delivered