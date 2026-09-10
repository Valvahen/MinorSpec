"""Publication-quality plotting utilities for AQA-Sim results."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


PROTOCOL_ORDER: tuple[str, ...] = ("SplitBFT", "AQA-SplitBFT")
MARKERS: dict[str, str] = {"SplitBFT": "o", "AQA-SplitBFT": "s"}
COLORS: dict[str, str] = {"SplitBFT": "#1b5e20", "AQA-SplitBFT": "#c62828"}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for plotting."""
    parser = argparse.ArgumentParser(description="Generate AQA-Sim publication figures")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("results/runs.csv"),
        help="Input runs CSV",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("results/figures"),
        help="Output figure directory",
    )
    parser.add_argument(
        "--rmse-rounds",
        type=Path,
        default=Path("results/rmse_rounds.csv"),
        help="Optional per-round RMSE CSV",
    )
    return parser.parse_args()


def normalize_protocol_label(raw_protocol: str) -> str:
    """Normalize protocol labels for consistent legend order and styling."""
    lowered = raw_protocol.strip().lower()
    if lowered == "splitbft":
        return "SplitBFT"
    if lowered in {"aqa", "aqa_splitbft", "aqa-splitbft"}:
        return "AQA-SplitBFT"
    return raw_protocol


def confidence_interval_95(values: Iterable[float]) -> tuple[float, float, float]:
    """Return mean and two-sided 95 percent CI bounds using t-distribution."""
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return np.nan, np.nan, np.nan
    mean = float(np.mean(arr))
    if arr.size == 1:
        return mean, mean, mean

    sem = float(stats.sem(arr, ddof=1))
    t_value = float(stats.t.ppf(0.975, df=arr.size - 1))
    margin = t_value * sem
    return mean, mean - margin, mean + margin


def ensure_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize expected config columns from cfg-prefixed variants when needed."""
    data = frame.copy()
    for key in ("n_nodes", "byzantine_fraction", "packet_drop", "n_rounds"):
        prefixed = f"cfg_{key}"
        if key not in data.columns and prefixed in data.columns:
            data[key] = data[prefixed]

    required = {
        "protocol",
        "n_nodes",
        "byzantine_fraction",
        "packet_drop",
        "TPS",
        "total_messages",
        "byzantine_success_count",
        "trust_estimation_rmse",
    }
    missing = required.difference(set(data.columns))
    if missing:
        raise ValueError(f"Missing required columns in runs CSV: {sorted(missing)}")

    data["protocol"] = data["protocol"].astype(str).map(normalize_protocol_label)
    data["n_nodes"] = data["n_nodes"].astype(int)
    data["byzantine_fraction"] = data["byzantine_fraction"].astype(float)
    data["packet_drop"] = data["packet_drop"].astype(float)
    if "n_rounds" in data.columns:
        data["n_rounds"] = data["n_rounds"].astype(int)
    else:
        data["n_rounds"] = 1

    data["byz_success_rate"] = data["byzantine_success_count"] / data["n_rounds"].clip(lower=1)
    return data


def aggregate_ci(data: pd.DataFrame, group_cols: list[str], metric: str) -> pd.DataFrame:
    """Aggregate mean and confidence intervals for a metric over grouping columns."""
    rows: list[dict[str, float | str | int]] = []
    grouped = data.groupby(group_cols, sort=True)
    for keys, group_frame in grouped:
        values = group_frame[metric].astype(float).to_numpy()
        mean, ci_low, ci_high = confidence_interval_95(values)

        row: dict[str, float | str | int] = {
            "mean": float(mean),
            "ci_low": float(ci_low),
            "ci_high": float(ci_high),
        }

        if not isinstance(keys, tuple):
            keys = (keys,)

        for idx, key_name in enumerate(group_cols):
            row[key_name] = keys[idx]
        rows.append(row)

    return pd.DataFrame(rows)


def save_figure(fig: plt.Figure, outdir: Path, stem: str) -> None:
    """Save a figure in both PNG and PDF formats at publication resolution."""
    outdir.mkdir(parents=True, exist_ok=True)
    fig.savefig(outdir / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(outdir / f"{stem}.pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_tps_vs_nodes(data: pd.DataFrame, outdir: Path) -> None:
    """Create TPS versus node-count figure with 95 percent CI error bars."""
    agg = aggregate_ci(data, ["protocol", "n_nodes"], "TPS")
    fig, ax = plt.subplots(figsize=(7.5, 4.8))

    for protocol in PROTOCOL_ORDER:
        subset = agg[agg["protocol"] == protocol].sort_values("n_nodes")
        if subset.empty:
            continue
        yerr = np.vstack(
            [
                subset["mean"].to_numpy() - subset["ci_low"].to_numpy(),
                subset["ci_high"].to_numpy() - subset["mean"].to_numpy(),
            ]
        )
        ax.errorbar(
            subset["n_nodes"],
            subset["mean"],
            yerr=yerr,
            marker=MARKERS.get(protocol, "o"),
            color=COLORS.get(protocol, "#000000"),
            linewidth=1.8,
            capsize=3,
            label=protocol,
        )

    ax.set_xlabel("Number of Nodes")
    ax.set_ylabel("TPS")
    ax.set_title("Throughput vs Network Size")
    ax.grid(alpha=0.25, linestyle="--")
    ax.legend()
    save_figure(fig, outdir, "fig1_tps_vs_n_nodes")


def plot_messages_vs_nodes(data: pd.DataFrame, outdir: Path) -> None:
    """Create total-messages versus node-count figure on log-scaled y-axis."""
    agg = aggregate_ci(data, ["protocol", "n_nodes"], "total_messages")
    fig, ax = plt.subplots(figsize=(7.5, 4.8))

    for protocol in PROTOCOL_ORDER:
        subset = agg[agg["protocol"] == protocol].sort_values("n_nodes")
        if subset.empty:
            continue
        yerr = np.vstack(
            [
                subset["mean"].to_numpy() - subset["ci_low"].to_numpy(),
                subset["ci_high"].to_numpy() - subset["mean"].to_numpy(),
            ]
        )
        ax.errorbar(
            subset["n_nodes"],
            subset["mean"],
            yerr=yerr,
            marker=MARKERS.get(protocol, "o"),
            color=COLORS.get(protocol, "#000000"),
            linewidth=1.8,
            capsize=3,
            label=protocol,
        )

    ax.set_yscale("log")
    ax.set_xlabel("Number of Nodes")
    ax.set_ylabel("Total Messages (log scale)")
    ax.set_title("Communication Cost vs Network Size")
    ax.grid(alpha=0.25, linestyle="--")
    ax.legend()
    save_figure(fig, outdir, "fig2_messages_vs_n_nodes")


def plot_byzantine_success(data: pd.DataFrame, outdir: Path) -> None:
    """Create byzantine success rate versus adversarial fraction figure."""
    agg = aggregate_ci(data, ["protocol", "byzantine_fraction"], "byz_success_rate")
    fig, ax = plt.subplots(figsize=(7.5, 4.8))

    for protocol in PROTOCOL_ORDER:
        subset = agg[agg["protocol"] == protocol].sort_values("byzantine_fraction")
        if subset.empty:
            continue
        yerr = np.vstack(
            [
                subset["mean"].to_numpy() - subset["ci_low"].to_numpy(),
                subset["ci_high"].to_numpy() - subset["mean"].to_numpy(),
            ]
        )
        ax.errorbar(
            subset["byzantine_fraction"],
            subset["mean"],
            yerr=yerr,
            marker=MARKERS.get(protocol, "o"),
            color=COLORS.get(protocol, "#000000"),
            linewidth=1.8,
            capsize=3,
            label=protocol,
        )

    ax.set_xlabel("Byzantine Fraction")
    ax.set_ylabel("Byzantine Success Rate")
    ax.set_title("Safety Resilience vs Byzantine Presence")
    ax.grid(alpha=0.25, linestyle="--")
    ax.legend()
    save_figure(fig, outdir, "fig3_byzantine_success_vs_fraction")


def load_rmse_curve_data(runs_data: pd.DataFrame, rmse_rounds_path: Path) -> pd.DataFrame:
    """Load per-round RMSE data or derive a flat per-round proxy from run-level RMSE."""
    if rmse_rounds_path.exists():
        curve = pd.read_csv(rmse_rounds_path)
        required = {"protocol", "round", "rmse"}
        missing = required.difference(set(curve.columns))
        if missing:
            raise ValueError(f"Missing columns in RMSE rounds CSV: {sorted(missing)}")
        curve = curve.copy()
        curve["protocol"] = curve["protocol"].astype(str).map(normalize_protocol_label)
        curve["round"] = curve["round"].astype(int)
        curve["rmse"] = curve["rmse"].astype(float)
        return curve

    rows: list[dict[str, float | int | str]] = []
    for _, row in runs_data.iterrows():
        rounds = int(max(int(row["n_rounds"]), 1))
        for round_idx in range(1, rounds + 1):
            rows.append(
                {
                    "protocol": str(row["protocol"]),
                    "round": int(round_idx),
                    "rmse": float(row["trust_estimation_rmse"]),
                }
            )
    return pd.DataFrame(rows)


def plot_rmse_convergence(runs_data: pd.DataFrame, rmse_rounds_path: Path, outdir: Path) -> None:
    """Create trust-estimation RMSE convergence figure over rounds."""
    curve_data = load_rmse_curve_data(runs_data=runs_data, rmse_rounds_path=rmse_rounds_path)
    agg = aggregate_ci(curve_data, ["protocol", "round"], "rmse")

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for protocol in PROTOCOL_ORDER:
        subset = agg[agg["protocol"] == protocol].sort_values("round")
        if subset.empty:
            continue
        yerr = np.vstack(
            [
                subset["mean"].to_numpy() - subset["ci_low"].to_numpy(),
                subset["ci_high"].to_numpy() - subset["mean"].to_numpy(),
            ]
        )
        ax.errorbar(
            subset["round"],
            subset["mean"],
            yerr=yerr,
            marker=MARKERS.get(protocol, "o"),
            color=COLORS.get(protocol, "#000000"),
            linewidth=1.8,
            capsize=3,
            label=protocol,
        )

    ax.set_xlabel("Round")
    ax.set_ylabel("Trust Estimation RMSE")
    ax.set_title("Trust Estimation Convergence")
    ax.grid(alpha=0.25, linestyle="--")
    ax.legend()
    save_figure(fig, outdir, "fig4_rmse_over_rounds")


def main() -> None:
    """Generate all publication figures from run-level and optional per-round data."""
    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Input runs CSV not found: {args.input}")

    raw = pd.read_csv(args.input)
    runs_data = ensure_columns(raw)

    plot_tps_vs_nodes(data=runs_data, outdir=args.outdir)
    plot_messages_vs_nodes(data=runs_data, outdir=args.outdir)
    plot_byzantine_success(data=runs_data, outdir=args.outdir)
    plot_rmse_convergence(runs_data=runs_data, rmse_rounds_path=args.rmse_rounds, outdir=args.outdir)

    print(f"Saved figures to {args.outdir}")


if __name__ == "__main__":
    main()
