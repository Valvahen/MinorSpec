def test_baseline_finalizes_all_blocks():
    """SplitBFT with 0% Byzantine, no drops → 100% finalization"""
    config = {"n_nodes": 10, "byzantine_fraction": 0.0, "packet_drop": 0.0,
              "chain_length": 20}
    result = run(SplitBFT, config, seed=42)
    assert result.blocks_finalized == 20
    assert result.safety_violations == 0

def test_aqa_finalizes_with_low_byzantine():
    """AQA-SplitBFT with 10% Byzantine → still finalizes >95%"""
    config = {"n_nodes": 30, "byzantine_fraction": 0.1, "packet_drop": 0.05,
              "chain_length": 50}
    result = run(AQASplitBFT, config, seed=42)
    assert result.blocks_finalized >= 47  # 95% of 50

def test_aqa_downweights_byzantine():
    """After 50 rounds, Byzantine nodes should have lower trust than honest"""
    result = run(AQASplitBFT, {"n_nodes": 20, "byzantine_fraction": 0.2}, seed=42)
    honest_trust = np.mean([n.trust_estimate for n in result.nodes if n.behavior_type == "honest"])
    byz_trust = np.mean([n.trust_estimate for n in result.nodes if n.behavior_type != "honest"])
    assert honest_trust > byz_trust + 0.2  # meaningful separation

def test_aqa_uses_smaller_quorum_when_trust_high():
    """With all-honest network, AQA should shrink quorum below max"""
    result = run(AQASplitBFT, {"n_nodes": 20, "byzantine_fraction": 0.0}, seed=42)
    assert result.avg_quorum_size < result.config["Q_max"]

def test_protocol_survives_partition():
    """Introduce partition mid-run; protocol should recover after healing"""
    config = {"n_nodes": 20, "partition_rounds": (10, 20)}
    result = run(AQASplitBFT, config, seed=42)
    assert result.blocks_finalized > 10  # some progress despite partition