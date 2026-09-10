"""Sensitivity analysis: does the 48% reduction depend on trust weight choices?

Reviewer 2 asked whether the weights (0.35, 0.30, 0.20, 0.15) are arbitrary.
We re-run the headline comparison under several alternative weightings.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
from tests.test_integration import run
from simulator.protocol_aqa_participation import AQAParticipationProtocol
from simulator.protocol_splitbft import SplitBFTProtocol
import simulator.node as node_mod

# Weight schemes: (uptime, voting, rtt, honesty)
SCHEMES = {
    "Paper (0.35/0.30/0.20/0.15)": (0.35, 0.30, 0.20, 0.15),
    "Equal (0.25 each)":           (0.25, 0.25, 0.25, 0.25),
    "Uptime-heavy":                (0.55, 0.20, 0.15, 0.10),
    "Voting-heavy":                (0.20, 0.55, 0.15, 0.10),
    "Honesty-heavy":               (0.20, 0.20, 0.15, 0.45),
    "RTT-heavy":                   (0.20, 0.20, 0.45, 0.15),
}


def set_weights(w):
    """Patch the module-level weights used by compute_trust_estimate."""
    node_mod.W_UPTIME, node_mod.W_VOTING, node_mod.W_RTT, node_mod.W_HONESTY = w


def avg_reduction(seeds=range(20)):
    reds = []
    for n in [20, 50, 100]:
        cfg = {"n_nodes": n, "n_groups": 2, "byzantine_fraction": 0.0,
               "packet_drop": 0.0, "chain_length": 20, "f_per_group": 1,
               "Q_min": 3, "Q_max": n, "Q_safe": 3}
        for s in seeds:
            p = run(AQAParticipationProtocol, cfg, seed=42 + s)
            b = run(SplitBFTProtocol, cfg, seed=42 + s)
            if b.total_messages:
                reds.append((1 - p.total_messages / b.total_messages) * 100)
    return float(np.mean(reds)), float(np.std(reds))


print("=" * 66)
print("  TRUST-WEIGHT SENSITIVITY: does the ~48% reduction hold?")
print("=" * 66)
print(f"{'weighting scheme':>32} | {'reduction %':>12} | {'std':>6}")
print("-" * 66)

for name, w in SCHEMES.items():
    set_weights(w)
    m, sd = avg_reduction()
    print(f"{name:>32} | {m:>11.1f}% | {sd:>6.2f}")

print("-" * 66)
print("  If reduction is stable across schemes -> result is weight-independent")
print("=" * 66)