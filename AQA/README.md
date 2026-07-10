# AQA-Sim

AQA-Sim is a Python discrete-event simulation project for evaluating an adaptive quorum BFT protocol against a static SplitBFT baseline.

## Project Layout

- `aqa_sim/simulator/`: simulation engine modules.
- `aqa_sim/analysis/`: analysis and post-processing code.
- `aqa_sim/results/`: generated experiment outputs.
- `aqa_sim/tests/`: test suite.
- `generate_profiles.py`: trust profile CSV generator.

## Requirements

- Python 3.10+
- Dependencies in `requirements.txt`

Install dependencies:

```bash
pip install -r requirements.txt
```

## Generate Trust Profiles

Default output (`trust_profiles.csv`) with 100 nodes:

```bash
python generate_profiles.py
```

Generate a specific profile with a custom seed and node count:

```bash
python generate_profiles.py --profile 20pct_byz --nodes 250 --seed 123 --output trust_profiles.csv
```

Supported `--profile` values:

- `uniform`
- `bimodal`
- `10pct_byz`
- `20pct_byz`
- `30pct_byz`

Generated CSV columns:

- `node_id`
- `ground_truth_trust`
- `behavior_type`
- `availability_prob`
- `base_latency_ms`
