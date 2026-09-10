"""Decisive test: does TRUST-based selection beat RANDOM selection?

If participation-AQA's ~48% saving comes purely from 'fewer participants',
then RANDOM subset selection should match it — and trust is incidental.
If trust genuinely helps, it should show better SAFETY (fewer byzantine
successes) and/or better LIVENESS, especially under attack, because it
avoids selecting known-bad nodes.
"""
import sys
sys.path.insert(0, ".")
import numpy as np

from tests.test_integration import run
from simulator.protocol_splitbft import SplitBFTProtocol
from simulator.protocol_aqa_participation import AQAParticipationProtocol
from simulator.node import Node


# --- Build a RANDOM-selection variant by subclassing participation-AQA ---
# It picks the subset uniformly at random instead of by trust.
from simulator.protocol_aqa_participation import AQAParticipationProtocol as _Base


class RandomParticipationProtocol(_Base):
    """Same participation reduction, but subset chosen RANDOMLY (trust ignored)."""

    def _select_trusted_subset(self, online, k):
        if k >= len(online) or k <= 0:
            return list(online)
        idx = self.rng.choice(len(online), size=k, replace=False)
        return [online[int(i)] for i in idx]


PROTOS = {
    "SplitBFT":         SplitBFTProtocol,
    "Part-AQA (trust)": AQAParticipationProtocol,
    "Part-AQA (random)": RandomParticipationProtocol,
}


def avg(cls, cfg, seeds=range(20)):
    blk, msg, byz = [], [], []
    for s in seeds:
        r = run(cls, cfg, seed=42 + s)
        blk.append(r.blocks_finalized)
        msg.append(r.total_messages)
        byz.append(r.byzantine_success_count)
    return np.mean(blk), np.mean(msg), np.mean(byz)


def scenario(title, cfg):
    print("\n" + "=" * 74)
    print("  " + title)
    print("=" * 74)
    print(f"{'protocol':>20} | {'blocks':>8} | {'messages':>10} | {'byz_succ':>9}")
    print("-" * 74)
    for name, cls in PROTOS.items():
        b, m, z = avg(cls, cfg)
        print(f"{name:>20} | {b:>8.1f} | {m:>10.0f} | {z:>9.2f}")


BASE = {"n_nodes": 50, "n_groups": 2, "f_per_group": 1,
        "Q_min": 3, "Q_max": 50, "Q_safe": 3, "chain_length": 20,
        "churn_p_leave": 0.0, "churn_p_join": 0.0}


def cfg(**o):
    c = dict(BASE); c.update(o); return c


# The decisive scenario: UNDER ATTACK. Trust should shine here by
# excluding known-bad nodes; random selection should let more attacks through.
scenario("TEST A: 20% Byzantine, no loss (does trust avoid bad nodes?)",
         cfg(byzantine_fraction=0.20, packet_drop=0.0))

scenario("TEST B: 30% Byzantine, no loss (stronger attack)",
         cfg(byzantine_fraction=0.30, packet_drop=0.0))

scenario("TEST C: Benign, no loss (is the 48% saving trust-dependent?)",
         cfg(byzantine_fraction=0.0, packet_drop=0.0))

print("\n" + "=" * 74)
print("  VERDICT LOGIC:")
print("  - If trust << random on byz_succ (TEST A/B) -> TRUST IS REAL (safety win)")
print("  - If trust == random on everything          -> trust incidental (honest)")
print("  - TEST C should show both saving ~48% msgs  -> saving is from participation")
print("=" * 74)