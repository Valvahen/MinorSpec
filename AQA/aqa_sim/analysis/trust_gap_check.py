# save as analysis/trust_gap_check.py
import sys; sys.path.insert(0, ".")
import numpy as np
from tests.test_integration import run
from simulator.protocol_aqa_participation import AQAParticipationProtocol
from analysis.trust_vs_random import RandomParticipationProtocol

def msgs(cls, cfg, seeds=range(30)):
    return [run(cls, cfg, seed=42+s).total_messages for s in seeds]

cfg = {"n_nodes":50,"n_groups":2,"byzantine_fraction":0.30,"packet_drop":0.0,
       "chain_length":20,"f_per_group":1,"Q_min":3,"Q_max":50,"Q_safe":3}

t = np.array(msgs(AQAParticipationProtocol, cfg))
r = np.array(msgs(RandomParticipationProtocol, cfg))
from scipy.stats import wilcoxon
_, p = wilcoxon(r, t, alternative="greater")  # H1: random > trust
print(f"Trust msgs: {t.mean():.0f} ± {t.std():.0f}")
print(f"Random msgs: {r.mean():.0f} ± {r.std():.0f}")
print(f"Trust saves {(1-t.mean()/r.mean())*100:.1f}% vs random under attack")
print(f"Wilcoxon p={p:.4g}  ->  {'SIGNIFICANT' if p<0.05 else 'NOT significant (noise)'}")