# AQA-SplitBFT: Trust-Adaptive Participation Simulator

A rigorously-tested discrete-event simulator for evaluating trust-adaptive
Byzantine Fault-Tolerant (BFT) consensus in fog-based blockchain environments.
This directory contains the complete implementation, test suite, experiments,
and analysis accompanying the paper:

> *Trust-Adaptive Participation in Fog-Based SplitBFT: A Communication–Liveness Trade-off Study.*

All results reported in the paper are reproducible from the scripts here.

---

## Overview

The simulator compares three consensus variants under controlled fog-network
conditions (variable size, adversarial load, and packet loss):

| Variant | Description |
|---|---|
| **SplitBFT** | Static baseline with fixed group quorums (`simulator/protocol_splitbft.py`) |
| **AQA (threshold)** | Trust-adaptive quorum threshold (`simulator/protocol_aqa.py`) |
| **Participation-AQA** | Trust-selected participant subset (`simulator/protocol_aqa_participation.py`) |

Node trust is computed from runtime telemetry — uptime, voting agreement,
response time, and observed misbehaviour — not assigned randomly.

---

## Directory structure

```
AQA/
├── simulator/
│   ├── node.py                      # Node model + telemetry-based trust
│   ├── network.py                   # Latency, packet drop, partition, churn
│   ├── adversary.py                 # Byzantine behaviours
│   ├── base_protocol.py             # Shared PBFT-style consensus core
│   ├── protocol_splitbft.py         # Static baseline
│   ├── protocol_aqa.py              # Adaptive quorum-threshold variant
│   ├── protocol_aqa_participation.py# Adaptive participation variant
│   └── metrics.py                   # Metrics + CSV export
├── tests/                           # 37-test validation suite (pytest)
├── analysis/                        # Statistics + figure generation
├── results/                         # Generated CSVs and figures
├── main.py                          # Full experiment-matrix runner
└── requirements.txt
```

---

## Installation

Requires Python 3.10+.

```bash
cd AQA
pip install -r requirements.txt
```

Dependencies: `numpy`, `pandas`, `scipy`, `matplotlib`, `pytest`, `tqdm`.

---

## Reproducing the paper's results

All experiments are seed-controlled and deterministic.

**1. Run the validation test suite (37 tests):**
```bash
pytest -v
```

**2. Reproduce the main message-reduction result (Table 1):**
```bash
python analysis/confirm_reduction.py
```

**3. Reproduce the communication–liveness trade-off (Table 2, Figure 2):**
```bash
python analysis/verify_boundary.py
```

**4. Reproduce the trust-vs-random comparison (Table 3):**
```bash
python analysis/trust_vs_random.py
python analysis/trust_gap_check.py     # Wilcoxon significance test
```

**5. Generate publication figures:**
```bash
python analysis/make_figures.py        # outputs to results/figures/
```

**6. (Optional) Run the full experiment matrix:**
```bash
python main.py results/runs.csv
```

---

## Validation

The simulator is validated by 37 automated tests covering:

- **Trust model** — bounds, sliding-window behaviour, telemetry aggregation
- **Network model** — latency floors, drop-rate accuracy, partitions, churn
- **Adversaries** — crash, equivocation, dishonest trust reporting, slow-response
- **Protocol safety** — quorum never below 2f+1, no double finalisation
- **Message accounting** — verified against manual counts and O(n²) scaling
- **Reproducibility** — identical output under identical seeds

Run `pytest -v` to execute the full suite.

---

## Key findings (summary)

1. Adapting the **quorum threshold** yields no benefit — a 2f+1 quorum already
   saturates Byzantine tolerance.
2. Adapting **participation** reduces communication by ~48% while preserving
   safety and liveness in near-stable networks.
3. **Trust-based** selection reduces adversarial overhead by a further ~10%
   versus random selection (Wilcoxon, p < 10⁻⁹).
4. The benefit is **fragile**: liveness collapses beyond ~1–2% packet loss.

---

## Notes

- This `AQA/` directory contains the current, paper-accurate implementation.
  Earlier exploratory code elsewhere in the repository is superseded by this work.
- Latency is modelled as communication volume; wall-clock latency analysis on a
  physical deployment is left to future work.

---

## Citation

If you use this simulator, please cite the accompanying paper (details to be
added upon publication).
```