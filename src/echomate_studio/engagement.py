"""Track a bot's active participation in a channel or thread without forced replies."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class EngagementPolicy:
    enabled: bool = True
    max_gap_seconds: float = 180.0
    def __post_init__(self):
        if self.max_gap_seconds <= 0:
            raise ValueError("max_gap_seconds must be positive")

def continue_engagement(policy: EngagementPolicy, *, ongoing: bool,
                        seconds_since_last_bot_reply: float,
                        addressed_to_bot: bool,
                        topic_continues: bool) -> bool:
    """Caller supplies contextual addressing/topic checks, not just elapsed time."""
    return (policy.enabled and ongoing and addressed_to_bot and topic_continues and
            0 <= seconds_since_last_bot_reply <= policy.max_gap_seconds)
