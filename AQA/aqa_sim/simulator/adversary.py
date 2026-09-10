"""Adversarial behavior transforms for AQA-Sim."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import numpy as np


MessagePayload = dict[str, Any]
BehaviorOutput = MessagePayload | tuple[MessagePayload, MessagePayload] | None


def apply_behavior(
    node: Any,
    message: Mapping[str, Any],
    rng: np.random.Generator,
) -> BehaviorOutput:
    """Apply node behavior to an outgoing message and return transformed payload(s)."""
    del rng

    behavior = str(getattr(node, "behavior_type", "honest"))
    payload: MessagePayload = dict(deepcopy(message))

    if behavior == "crash":
        return None

    if behavior == "equivocate":
        first = dict(payload)
        second = dict(payload)

        if "vote" in payload:
            first["vote"] = payload["vote"]
            second["vote"] = _flip_vote_value(payload["vote"])
            if second["vote"] == first["vote"]:
                first["vote"] = 0
                second["vote"] = 1
        else:
            first["vote"] = 0
            second["vote"] = 1

        return [first, second]

    if behavior == "lie_trust":
        payload["reported_trust"] = 0.95
        return payload

    if behavior == "slow":
        baseline = float(payload.get("latency_ms", getattr(node, "base_latency_ms", 50.0)))
        payload["latency_ms"] = baseline * 3.0
        return payload

    return payload


def ground_truth_vote_from_behavior(
    node: Any,
    correct_vote: int,
    rng: np.random.Generator,
) -> int | None:
    """Derive the vote emitted by a node in the voting phase based on its behavior."""
    behavior = str(getattr(node, "behavior_type", "honest"))

    if behavior == "crash":
        return None

    if behavior == "equivocate":
        flipped = _flip_binary_vote(correct_vote)
        return int(rng.choice([correct_vote, flipped]))

    if behavior == "lie_trust":
        return int(correct_vote)

    if behavior == "slow":
        return int(correct_vote)

    return int(correct_vote)


def _flip_vote_value(vote: Any) -> Any:
    """Flip a generic vote value for equivocation payload generation."""
    if isinstance(vote, bool):
        return not vote
    if isinstance(vote, (int, np.integer)):
        return 1 - int(vote)
    if isinstance(vote, str):
        lowered = vote.lower()
        if lowered == "yes":
            return "no"
        if lowered == "no":
            return "yes"
        if lowered == "true":
            return "false"
        if lowered == "false":
            return "true"
    return vote


def _flip_binary_vote(vote: int) -> int:
    """Flip a binary integer vote in {0, 1}."""
    return 1 if int(vote) == 0 else 0

def get_reported_trust(node) -> float:
    """
    Returns the trust score a node self-reports to the protocol.
    Honest nodes report their computed estimate; 'lie_trust' nodes inflate it.
    """
    if getattr(node, "behavior_type", "honest") == "lie_trust":
        return 0.95  # dishonest self-boost
    return float(getattr(node, "trust_estimate", node.ground_truth_trust))
