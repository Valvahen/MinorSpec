"""Verify enough runs for statistical power.
For a 10% effect size at α=0.05, β=0.2, need ~30 runs per config."""

from statsmodels.stats.power import TTestPower
required_n = TTestPower().solve_power(effect_size=0.5, alpha=0.05, power=0.8)
assert n_repeats >= required_n, f"Need at least {int(required_n)} runs"