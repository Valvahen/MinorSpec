"""Adaptive quorum AQA-SplitBFT protocol implementation."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from .base_protocol import BaseProtocol, RoundResult


class AQASplitBFTProtocol(BaseProtocol):
    """Adaptive quorum protocol with trust-driven dynamic quorum sizing."""

    def __init__(
        self,
        nodes: Sequence[Any],
        network: Any,
        rng: np.random.Generator,
        config: Mapping[str, Any] | None,
    ) -> None:
        """Initialize adaptive quorum protocol state and safety defaults."""
        super().__init__(nodes=nodes, network=network, rng=rng, config=config)

    def run_round(self, round_no: int) -> RoundResult:
        """Execute one AQA round with trust-based dynamic quorums."""
        for node in self.nodes:
            node.compute_trust_estimate()

        correct_vote = 1

        group_results = []
        total_messages = 0
        round_latencies: list[float] = []
        round_quorums: list[float] = []

        for group_id, group_nodes in self.groups.items():
            # Trust measured over the WHOLE group so Byzantine presence lowers it.
            group_trust = self._group_trust_mean(group_nodes)

            group_size = len(group_nodes)
            f_group = self._compute_f(group_size)
            q_safe = min(max(2 * f_group + 1, (group_size + f_group) // 2 + 1), group_size)

            # Adaptive range: small quorum when trusted, grows toward group size under attack.
            q_min = max(q_safe, int(self.config.get("Q_min", self.config.get("q_min", q_safe))))
            q_max = min(group_size, int(self.config.get("Q_max", self.config.get("q_max", group_size))))
            if q_max < q_min:
                q_max = q_min

            # LOW trust  -> quorum toward q_max  (defensive, big quorum)
            # HIGH trust -> quorum toward q_min  (fast, small quorum)
            q_candidate = int(np.clip(
                round(q_max - (q_max - q_min) * group_trust),
                q_min, q_max,
            ))
            quorum = self._safety_check(
                q_candidate=q_candidate,
                q_safe=q_safe,
                group_id=group_id,
                round_no=round_no,
            )

            # All online nodes may vote; security comes from the adaptive quorum size,
            # not from excluding nodes. This is the core AQA mechanism.
            eligible_ids = {int(n.id) for n in group_nodes if self._is_node_online(n)}
            group_result = self._execute_group_pbft(
                group_id=group_id,
                group_nodes=group_nodes,
                quorum_size=quorum,
                correct_vote=correct_vote,
                eligible_active_ids=eligible_ids,
            )
            group_results.append(group_result)
            total_messages += int(group_result.msgs)
            round_latencies.append(float(group_result.latency_ms))
            round_quorums.append(float(quorum))

        inter_finalized, inter_messages, inter_latency, inter_byz_success, inter_quorum = self._execute_inter_group(
            group_results=group_results,
            correct_vote=correct_vote,
        )
        total_messages += int(inter_messages)
        round_latencies.append(float(inter_latency))

        all_groups_finalized = all(result.finalized for result in group_results)
        finalized = bool(all_groups_finalized and inter_finalized)
        byzantine_success = bool(finalized and inter_byz_success)

        latency_ms = float(np.mean(np.asarray(round_latencies))) if round_latencies else 0.0
        quorum_size = float(np.mean(round_quorums)) if round_quorums else 0.0

        return RoundResult(
            finalized=finalized,
            msgs=total_messages,
            latency_ms=latency_ms,
            byzantine_success=byzantine_success,
            quorum_size=quorum_size,
        )

    def _group_trust_mean(self, group_nodes: Sequence[Any]) -> float:
        """Mean trust across ALL nodes in a group (online or not).

        Unlike the median, the mean responds to the presence of low-trust
        nodes, which is what drives adaptive quorum growth under attack.
        """
        if len(group_nodes) == 0:
            return 1.0
        trust_values = np.asarray(
            [float(getattr(node, "trust_estimate", 0.5)) for node in group_nodes],
            dtype=float,
        )
        return float(np.mean(trust_values))

    def _group_trust_median(self, active_group_nodes: Sequence[Any]) -> float:
        """Compute median trust among nodes in a group (kept for reference)."""
        if len(active_group_nodes) == 0:
            return 0.0
        trust_values = np.asarray(
            [float(getattr(node, "trust_estimate", 0.5)) for node in active_group_nodes],
            dtype=float,
        )
        return float(np.median(trust_values))

    def _safety_check(
        self,
        q_candidate: int,
        q_safe: int,
        group_id: int,
        round_no: int,
    ) -> int:
        """Ensure adaptive quorum never drops below 2f+1, else revert to safe quorum."""
        if q_candidate >= q_safe:
            return int(q_candidate)
        self.logs.append(
            f"round={round_no} group={group_id} unsafe_quorum={q_candidate} reverted_to={q_safe}"
        )
        return int(q_safe)