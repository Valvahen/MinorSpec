"""Characterize the participation-vs-liveness trade-off in trust-adaptive BFT.

Compares three protocols across packet-loss and churn:
  - SplitBFT            (static baseline)
  - AQA-Threshold       (all vote; quorum threshold)
  - AQA-Participation   (trust-selected subset participates)

Measures MESSAGES (efficiency) and BLOCKS FINALIZED (liveness) so the
trade-off is explicit.
"""
from __future__ import annotations
import sys
sys.path.insert(0, ".")

import numpy as np
from tests.test_integration import run
from simulator.protocol_splitbft import SplitBFTProtocol
from simulator.protocol_aqa import AQASplitBFTProtocol
from simulator.protocol_aqa_participation import AQAParticipationProtocol

PROTOS = {
    "SplitBFT":          SplitBFTProtocol,
    "AQA-Threshold":     AQASplitBFTProtocol,
    "AQA-Participation": AQAParticipationProtocol,
}


def avg(proto_cls, cfg, seeds=range(15)):
    blocks, msgs, byz, part = [], [], [], []
    for s in seeds:
        r = run(proto_cls, cfg, seed=42 + s)
        blocks.append(r.blocks_finalized)
        msgs.append(r.total_messages)
        byz.append(r.byzantine_success_count)
        part.append(r.avg_quorum_size)
    return {
        "blocks": float(np.mean(blocks)),
        "msgs": float(np.mean(msgs)),
        "byz": float(np.mean(byz)),
        "part": float(np.mean(part)),
    }


def scenario(title, base_cfg):
    print("\n" + "=" * 76)
    print("  " + title)
    print("=" * 76)
    hdr = f"{'protocol':>20} | {'blocks':>8} | {'messages':>10} | {'byz_succ':>8} | {'part/Q':>7}"
    print(hdr)
    print("-" * len(hdr))
    ref_msgs = None
    for name, cls in PROTOS.items():
        m = avg(cls, base_cfg)
        if name == "SplitBFT":
            ref_msgs = m["msgs"]
        msg_delta = ""
        if ref_msgs and name != "SplitBFT":
            pct = (1 - m["msgs"] / ref_msgs) * 100
            msg_delta = f" ({pct:+.0f}%)"
        print(f"{name:>20} | {m['blocks']:>8.1f} | {m['msgs']:>10.0f}{msg_delta:>8} "
              f"| {m['byz']:>8.2f} | {m['part']:>7.1f}")


BASE = {
    "n_nodes": 50, "n_groups": 2, "f_per_group": 1,
    "Q_min": 3, "Q_max": 25, "Q_safe": 3, "chain_length": 30,
    "byzantine_fraction": 0.0, "packet_drop": 0.0,
    "churn_p_leave": 0.0, "churn_p_join": 0.0,
}


def cfg(**over):
    c = dict(BASE); c.update(over); return c


# 1) Ideal conditions — does participation-AQA save messages?
scenario("SCENARIO 1: Benign, no loss (efficiency test)",
         cfg(byzantine_fraction=0.0, packet_drop=0.0))

# 2) Packet loss — does participation-AQA lose liveness?
scenario("SCENARIO 2: 10% packet loss (liveness stress)",
         cfg(byzantine_fraction=0.0, packet_drop=0.10))

# 3) Churn — realistic fog
scenario("SCENARIO 3: Churn (nodes leave/join)",
         cfg(byzantine_fraction=0.0, packet_drop=0.05,
             churn_p_leave=0.1, churn_p_join=0.3))

# 4) Under attack — does anyone lose safety?
scenario("SCENARIO 4: 30% Byzantine (safety test)",
         cfg(byzantine_fraction=0.30, packet_drop=0.0))

print("\n" + "=" * 76)
print("  READING THE TRADE-OFF:")
print("  - AQA-Participation SHOULD show fewer messages in Scenario 1 (benign)")
print("  - AQA-Participation MAY show fewer blocks in Scenarios 2/3 (liveness cost)")
print("  - ALL should show byz_succ near 0 in Scenario 4 (safety preserved)")
print("  => If so, you have a REAL, honest participation-vs-liveness trade-off.")
print("=" * 76)