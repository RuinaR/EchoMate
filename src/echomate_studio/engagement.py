"""Context-first continuation of an established conversation.

Timing is diagnostic only. The caller must prove addressee and topical
continuity from actual channel/thread events; no guessed intent.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class EngagementPolicy:
    enabled: bool = True
    # Kept for backward compatibility. None means no hard expiry.
    max_gap_seconds: float | None = None

    def __post_init__(self):
        if self.max_gap_seconds is not None and self.max_gap_seconds <= 0:
            raise ValueError("max_gap_seconds must be positive or None")


def continue_engagement(policy: EngagementPolicy, *, ongoing: bool,
                        seconds_since_last_bot_reply: float,
                        addressed_to_bot: bool, topic_continues: bool) -> bool:
    """Require affirmative context evidence; time alone cannot grant engagement."""
    if not (policy.enabled and ongoing and addressed_to_bot and topic_continues):
        return False
    if seconds_since_last_bot_reply < 0:
        return False
    return (policy.max_gap_seconds is None or
            seconds_since_last_bot_reply <= policy.max_gap_seconds)
