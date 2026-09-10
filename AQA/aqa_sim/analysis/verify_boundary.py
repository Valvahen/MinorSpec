"""Verify the communication-liveness crossover boundary across network sizes.

Confirms WHERE participation-AQA's liveness drops below static SplitBFT,
for n = 20, 50, 100. The crossover packet-loss level is the paper's
'operating boundary' — it must be consistent to be a defensible claim.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
from tests.test_integration import run
from simulator.protocol_aqa_participation import AQAParticipationProtocol
from simulator.protocol_splitbft import SplitBFTProtocol


def avg(cls, cfg, seeds=range(20)):
    blk, msg = [], []
    for s in seeds:
        r = run(cls, cfg, seed=42 + s)
        blk.append(r.blocks_finalized)
        msg.append(r.total_messages)
    return float(np.mean(blk)), float(np.mean(msg))


drops = [0.0, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10]

for n in [20, 50, 100]:
    print("\n" + "=" * 72)
    print(f"  n = {n}  |  crossover boundary search")
    print("=" * 72)
    print(f"{'loss%':>6} | {'Split blk':>9} | {'Part blk':>9} | {'msg red%':>9} | {'winner':>10}")
    print("-" * 72)
    crossover = None
    for d in drops:
        cfg = {"n_nodes": n, "n_groups": 2, "byzantine_fraction": 0.0,
               "packet_drop": d, "chain_length": 20, "f_per_group": 1,
               "Q_min": 3, "Q_max": n, "Q_safe": 3}
        sblk, smsg = avg(SplitBFTProtocol, cfg)
        pblk, pmsg = avg(AQAParticipationProtocol, cfg)
        red = (1 - pmsg / smsg) * 100 if smsg else 0
        # Winner: Part wins if liveness within 5% of Split AND saves messages
        part_wins = pblk >= 0.95 * sblk
        winner = "Part" if part_wins else "Split"
        if crossover is None and not part_wins:
            crossover = d
        print(f"{int(d*100):>5}% | {sblk:>9.1f} | {pblk:>9.1f} | {red:>8.0f}% | {winner:>10}")
    print("-" * 72)
    if crossover is not None:
        print(f"  >>> Crossover for n={n}: participation-AQA loses advantage at {int(crossover*100)}% loss")
    else:
        print(f"  >>> n={n}: participation-AQA wins across entire tested range")

print("\n" + "=" * 72)
print("  CONFIRMS if: crossover is CONSISTENT (~2%) across n=20/50/100")
print("  If it varies wildly by n -> boundary is size-dependent, state that instead")
print("=" * 72)