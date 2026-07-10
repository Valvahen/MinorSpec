"""Network simulation utilities for AQA-Sim."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


@dataclass
class Network:
    """Network model with probabilistic drops, partitions, and latency sampling."""

    rng: np.random.Generator
    drop_prob: float = 0.05
    partition_config: Mapping[str, Sequence[int]] | Sequence[set[int]] | Mapping[int, int] | None = None
    latency_std_ms: float = 20.0
    latency_floor_ms: float = 5.0

    # Runtime-only field: node_id -> partition side (built from partition_config)
    _partition_lookup: dict[int, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.partition_config is not None:
            self._build_partition_lookup(self.partition_config)

    # ------------------------------------------------------------------
    # Partition API
    # ------------------------------------------------------------------

    def enable_partition(self, partition_config: Mapping[str, Sequence[int]] | Sequence[set[int]] | Mapping[int, int]) -> None:
        """Activate (or re-activate) a network partition."""
        self.partition_config = partition_config
        self._build_partition_lookup(partition_config)

    def disable_partition(self) -> None:
        """Lift the current partition; all cross-side communication resumes."""
        self.partition_config = None
        self._partition_lookup = {}

    def _build_partition_lookup(self, partition_config: Any) -> None:
        """Flatten any supported partition_config format into node_id -> side."""
        self._partition_lookup = {}

        if partition_config is None:
            return

        # Case A: {"side_name": [id, id, ...]} — the format the tests use
        if isinstance(partition_config, Mapping):
            # Distinguish {side_name: [ids]} from {node_id: side_id}
            sample_val = next(iter(partition_config.values()), None)
            if isinstance(sample_val, (list, tuple, set)):
                for side_name, ids in partition_config.items():
                    for nid in ids:
                        self._partition_lookup[int(nid)] = side_name
            else:
                # {node_id: side_id} form
                for nid, side in partition_config.items():
                    self._partition_lookup[int(nid)] = side
            return

        # Case B: sequence of sets [{0, 1}, {2, 3}] — legacy form
        if isinstance(partition_config, Sequence):
            for idx, partition in enumerate(partition_config):
                for nid in partition:
                    self._partition_lookup[int(nid)] = idx

    def _same_partition(self, sender_id: int, receiver_id: int) -> bool:
        """True if sender and receiver are on the same partition side (or no partition)."""
        if not self._partition_lookup:
            return True
        return self._partition_lookup.get(sender_id) == self._partition_lookup.get(receiver_id)

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------

    def send(self, sender: Any, receiver: Any, msg: Mapping[str, Any]) -> tuple[bool, float]:
        """Send one message and return (delivered, latency_ms)."""
        del msg  # not currently inspected

        # Sample latency once (may be reported even if dropped)
        sampled = float(self.rng.normal(float(receiver.base_latency_ms), self.latency_std_ms))
        latency_ms = max(sampled, self.latency_floor_ms)

        # Offline sender / receiver → drop
        if not _is_online(sender):
            return False, latency_ms
        if not _is_online(receiver):
            return False, latency_ms

        # Cross-partition → drop
        if not self._same_partition(int(sender.id), int(receiver.id)):
            return False, latency_ms

        # Random packet drop
        if self.rng.random() < self.drop_prob:
            return False, latency_ms

        return True, latency_ms

    # ------------------------------------------------------------------
    # Churn
    # ------------------------------------------------------------------

    def churn_step(
        self,
        nodes: Iterable[Any],
        p_leave: float,
        p_join: float,
        rng: np.random.Generator,
    ) -> None:
        """Toggle per-round node availability under join/leave churn probabilities."""
        churn_step(nodes=nodes, p_leave=p_leave, p_join=p_join, rng=rng)


# ----------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------

def _is_online(node: Any) -> bool:
    """Read is_online, falling back to is_available for backward compatibility."""
    if hasattr(node, "is_online"):
        return bool(node.is_online)
    if hasattr(node, "is_available"):
        return bool(node.is_available)
    return True


def _set_online(node: Any, value: bool) -> None:
    """Set is_online (and mirror to is_available if present)."""
    node.is_online = value
    if hasattr(node, "is_available"):
        node.is_available = value


def churn_step(
    nodes: Iterable[Any],
    p_leave: float,
    p_join: float,
    rng: np.random.Generator,
) -> None:
    """Toggle per-round node availability under join/leave churn probabilities."""
    if not 0.0 <= p_leave <= 1.0:
        raise ValueError("p_leave must be in [0, 1]")
    if not 0.0 <= p_join <= 1.0:
        raise ValueError("p_join must be in [0, 1]")

    for node in nodes:
        current = _is_online(node)
        if current and rng.random() < p_leave:
            _set_online(node, False)
        elif (not current) and rng.random() < p_join:
            _set_online(node, True)