"""Metrics definitions and serialization helpers for simulation runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Mapping


@dataclass
class RunMetrics:
    """Aggregated metrics captured from one experiment run.

    Can be constructed empty and populated round-by-round via
    `update_from_round()`, then `finalize()` computes derived aggregates.
    Alternatively, all fields may be set directly on construction.
    """

    # ---- Public aggregate fields (all with defaults so RunMetrics() works)
    TPS: float = 0.0
    blocks_finalized: int = 0
    total_messages: int = 0
    avg_consensus_latency_ms: float = 0.0
    avg_quorum_size: float = 0.0
    safety_violations: int = 0
    byzantine_success_count: int = 0
    trust_estimation_rmse: float = 0.0

    # ---- Internal accumulators (excluded from asdict / CSV export)
    _latencies: list[float] = field(default_factory=list, repr=False, compare=False)
    _quorum_sizes: list[int] = field(default_factory=list, repr=False, compare=False)
    _elapsed_s: float = field(default=0.0, repr=False, compare=False)
    _trust_errors: list[float] = field(default_factory=list, repr=False, compare=False)

    # ------------------------------------------------------------------
    # Lowercase alias — tests read `metrics.tps`
    # ------------------------------------------------------------------

    @property
    def tps(self) -> float:
        """Lowercase alias for TPS."""
        return self.TPS

    @tps.setter
    def tps(self, value: float) -> None:
        self.TPS = float(value)

    # ------------------------------------------------------------------
    # Accumulation API
    # ------------------------------------------------------------------

    def update_from_round(self, result: Any) -> None:
        """Merge one round's RoundResult into the running totals.

        Reads the following attributes off `result` (missing = default):
          finalized (bool), msgs (int), latency_ms (float),
          quorum_size (int), byzantine_success (bool),
          safety_violation (bool), trust_error (float, optional).
        """
        msgs = int(getattr(result, "msgs", 0))
        latency_ms = float(getattr(result, "latency_ms", 0.0))
        quorum_size = int(getattr(result, "quorum_size", 0))

        self.total_messages += msgs
        self._latencies.append(latency_ms)
        self._quorum_sizes.append(quorum_size)
        self._elapsed_s += latency_ms / 1000.0  # ms → s

        if getattr(result, "finalized", False):
            self.blocks_finalized += 1
        if getattr(result, "byzantine_success", False):
            self.byzantine_success_count += 1
        if getattr(result, "safety_violation", False):
            self.safety_violations += 1

        trust_err = getattr(result, "trust_error", None)
        if trust_err is not None:
            self._trust_errors.append(float(trust_err))

    def finalize(self) -> None:
        """Compute derived metrics after all rounds are complete."""
        if self._elapsed_s > 0:
            self.TPS = self.blocks_finalized / self._elapsed_s
        else:
            self.TPS = 0.0

        if self._latencies:
            self.avg_consensus_latency_ms = float(
                sum(self._latencies) / len(self._latencies)
            )

        if self._quorum_sizes:
            self.avg_quorum_size = float(
                sum(self._quorum_sizes) / len(self._quorum_sizes)
            )

        if self._trust_errors:
            mean_sq = sum(e * e for e in self._trust_errors) / len(self._trust_errors)
            self.trust_estimation_rmse = float(mean_sq ** 0.5)


# ----------------------------------------------------------------------
# CSV export (unchanged behavior, but skips private accumulators)
# ----------------------------------------------------------------------

def to_csv_row(
    run_id: str,
    protocol_name: str,
    config: Mapping[str, Any],
    metrics: RunMetrics,
) -> dict[str, Any]:
    """Convert run metadata and aggregate metrics into one CSV row dictionary."""
    row: dict[str, Any] = {
        "run_id": run_id,
        "protocol": protocol_name,
    }
    for key, value in config.items():
        row[f"cfg_{key}"] = value

    # Only export public (non-underscored) fields to CSV
    for f in fields(metrics):
        if f.name.startswith("_"):
            continue
        row[f.name] = getattr(metrics, f.name)
    return row