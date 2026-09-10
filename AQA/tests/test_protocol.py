def test_quorum_size_never_below_2f_plus_1():
    """This is THE safety invariant. If this fails, your paper is wrong."""
    rng = np.random.default_rng(42)
    nodes = load_nodes("trust_profiles.csv")
    protocol = AQASplitBFT(nodes, network, rng, config={"f": 3, "Q_min": 5, "Q_max": 10})
    
    for round_no in range(100):
        result = protocol.run_round(round_no)
        assert result.quorum_size >= 2 * 3 + 1, f"Safety violated at round {round_no}"

def test_no_double_finalization():
    """Same block number should never be finalized twice"""
    finalized_blocks = set()
    for round_no in range(50):
        result = protocol.run_round(round_no)
        if result.finalized:
            assert result.block_number not in finalized_blocks
            finalized_blocks.add(result.block_number)

def test_message_counter_matches_manual_count():
    """Manual walkthrough: 3 groups × (1 pre-prepare + Q prepare + Q commit) + inter-group"""
    # Set up known scenario, count by hand, assert protocol matches
    ...

def test_seeded_run_is_reproducible():
    """Same seed → identical results"""
    r1 = run_full_experiment(seed=42)
    r2 = run_full_experiment(seed=42)
    assert r1.tps == r2.tps
    assert r1.total_messages == r2.total_messages
    assert r1.byzantine_success_count == r2.byzantine_success_count