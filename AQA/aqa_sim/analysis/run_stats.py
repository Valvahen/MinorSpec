"""Statistical validation of AQA-SplitBFT attack resistance vs baseline."""
from __future__ import annotations

import sys
import numpy as np
import pandas as pd
from scipy.stats import wilcoxon


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    """Cliff's delta effect size. Negative => a smaller than b (AQA fewer attacks)."""
    a = np.asarray(a); b = np.asarray(b)
    n_greater = sum((x > b).sum() for x in a)
    n_less = sum((x < b).sum() for x in a)
    return (n_greater - n_less) / (len(a) * len(b))


def interpret_delta(d: float) -> str:
    ad = abs(d)
    if ad < 0.147: return "negligible"
    if ad < 0.33:  return "small"
    if ad < 0.474: return "medium"
    return "large"


def ci95(x: np.ndarray) -> tuple[float, float]:
    x = np.asarray(x, dtype=float)
    m = x.mean()
    se = x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0
    return m - 1.96 * se, m + 1.96 * se


def main(csv_path: str = "results/runs_v2.csv") -> None:
    df = pd.read_csv(csv_path)

    print("=" * 78)
    print("  STATISTICAL VALIDATION: AQA-SplitBFT Byzantine Attack Resistance")
    print("=" * 78)
    print(f"  Dataset: {csv_path}  |  Total runs: {len(df):,}")
    print(f"  Safety violations (all runs): {df['safety_violations'].sum()}")
    print("=" * 78)

    metric = "byzantine_success_count"
    byz_levels = sorted(f for f in df["byzantine_fraction"].unique() if f > 0)
    keys = ["n_nodes", "n_groups", "packet_drop", "seed"]

    print(f"\n{'Byz%':>5} | {'SplitBFT mean [95% CI]':>28} | {'AQA mean [95% CI]':>28}")
    print("-" * 78)

    results = []
    for bf in byz_levels:
        sub = df[df["byzantine_fraction"] == bf]
        split = sub[sub["protocol"] == "SplitBFT"].set_index(keys)[metric]
        aqa = sub[sub["protocol"] == "AQASplitBFT"].set_index(keys)[metric]

        common = split.index.intersection(aqa.index)
        s = split.loc[common].sort_index().values
        a = aqa.loc[common].sort_index().values

        s_lo, s_hi = ci95(s)
        a_lo, a_hi = ci95(a)
        reduction = (1 - a.mean() / s.mean()) * 100 if s.mean() > 0 else 0.0

        try:
            if np.allclose(s, a):
                pval = 1.0
            else:
                _, pval = wilcoxon(s, a, alternative="greater")
        except ValueError:
            pval = 1.0

        delta = cliffs_delta(a, s)
        results.append((bf, s.mean(), a.mean(), reduction, pval, delta, len(common)))

        split_str = f"{s.mean():.3f} [{s_lo:.2f}, {s_hi:.2f}]"
        aqa_str = f"{a.mean():.3f} [{a_lo:.2f}, {a_hi:.2f}]"
        print(f"{int(bf*100):>4}% | {split_str:>28} | {aqa_str:>28}")

    print("\n" + "=" * 78)
    print("  SIGNIFICANCE OF ATTACK REDUCTION (AQA vs SplitBFT)")
    print("=" * 78)
    print(f"\n{'Byz%':>5} | {'Reduction':>10} | {'p-value':>10} | {'Significant?':>12} | {'Effect size':>20}")
    print("-" * 78)

    for bf, sm, am, red, p, d, n in results:
        sig = "YES ***" if p < 0.001 else "YES **" if p < 0.01 else "YES *" if p < 0.05 else "no"
        eff = f"{interpret_delta(d)} ({d:+.3f})"
        print(f"{int(bf*100):>4}% | {red:>8.1f}% | {p:>10.4g} | {sig:>12} | {eff:>20}")

    print("-" * 78)
    print("  * p<0.05   ** p<0.01   *** p<0.001   |   paired Wilcoxon (H1: SplitBFT > AQA)")
    print(f"  Pairs per level: {[r[6] for r in results]}")

    print("\n" + "=" * 78)
    print("  VERDICT")
    print("=" * 78)
    sig_levels = [f"{int(r[0]*100)}%" for r in results if r[4] < 0.05]
    if sig_levels:
        print(f"  Attack reduction is STATISTICALLY SIGNIFICANT at: {', '.join(sig_levels)}")
        print("  => The attack-resistance headline is defensible. Build the paper on it.")
    else:
        print("  Attack reduction is NOT significant at any level.")
        print("  => Do NOT headline attack-resistance. Reconsider framing.")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/runs_v2.csv")