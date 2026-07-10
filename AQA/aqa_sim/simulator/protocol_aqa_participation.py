"""Participation-based AQA: restricts consensus to a trust-selected subset.

Contrast with threshold-AQA (protocol_aqa.py):
  - Threshold-AQA: ALL online nodes vote; quorum is a tally threshold. O(n^2) msgs.
  - Participation-AQA: only a trust-selected SUBSET participates. O(k^2) msgs, k<=n.

Under high trust the subset shrinks (fewer messages); under low trust it grows
toward full participation (safety), then a static fallback guards liveness.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .base_protocol import BaseProtocol, RoundResult


class AQAParticipationProtocol(BaseProtocol):
    """Trust-adaptive PARTICIPATION: shrink the active set when trust is high."""

    def __init__(self, nodes, network, rng, config) -> None:
        super().__init__(nodes=nodes, network=network, rng=rng, config=config)

    def run_round(self, round_no: int) -> RoundResult:
        for node in self.nodes:
            node.compute_trust_estimate()

        correct_vote = 1
        group_results = []
        total_messages = 0
        round_latencies: list[float] = []
        round_quorums: list[float] = []

        for group_id, group_nodes in self.groups.items():
            online = [n for n in group_nodes if self._is_node_online(n)]
            f_group = self._compute_f(len(group_nodes))
            # Safety floor: must keep at least 2f+1 (majority-clamped) participants
            min_participants = min(
                max(2 * f_group + 1, len(group_nodes) // 2 + 1),
                len(group_nodes),
            )

            group_trust = self._group_trust_mean(group_nodes)

            # High trust -> small participation set (toward min_participants)
            # Low trust  -> large participation set (toward all online)
            max_p = len(online)
            target = int(round(min_participants + (max_p - min_participants) * (1.0 - group_trust)))
            target = int(np.clip(target, min_participants, max_p)) if max_p >= min_participants else max_p

            active_subset = self._select_trusted_subset(online, target)
            eligible_ids = {int(n.id) for n in active_subset}

            # Quorum within the participating subset (majority of participants)
            quorum = min(max(2 * f_group + 1, len(active_subset) // 2 + 1), len(active_subset)) \
                if active_subset else 1

            gr = self._execute_group_pbft(
                group_id=group_id,
                group_nodes=group_nodes,
                quorum_size=quorum,
                correct_vote=correct_vote,
                eligible_active_ids=eligible_ids,
            )
            group_results.append(gr)
            total_messages += int(gr.msgs)
            round_latencies.append(float(gr.latency_ms))
            round_quorums.append(float(len(active_subset)))  # track participation size

        inter_finalized, inter_msgs, inter_lat, inter_byz, inter_q = self._execute_inter_group(
            group_results=group_results, correct_vote=correct_vote,
        )
        total_messages += int(inter_msgs)
        round_latencies.append(float(inter_lat))

        finalized = bool(all(r.finalized for r in group_results) and inter_finalized)
        byzantine_success = bool(finalized and inter_byz)

        latency_ms = float(np.mean(round_latencies)) if round_latencies else 0.0
        participation = float(np.mean(round_quorums)) if round_quorums else 0.0

        return RoundResult(
            finalized=finalized,
            msgs=total_messages,
            latency_ms=latency_ms,
            byzantine_success=byzantine_success,
            quorum_size=participation,   # here quorum_size field = avg participation
        )

    def _group_trust_mean(self, group_nodes: Sequence[Any]) -> float:
        if len(group_nodes) == 0:
            return 1.0
        vals = [float(getattr(n, "trust_estimate", 0.5)) for n in group_nodes]
        return float(np.mean(vals))

    def _select_trusted_subset(self, online: Sequence[Any], k: int) -> list:
        """Pick the k most-trusted online nodes (deterministic given trust)."""
        if k >= len(online) or k <= 0:
            return list(online)
        # Highest trust first; ties broken by id for reproducibility
        ranked = sorted(
            online,
            key=lambda n: (float(getattr(n, "trust_estimate", 0.5)), -int(n.id)),
            reverse=True,
        )
        return ranked[:k]