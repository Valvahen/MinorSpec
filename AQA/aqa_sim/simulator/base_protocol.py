"""Base protocol primitives for PBFT-style simulation rounds."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .adversary import apply_behavior, ground_truth_vote_from_behavior


@dataclass(frozen=True)
class RoundResult:
    """Round-level metrics returned by protocol executions."""

    finalized: bool
    msgs: int
    latency_ms: float
    byzantine_success: bool
    quorum_size: int


@dataclass
class GroupExecutionResult:
    """Internal per-group PBFT outcome for one protocol round."""

    group_id: int
    finalized: bool
    decision: int | None
    msgs: int
    latency_ms: float
    byzantine_success: bool
    leader: Any | None
    active_nodes: list[Any]
    quorum_size: int


class BaseProtocol(ABC):
    """Abstract base class for SplitBFT-family protocol simulations."""

    def __init__(
        self,
        nodes: Sequence[Any],
        network: Any,
        rng: np.random.Generator,
        config: Mapping[str, Any] | None,
    ) -> None:
        """Initialize protocol state and immutable node grouping."""
        self.nodes: list[Any] = list(nodes)
        self.network = network
        self.rng = rng
        self.config: dict[str, Any] = dict(config or {})
        self.groups: dict[int, list[Any]] = self._build_groups(self.nodes)
        self.logs: list[str] = []

    @abstractmethod
    def run_round(self, round_no: int) -> RoundResult:
        """Execute one complete consensus round and return round metrics."""

    def _build_groups(self, nodes: Sequence[Any]) -> dict[int, list[Any]]:
        """Create group_id -> nodes mapping from fixed node assignments."""
        groups: dict[int, list[Any]] = defaultdict(list)
        for node in nodes:
            groups[int(node.group_id)].append(node)
        return {group_id: members for group_id, members in sorted(groups.items())}

    def _compute_f(self, n_nodes: int) -> int:
        """Compute PBFT fault tolerance bound f for group size n."""
        if n_nodes <= 0:
            return 0
        return max((n_nodes - 1) // 3, 0)

    def _is_node_online(self, node: Any) -> bool:
        """Sample per-round node participation using availability state and probability."""
        # Availability_prob is the LONG-TERM online rate; churn_step handles dynamics.
        # Per-round, just respect the current is_online / is_available state.
        return bool(getattr(node, "is_online", getattr(node, "is_available", True)))

    def _expand_behavior_output(self, transformed: Any) -> list[dict[str, Any]]:
        """Normalize adversary output into a list of concrete outgoing payloads."""
        if transformed is None:
            return []
        if isinstance(transformed, dict):
            return [dict(transformed)]
        if isinstance(transformed, (list, tuple)):
            return [dict(item) for item in transformed]
        raise TypeError(
            f"Unexpected adversary output type: {type(transformed)._name_}"
    )

    def _send_with_behavior(
        self,
        sender: Any,
        receiver: Any,
        payload: Mapping[str, Any],
    ) -> tuple[list[dict[str, Any]], int, list[float]]:
        """Send one logical message after adversarial mutation and collect deliveries."""
        transformed = apply_behavior(node=sender, message=payload, rng=self.rng)
        attempted = 0
        delivered_payloads: list[dict[str, Any]] = []
        latencies: list[float] = []

        if transformed is None:
            return delivered_payloads, 1, latencies

        versions = self._expand_behavior_output(transformed)
        for version in versions:
            attempted += 1
            delivered, sampled_latency = self.network.send(sender=sender, receiver=receiver, msg=version)
            effective_latency = sampled_latency
            if "latency_ms" in version:
                effective_latency = max(effective_latency, float(version["latency_ms"]))
            if delivered:
                delivered_payloads.append(version)
                latencies.append(float(effective_latency))

        return delivered_payloads, attempted, latencies

    def _execute_group_pbft(
        self,
        group_id: int,
        group_nodes: Sequence[Any],
        quorum_size: int,
        correct_vote: int,
        eligible_active_ids: set[int] | None = None,
    ) -> GroupExecutionResult:
        """Run pre-prepare/prepare/commit phases for one group."""
        active_nodes = [node for node in group_nodes if self._is_node_online(node)]
        if eligible_active_ids is not None:
            active_nodes = [node for node in active_nodes if int(node.id) in eligible_active_ids]

        messages = 0
        delivered_latencies: list[float] = []
        sender_latency_book: dict[int, list[float]] = defaultdict(list)

        if len(active_nodes) == 0:
            for node in group_nodes:
                node.record_round(
                    participated=False,
                    voted=False,
                    agreed_with_majority=False,
                    rtt_ms=None,
                    misbehaved=False,
                )
            return GroupExecutionResult(
                group_id=group_id,
                finalized=False,
                decision=None,
                msgs=0,
                latency_ms=0.0,
                byzantine_success=False,
                leader=None,
                active_nodes=[],
                quorum_size=quorum_size,
            )

        leader = min(active_nodes, key=lambda item: int(item.id))

        preprepare_votes: dict[int, list[int]] = defaultdict(list)
        preprepare_votes[int(leader.id)].append(int(correct_vote))
        for receiver in active_nodes:
            if int(receiver.id) == int(leader.id):
                continue
            payload = {
                "phase": "pre-prepare",
                "vote": int(correct_vote),
                "reported_trust": float(getattr(leader, "trust_estimate", 0.5)),
            }
            delivered_payloads, attempted, latencies = self._send_with_behavior(
                sender=leader,
                receiver=receiver,
                payload=payload,
            )
            messages += attempted
            delivered_latencies.extend(latencies)
            sender_latency_book[int(leader.id)].extend(latencies)
            for delivered_payload in delivered_payloads:
                if "vote" in delivered_payload:
                    preprepare_votes[int(receiver.id)].append(int(delivered_payload["vote"]))

        prepare_sent_vote: dict[int, int] = {}
        prepare_received: dict[int, list[int]] = defaultdict(list)
        for sender in active_nodes:
            sender_id = int(sender.id)
            sender_seen = preprepare_votes.get(sender_id, [])
            if sender_seen:
                phase_vote = int(sender_seen[0])
            else:
                phase_vote = int(correct_vote)

            voted = ground_truth_vote_from_behavior(
                node=sender,
                correct_vote=phase_vote,
                rng=self.rng,
            )
            if voted is None:
                continue

            voted_int = int(voted)
            prepare_sent_vote[sender_id] = voted_int
            prepare_received[sender_id].append(voted_int)

            for receiver in active_nodes:
                if int(receiver.id) == sender_id:
                    continue
                payload = {
                    "phase": "prepare",
                    "vote": voted_int,
                    "reported_trust": float(getattr(sender, "trust_estimate", 0.5)),
                }
                delivered_payloads, attempted, latencies = self._send_with_behavior(
                    sender=sender,
                    receiver=receiver,
                    payload=payload,
                )
                messages += attempted
                delivered_latencies.extend(latencies)
                sender_latency_book[sender_id].extend(latencies)
                for delivered_payload in delivered_payloads:
                    if "vote" in delivered_payload:
                        prepare_received[int(receiver.id)].append(int(delivered_payload["vote"]))

        prepared_vote: dict[int, int] = {}
        for receiver in active_nodes:
            receiver_votes = prepare_received.get(int(receiver.id), [])
            if not receiver_votes:
                continue
            unique_votes, counts = np.unique(np.asarray(receiver_votes), return_counts=True)
            best_index = int(np.argmax(counts))
            if int(counts[best_index]) >= quorum_size:
                prepared_vote[int(receiver.id)] = int(unique_votes[best_index])

        commit_received: dict[int, list[int]] = defaultdict(list)
        for sender in active_nodes:
            sender_id = int(sender.id)
            if sender_id not in prepared_vote:
                continue
            sender_vote = int(prepared_vote[sender_id])
            commit_received[sender_id].append(sender_vote)
            for receiver in active_nodes:
                if int(receiver.id) == sender_id:
                    continue
                payload = {
                    "phase": "commit",
                    "vote": sender_vote,
                    "reported_trust": float(getattr(sender, "trust_estimate", 0.5)),
                }
                delivered_payloads, attempted, latencies = self._send_with_behavior(
                    sender=sender,
                    receiver=receiver,
                    payload=payload,
                )
                messages += attempted
                delivered_latencies.extend(latencies)
                sender_latency_book[sender_id].extend(latencies)
                for delivered_payload in delivered_payloads:
                    if "vote" in delivered_payload:
                        commit_received[int(receiver.id)].append(int(delivered_payload["vote"]))

        local_commit_vote: dict[int, int] = {}
        for receiver in active_nodes:
            receiver_votes = commit_received.get(int(receiver.id), [])
            if not receiver_votes:
                continue
            unique_votes, counts = np.unique(np.asarray(receiver_votes), return_counts=True)
            best_index = int(np.argmax(counts))
            if int(counts[best_index]) >= quorum_size:
                local_commit_vote[int(receiver.id)] = int(unique_votes[best_index])

        decision: int | None = None
        finalized = False
        if local_commit_vote:
            committed_votes = np.asarray(list(local_commit_vote.values()), dtype=int)
            unique_votes, counts = np.unique(committed_votes, return_counts=True)
            best_index = int(np.argmax(counts))
            if int(counts[best_index]) >= quorum_size:
                decision = int(unique_votes[best_index])
                finalized = True

        group_latency = float(np.mean(np.asarray(delivered_latencies))) if delivered_latencies else 0.0

        active_ids = {int(node.id) for node in active_nodes}
        for node in group_nodes:
            node_id = int(node.id)
            participated = node_id in active_ids
            voted = node_id in prepare_sent_vote
            agreed = voted and decision is not None and int(prepare_sent_vote[node_id]) == int(decision)
            per_node_rtts = sender_latency_book.get(node_id, [])
            avg_rtt = float(np.mean(np.asarray(per_node_rtts))) if per_node_rtts else None
            behavior = str(getattr(node, "behavior_type", "honest"))
            misbehaved = behavior in {"crash", "equivocate", "lie_trust"}
            node.record_round(
                participated=participated,
                voted=voted,
                agreed_with_majority=agreed,
                rtt_ms=avg_rtt,
                misbehaved=misbehaved,
            )

        return GroupExecutionResult(
            group_id=group_id,
            finalized=finalized,
            decision=decision,
            msgs=messages,
            latency_ms=group_latency,
            byzantine_success=bool(finalized and decision is not None and int(decision) != int(correct_vote)),
            leader=leader,
            active_nodes=active_nodes,
            quorum_size=quorum_size,
        )

    def _execute_inter_group(
        self,
        group_results: Sequence[GroupExecutionResult],
        correct_vote: int,
    ) -> tuple[bool, int, float, bool, int]:
        """Run cross-group PBFT-style aggregation over finalized group decisions."""
        finalized_groups = [result for result in group_results if result.finalized and result.decision is not None]
        if len(finalized_groups) == 0:
            return False, 0, 0.0, False, 0

        representative_map: dict[int, Any] = {}
        for result in finalized_groups:
            if result.leader is not None:
                representative_map[result.group_id] = result.leader

        group_count = len(self.groups)
        inter_quorum = max((2 * group_count) // 3 + 1, 1)
        inter_messages = 0
        inter_latencies: list[float] = []

        representatives: list[tuple[int, Any, int]] = []
        for result in finalized_groups:
            rep = representative_map.get(result.group_id)
            if rep is not None:
                representatives.append((int(result.group_id), rep, int(result.decision)))

        if len(representatives) == 0:
            return False, inter_messages, 0.0, False, inter_quorum

        coordinator_group, coordinator, _ = min(representatives, key=lambda item: int(item[1].id))
        group_decisions = np.asarray([item[2] for item in representatives], dtype=int)
        unique_group_votes, group_vote_counts = np.unique(group_decisions, return_counts=True)
        proposal_vote = int(unique_group_votes[int(np.argmax(group_vote_counts))])

        preprepare_received: dict[int, list[int]] = defaultdict(list)
        preprepare_received[int(coordinator_group)].append(proposal_vote)
        for dst_group, receiver, _ in representatives:
            if dst_group == coordinator_group:
                continue
            payload = {
                "phase": "cross-pre-prepare",
                "vote": proposal_vote,
                "from_group": int(coordinator_group),
            }
            delivered_payloads, attempted, latencies = self._send_with_behavior(
                sender=coordinator,
                receiver=receiver,
                payload=payload,
            )
            inter_messages += attempted
            inter_latencies.extend(latencies)
            for delivered_payload in delivered_payloads:
                if "vote" in delivered_payload:
                    preprepare_received[int(dst_group)].append(int(delivered_payload["vote"]))

        prepare_sent: dict[int, int] = {}
        prepare_received: dict[int, list[int]] = defaultdict(list)
        for src_group, sender, local_decision in representatives:
            seen = preprepare_received.get(src_group, [])
            vote = int(seen[0]) if seen else int(local_decision)
            prepare_sent[src_group] = vote
            prepare_received[src_group].append(vote)
            for dst_group, receiver, _ in representatives:
                if dst_group == src_group:
                    continue
                payload = {
                    "phase": "cross-prepare",
                    "vote": vote,
                    "from_group": int(src_group),
                }
                delivered_payloads, attempted, latencies = self._send_with_behavior(
                    sender=sender,
                    receiver=receiver,
                    payload=payload,
                )
                inter_messages += attempted
                inter_latencies.extend(latencies)
                for delivered_payload in delivered_payloads:
                    if "vote" in delivered_payload:
                        prepare_received[int(dst_group)].append(int(delivered_payload["vote"]))

        prepared_vote: dict[int, int] = {}
        for dst_group, _, _ in representatives:
            votes = prepare_received.get(dst_group, [])
            if not votes:
                continue
            unique_votes, counts = np.unique(np.asarray(votes), return_counts=True)
            best_index = int(np.argmax(counts))
            if int(counts[best_index]) >= inter_quorum:
                prepared_vote[int(dst_group)] = int(unique_votes[best_index])

        commit_received: dict[int, list[int]] = defaultdict(list)
        for src_group, sender, _ in representatives:
            if src_group not in prepared_vote:
                continue
            vote = int(prepared_vote[src_group])
            commit_received[src_group].append(vote)
            for dst_group, receiver, _ in representatives:
                if dst_group == src_group:
                    continue
                payload = {
                    "phase": "cross-commit",
                    "vote": vote,
                    "from_group": int(src_group),
                }
                delivered_payloads, attempted, latencies = self._send_with_behavior(
                    sender=sender,
                    receiver=receiver,
                    payload=payload,
                )
                inter_messages += attempted
                inter_latencies.extend(latencies)
                for delivered_payload in delivered_payloads:
                    if "vote" in delivered_payload:
                        commit_received[int(dst_group)].append(int(delivered_payload["vote"]))

        final_votes: list[int] = []
        for dst_group, _, _ in representatives:
            votes = commit_received.get(dst_group, [])
            if not votes:
                continue
            unique_votes, counts = np.unique(np.asarray(votes), return_counts=True)
            best_index = int(np.argmax(counts))
            if int(counts[best_index]) >= inter_quorum:
                final_votes.append(int(unique_votes[best_index]))

        if len(final_votes) < inter_quorum:
            latency_ms = float(np.mean(np.asarray(inter_latencies))) if inter_latencies else 0.0
            return False, inter_messages, latency_ms, False, inter_quorum

        unique_votes, counts = np.unique(np.asarray(final_votes), return_counts=True)
        best_index = int(np.argmax(counts))
        global_decision = int(unique_votes[best_index])
        finalized = int(counts[best_index]) >= inter_quorum
        byzantine_success = finalized and global_decision != int(correct_vote)
        latency_ms = float(np.mean(np.asarray(inter_latencies))) if inter_latencies else 0.0
        return finalized, inter_messages, latency_ms, byzantine_success, inter_quorum
