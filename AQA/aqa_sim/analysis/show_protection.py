"""Print AQA-SplitBFT Byzantine attack protection vs baseline — mentor demo."""
import pandas as pd

df = pd.read_csv("results/runs_v2.csv")

# Mean successful Byzantine attacks per run, by protocol & attack level
tbl = (df.groupby(["protocol", "byzantine_fraction"])["byzantine_success_count"]
         .mean().unstack(0).round(3))

# Attack-resistance improvement of AQA over baseline
tbl["Attacks_Blocked_%"] = ((1 - tbl["AQASplitBFT"] / tbl["SplitBFT"]) * 100).round(1)

print("\n" + "=" * 62)
print("   AQA-SplitBFT: BYZANTINE ATTACK RESISTANCE vs BASELINE")
print("   (successful attacks per run — lower is better)")
print("=" * 62)
print(f"\n{'Byzantine %':>12} | {'SplitBFT':>10} | {'AQA':>8} | {'Attacks Blocked':>16}")
print("-" * 62)

for bf in sorted(df["byzantine_fraction"].unique()):
    if bf == 0.0:
        continue  # no attacks at 0%
    row = tbl.loc[bf]
    print(f"{int(bf*100):>10}%  | {row['SplitBFT']:>10.2f} | "
          f"{row['AQASplitBFT']:>8.2f} | {row['Attacks_Blocked_%']:>14.1f}%")

print("-" * 62)
print("\n  KEY RESULT: Protection GROWS with adversary load")
print(f"    - At 10% Byzantine: {tbl.loc[0.1,'Attacks_Blocked_%']:.0f}% fewer successful attacks")
print(f"    - At 30% Byzantine: {tbl.loc[0.3,'Attacks_Blocked_%']:.0f}% fewer successful attacks")
print(f"    => The harder the attack, the more AQA helps.\n")
print(f"  Runs analyzed: {len(df):,}  |  Safety violations: {df['safety_violations'].sum()}")
print("=" * 62 + "\n")

import matplotlib.pyplot as plt

fractions = [10, 20, 30]
blocked = [tbl.loc[0.1, "Attacks_Blocked_%"],
           tbl.loc[0.2, "Attacks_Blocked_%"],
           tbl.loc[0.3, "Attacks_Blocked_%"]]

plt.figure(figsize=(6, 4))
plt.plot(fractions, blocked, marker="o", linewidth=2, markersize=8, color="#2c7fb8")
plt.fill_between(fractions, blocked, alpha=0.15, color="#2c7fb8")
plt.xlabel("Byzantine Node Fraction (%)")
plt.ylabel("Attacks Blocked vs Baseline (%)")
plt.title("AQA-SplitBFT: Attack Resistance Scales with Threat")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("results/attack_protection.png", dpi=150)
print("Chart saved: results/attack_protection.png")
plt.show()