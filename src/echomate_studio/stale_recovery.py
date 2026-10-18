"""Bounded stale-response recovery; no Discord network interactions.

A generated reply is reusable only if the new turns were explicitly classified
as non-material. Default classifier treats every new turn as material, so it
restarts once or safely stays silent.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

from .dialogue_state import DialogueState, Turn
from .turn_pipeline import TurnResult


@dataclass(frozen=True)
class RecoveryResult:
    reply: str | None
    reason: str
    version: int
    attempts: int


def recover_latest(*, state: DialogueState, channel_id: int,
                   thread_id: int | None,
                   evaluate: Callable[[], TurnResult],
                   max_attempts: int = 2,
                   non_material_update: Callable[[list[Turn]], bool] | None = None) -> RecoveryResult:
    """Restart on material change, with finite retries and fail-closed default.

    This code is synchronous. Actual Discord integration must serialize sends
    and revalidate the version inside its per-channel send lock.
    """
    if max_attempts < 1 or max_attempts > 3:
        raise ValueError("max_attempts must be 1..3")
    for attempt in range(1, max_attempts + 1):
        before_version, before = state.snapshot(channel_id=channel_id, thread_id=thread_id)
        result = evaluate()
        if result.reply is None and not result.reason.startswith("stale_"):
            return RecoveryResult(None, result.reason, result.version, attempt)
        after_version, after = state.snapshot(channel_id=channel_id, thread_id=thread_id)
        if result.reply is not None and result.version == after_version and before_version == after_version:
            return RecoveryResult(result.reply, "ready", after_version, attempt)
        added = after[len(before):] if after[:len(before)] == before else after
        # Only reuse a previous answer if a caller supplies a validated classifier.
        if (result.reply and non_material_update is not None and
                after_version != result.version and added and
                non_material_update(added)):
            return RecoveryResult(result.reply, "ready_non_material_update", after_version, attempt)
    version, _ = state.snapshot(channel_id=channel_id, thread_id=thread_id)
    return RecoveryResult(None, "stale_retry_exhausted", version, max_attempts)
