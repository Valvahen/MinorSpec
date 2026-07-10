"""Run each configuration 3 times with the same seed.
Results must be byte-identical or the sim has hidden nondeterminism."""

for config in configurations:
    results = [run_full(config, seed=42) for _ in range(3)]
    assert results[0] == results[1] == results[2], f"Non-deterministic: {config}"
