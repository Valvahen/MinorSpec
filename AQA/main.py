"""AQA-Sim experiment matrix runner (uses the test-validated run() path)."""
from __future__ import annotations

import csv
import itertools
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from simulator.protocol_splitbft import SplitBFTProtocol
from simulator.protocol_aqa import AQASplitBFTProtocol
from tests.test_integration import run   # proven, 37-test-validated path

try:
    from tqdm import tqdm
    _HAS_TQDM = True
except ImportError:
    _HAS_TQDM = False


# ====================  EDIT THE EXPERIMENT HERE  ====================
MATRIX = {
    "protocol":            ["SplitBFT", "AQASplitBFT"],
    "n_nodes":             [10, 20, 30, 50, 100],
    "n_groups":            [2, 4],          # bigger groups = visible adaptation
    "byzantine_fraction":  [0.0, 0.10, 0.20, 0.30],
    "packet_drop":         [0.0, 0.05, 0.10],
}

FIXED = {
    "chain_length": 50,
    "f_per_group": 1,
    "Q_min": 3,
    "Q_max": 15,        # ceiling; clamped to group size internally
    "Q_safe": 3,
    "partition_rounds": None,
    "churn_p_leave": 0.0,
    "churn_p_join": 0.0,
    "base_latency_ms": 50,
}

N_REPEATS = 30
BASE_SEED = 20260709
MIN_GROUP_SIZE = 3
# ===================================================================

PROTOCOL_CLASSES = {
    "SplitBFT": SplitBFTProtocol,
    "AQASplitBFT": AQASplitBFTProtocol,
}

CSV_FIELDS = [
    "run_id", "protocol", "seed", "repeat",
    "n_nodes", "n_groups", "group_size", "byzantine_fraction", "packet_drop",
    "chain_length", "f_per_group", "Q_min", "Q_max", "Q_safe",
    "blocks_finalized", "total_messages", "tps",
    "avg_quorum_size", "safety_violations", "byzantine_success_count",
]


def build_jobs():
    keys = list(MATRIX.keys())
    for combo in itertools.product(*(MATRIX[k] for k in keys)):
        cell = dict(zip(keys, combo))
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


def main(output_path: str = "results/runs_v2.csv") -> None:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    jobs = list(build_jobs())
    total = len(jobs)
    n_split = sum(1 for p, *_ in jobs if p == "SplitBFT")
    print(f"Planned runs: {total}  ({n_split} SplitBFT, {total - n_split} AQA)")
    print(f"Writing to: {out.resolve()}")

    start = time.time()
    it = tqdm(jobs, desc="Running") if _HAS_TQDM else jobs

    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for i, (proto, seed, repeat, gsize, cfg) in enumerate(it):
            try:
                r = run(PROTOCOL_CLASSES[proto], cfg, seed=seed)
            except Exception as exc:
                print(f"\n[WARN] {proto} seed={seed} failed: {exc}")
                continue
            writer.writerow({
                "run_id": f"{proto}_{seed}_{cfg['n_nodes']}n_{cfg['n_groups']}g_{cfg['byzantine_fraction']}b",
                "protocol": proto, "seed": seed, "repeat": repeat,
                "n_nodes": cfg["n_nodes"], "n_groups": cfg["n_groups"], "group_size": gsize,
                "byzantine_fraction": cfg["byzantine_fraction"], "packet_drop": cfg["packet_drop"],
                "chain_length": cfg["chain_length"], "f_per_group": cfg["f_per_group"],
                "Q_min": cfg["Q_min"], "Q_max": cfg["Q_max"], "Q_safe": cfg["Q_safe"],
                "blocks_finalized": r.blocks_finalized,
                "total_messages": r.total_messages,
                "tps": round(r.tps, 6),
                "avg_quorum_size": round(r.avg_quorum_size, 4),   # keeps the float signal!
                "safety_violations": r.safety_violations,
                "byzantine_success_count": r.byzantine_success_count,
            })
            if (i + 1) % 200 == 0:
                f.flush()

    elapsed = time.time() - start
    print(f"\nDONE. {total} runs in {elapsed:.0f}s ({elapsed/max(total,1)*1000:.1f} ms/run)")
    print(f"Results: {out.resolve()}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/runs_v2.csv")