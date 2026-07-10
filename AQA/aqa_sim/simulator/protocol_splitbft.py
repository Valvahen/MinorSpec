"""Static SplitBFT baseline protocol implementation."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .base_protocol import BaseProtocol, RoundResult


class SplitBFTProtocol(BaseProtocol):
    """SplitBFT baseline with fixed groups and static 2f+1 quorum."""

    def __init__(
        self,
        nodes: Sequence[Any],
        network: Any,
        rng: np.random.Generator,
        config: Mapping[str, Any] | None,
    ) -> None:
        """Initialize static per-group quorums at protocol construction."""
        super().__init__(nodes=nodes, network=network, rng=rng, config=config)
        self.group_quorums: dict[int, int] = {}
        for group_id, group_nodes in self.groups.items():
            n = len(group_nodes)
            f_value = self._compute_f(n)
            # Quorum must be a strict majority AND >= 2f+1, capped at group size.
            quorum = max(2 * f_value + 1, n // 2 + 1)
            self.group_quorums[group_id] = min(quorum, n)

    def run_round(self, round_no: int) -> RoundResult:
        """Execute one full SplitBFT round with static group quorums."""
        del round_no

        correct_vote = 1
        group_results = []
        total_messages = 0
        group_latencies: list[float] = []

        for group_id, group_nodes in self.groups.items():
            group_result = self._execute_group_pbft(
                group_id=group_id,
                group_nodes=group_nodes,
                quorum_size=int(self.group_quorums[group_id]),
                correct_vote=correct_vote,
                eligible_active_ids=None,
            )
            group_results.append(group_result)
            total_messages += int(group_result.msgs)
            group_latencies.append(float(group_result.latency_ms))

        inter_finalized, inter_messages, inter_latency, inter_byz_success, inter_quorum = self._execute_inter_group(
            group_results=group_results,
            correct_vote=correct_vote,
        )
        total_messages += int(inter_messages)
        group_latencies.append(float(inter_latency))

        all_groups_finalized = all(result.finalized for result in group_results)
        finalized = bool(all_groups_finalized and inter_finalized)
        byzantine_success = bool(finalized and inter_byz_success)
        quorum_size = int(max(max(self.group_quorums.values(), default=0), inter_quorum))
        latency_ms = float(np.mean(np.asarray(group_latencies))) if group_latencies else 0.0

        return RoundResult(
            finalized=finalized,
            msgs=total_messages,
            latency_ms=latency_ms,
            byzantine_success=byzantine_success,
            quorum_size=quorum_size,
        )
