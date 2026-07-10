# save as analysis/confirm_reduction.py
import sys
sys.path.insert(0, ".")
import numpy as np
from tests.test_integration import run
from simulator.protocol_aqa_participation import AQAParticipationProtocol
from simulator.protocol_splitbft import SplitBFTProtocol


def ci95(x):
    x = np.asarray(x, float)
    m = x.mean()
    se = x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0
    return m, m - 1.96 * se, m + 1.96 * se


print("=" * 72)
print("  MESSAGE REDUCTION: Participation-AQA vs SplitBFT (30 seeds)")
print("=" * 72)
print(f"{'n':>5} | {'reduction% [95% CI]':>26} | {'Part blk':>9} | {'Split blk':>9}")
print("-" * 72)

for n in [20, 50, 100]:
    reductions, pblk, sblk = [], [], []
    for seed in range(30):
        cfg = {"n_nodes": n, "n_groups": 2, "byzantine_fraction": 0.0,
               "packet_drop": 0.0, "chain_length": 20, "f_per_group": 1,
               "Q_min": 3, "Q_max": n, "Q_safe": 3}
        p = run(AQAParticipationProtocol, cfg, seed=42 + seed)
        s = run(SplitBFTProtocol, cfg, seed=42 + seed)
        if s.total_messages > 0:
            reductions.append((1 - p.total_messages / s.total_messages) * 100)
        pblk.append(p.blocks_finalized)
        sblk.append(s.blocks_finalized)
    m, lo, hi = ci95(reductions)
    print(f"{n:>5} | {m:>10.1f}% [{lo:.1f}, {hi:.1f}]{'':>4} | "
          f"{np.mean(pblk):>9.1f} | {np.mean(sblk):>9.1f}")

print("-" * 72)
print("  CONFIRMS if: reduction ~48% with TIGHT CI, and Part blk == Split blk")
print("=" * 72)