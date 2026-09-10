"""Hunt for a genuine, honest AQA advantage across unmeasured dimensions."""
from __future__ import annotations
import sys
sys.path.insert(0, ".")

import numpy as np
from tests.test_integration import run
from simulator.protocol_aqa import AQASplitBFTProtocol
from simulator.protocol_splitbft import SplitBFTProtocol


def avg_over_seeds(proto, cfg, seeds=range(10)):
    """Run a config over several seeds, return averaged metrics."""
    blocks, msgs, lat, q, byz, sep = [], [], [], [], [], []
    for s in seeds:
        r = run(proto, cfg, seed=42 + s)
        blocks.append(r.blocks_finalized)
        msgs.append(r.total_messages)
        lat.append(float(getattr(r, "avg_consensus_latency_ms", 0.0) or 0.0))
        q.append(r.avg_quorum_size)
        byz.append(r.byzantine_success_count)
        honest = [n.trust_estimate for n in r.nodes if n.behavior_type == "honest"]
        bad = [n.trust_estimate for n in r.nodes if n.behavior_type != "honest"]
        if honest and bad:
            sep.append(np.mean(honest) - np.mean(bad))
        else:
            sep.append(np.nan)
    return {
        "blocks": float(np.mean(blocks)),
        "msgs": float(np.mean(msgs)),
        "latency": float(np.mean(lat)),
        "quorum": float(np.mean(q)),
        "byz": float(np.mean(byz)),
        "trust_sep": float(np.nanmean(sep)),
    }


def compare(title, cfg):
    print("\n" + "=" * 70)
    print("  " + title)
    print("=" * 70)
    a = avg_over_seeds(AQASplitBFTProtocol, cfg)
    s = avg_over_seeds(SplitBFTProtocol, cfg)
    header = f"{'metric':>12} | {'AQA':>10} | {'SplitBFT':>10} | {'diff':>10}"
    print(header)
    print("-" * len(header))
    for k in ["blocks", "msgs", "latency", "quorum", "byz", "trust_sep"]:
        av = a[k]
        sv = s[k]
        diff = av - sv
        print(f"{k:>12} | {av:>10.2f} | {sv:>10.2f} | {diff:>+10.2f}")


# --- TEST 1: Latency in benign conditions ---
compare(
    "TEST 1: Benign latency (big group, high trust -> small AQA quorum)",
    {"n_nodes": 50, "n_groups": 2, "byzantine_fraction": 0.0,
     "packet_drop": 0.0, "chain_length": 30, "f_per_group": 1,
     "Q_min": 3, "Q_max": 25, "Q_safe": 3},
)

# --- TEST 2: Latency under packet loss ---
compare(
    "TEST 2: Latency under packet loss",
    {"n_nodes": 50, "n_groups": 2, "byzantine_fraction": 0.0,
     "packet_drop": 0.10, "chain_length": 30, "f_per_group": 1,
     "Q_min": 3, "Q_max": 25, "Q_safe": 3},
)

# --- TEST 3: Churn resilience ---
compare(
    "TEST 3: Churn resilience (nodes leave/join each round)",
    {"n_nodes": 30, "n_groups": 3, "byzantine_fraction": 0.1,
     "packet_drop": 0.05, "chain_length": 30, "f_per_group": 1,
     "Q_min": 3, "Q_max": 10, "Q_safe": 3,
     "churn_p_leave": 0.1, "churn_p_join": 0.3},
)

# --- TEST 4: Trust observability (AQA-only capability) ---
compare(
    "TEST 4: Byzantine identification (trust separation, higher=better)",
    {"n_nodes": 30, "n_groups": 3, "byzantine_fraction": 0.3,
     "packet_drop": 0.0, "chain_length": 50, "f_per_group": 1,
     "Q_min": 3, "Q_max": 10, "Q_safe": 3},
)

print("\n" + "=" * 70)
print("  HOW TO READ THIS:")
print("  - latency:   NEGATIVE diff = AQA faster  (a WIN)")
print("  - blocks:    POSITIVE diff = AQA finalizes more  (a WIN)")
print("  - trust_sep: AQA should be > 0 (separates good/bad); Split ~0 (blind)")
print("=" * 70)