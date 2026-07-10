def test_crash_drops_all():
    node = Node(id=0, behavior_type="crash", ...)
    for _ in range(100):
        result = apply_behavior(node, msg, rng)
        assert result is None

def test_equivocator_sends_conflicting():
    node = Node(id=0, behavior_type="equivocate", ...)
    msgs = apply_behavior(node, msg, rng)  # returns list of 2
    assert len(msgs) == 2
    assert msgs[0].vote != msgs[1].vote

def test_lie_trust_returns_high():
    node = Node(id=0, behavior_type="lie_trust", ground_truth_trust=0.1, ...)
    reported = get_reported_trust(node)  # what protocol sees
    assert reported > 0.9