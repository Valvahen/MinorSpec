"""
AQA-Sim experiment matrix runner.

Runs a full factorial of (protocol × n_nodes × n_groups × byzantine_fraction ×
packet_drop) with N repeats each, writing one CSV row per run.

Reuses the proven run() helper from tests.test_integration so the experiment
path is identical to the one validated by the 37-test suite.
"""
from __future__ import annotations

import csv
import itertools
import sys
import time
from pathlib import Path

# Make 'simulator' and 'tests' importable regardless of CWD
sys.path.insert(0, str(Path(__file__).parent))

from simulator.protocol_splitbft import SplitBFTProtocol
from simulator.protocol_aqa import AQASplitBFTProtocol
from tests.test_integration import run  # proven, test-validated run() helper

# Optional progress bar
try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False


# ----------------------------------------------------------------------
# EXPERIMENT MATRIX — edit here to change scope
# ----------------------------------------------------------------------

MATRIX = {
    "protocol":            ["SplitBFT", "AQASplitBFT"],
    "n_nodes":             [10, 20, 30, 50, 100],
    "n_groups":            [2, 4, 5, 10],
    "byzantine_fraction":  [0.0, 0.10, 0.20, 0.30],
    "packet_drop":         [0.0, 0.05, 0.10],
}

FIXED = {
    "chain_length": 50,
    "f_per_group": 1,
    "Q_min": 3,
    "Q_max": 7,
    "Q_safe": 3,
    "partition_rounds": None,
    "churn_p_leave": 0.0,
    "churn_p_join": 0.0,
    "base_latency_ms": 50,
}

N_REPEATS = 30
BASE_SEED = 20260708
MIN_GROUP_SIZE = 3   # skip configs where n_nodes / n_groups < 3

PROTOCOL_CLASSES = {
    "SplitBFT": SplitBFTProtocol,
    "AQASplitBFT": AQASplitBFTProtocol,
}


# ----------------------------------------------------------------------
# CSV columns
# ----------------------------------------------------------------------

CSV_FIELDS = [
    "run_id", "protocol", "seed", "repeat",
    "n_nodes", "n_groups", "group_size", "byzantine_fraction", "packet_drop",
    "chain_length", "f_per_group", "Q_min", "Q_max", "Q_safe",
    "blocks_finalized", "total_messages", "tps",
    "avg_quorum_size", "safety_violations", "byzantine_success_count",
]


def build_configs():
    """Yield (protocol_name, cfg dict) for every valid matrix cell × repeat."""
    keys = list(MATRIX.keys())
    for combo in itertools.product(*(MATRIX[k] for k in keys)):
        cell = dict(zip(keys, combo))

        # Skip invalid group sizes
        group_size = cell["n_nodes"] // cell["n_groups"]
        if group_size < MIN_GROUP_SIZE:
            continue

        for repeat in range(N_REPEATS):
            seed = BASE_SEED + repeat
            cfg = dict(FIXED)
            cfg.update({
                "n_nodes": cell["n_nodes"],
                "n_groups": cell["n_groups"],
                "byzantine_fraction": cell["byzantine_fraction"],
                "packet_drop": cell["packet_drop"],
            })
            yield cell["protocol"], seed, repeat, group_size, cfg


def main(output_path: str = "results/runs.csv") -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    all_jobs = list(build_configs())
    total = len(all_jobs)
    print(f"Planned runs: {total}  "
          f"({len([1 for p,_,_,_,_ in all_jobs if p=='SplitBFT'])} SplitBFT, "
          f"{len([1 for p,_,_,_,_ in all_jobs if p=='AQASplitBFT'])} AQA)")
    print(f"Writing to: {out.resolve()}")

    start = time.time()
    iterator = tqdm(all_jobs, desc="Running") if _HAS_TQDM else all_jobs

    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for i, (proto_name, seed, repeat, group_size, cfg) in enumerate(iterator):
            proto_cls = PROTOCOL_CLASSES[proto_name]
            try:
                result = run(proto_cls, cfg, seed=seed)
            except Exception as exc:
                print(f"\n[WARN] run failed: {proto_name} seed={seed} "
                      f"cfg={cfg} -> {exc}")
                continue

            writer.writerow({
                "run_id": f"{proto_name}_{seed}_{cfg['n_nodes']}n_{cfg['n_groups']}g",
                "protocol": proto_name,
                "seed": seed,
                "repeat": repeat,
                "n_nodes": cfg["n_nodes"],
                "n_groups": cfg["n_groups"],
                "group_size": group_size,
                "byzantine_fraction": cfg["byzantine_fraction"],
                "packet_drop": cfg["packet_drop"],
                "chain_length": cfg["chain_length"],
                "f_per_group": cfg["f_per_group"],
                "Q_min": cfg["Q_min"],
                "Q_max": cfg["Q_max"],
                "Q_safe": cfg["Q_safe"],
                "blocks_finalized": result.blocks_finalized,
                "total_messages": result.total_messages,
                "tps": round(result.tps, 6),
                "avg_quorum_size": round(result.avg_quorum_size, 4),
                "safety_violations": result.safety_violations,
                "byzantine_success_count": result.byzantine_success_count,
            })

            # Flush periodically so a crash doesn't lose everything
            if (i + 1) % 200 == 0:
                f.flush()
            if not _HAS_TQDM and (i + 1) % 500 == 0:
                elapsed = time.time() - start
                print(f"  {i+1}/{total} done ({elapsed:.0f}s)")

    elapsed = time.time() - start
    print(f"\nDONE. {total} runs in {elapsed:.0f}s "
          f"({elapsed/max(total,1)*1000:.1f} ms/run)")
    print(f"Results: {out.resolve()}")


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "results/runs.csv"
    main(output)