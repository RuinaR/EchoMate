"""Conservative engagement signals from actual message reply references.

Reply chains are evidence of addressing, not proof of topical continuity.
Never derive ongoing engagement solely from recent timestamps.
"""
from __future__ import annotations
from dataclasses import dataclass
from .dialogue_state import Turn

@dataclass(frozen=True)
class EngagementEvidence:
    ongoing_engagement: bool
    addressed_to_bot: bool
    topic_continues: bool
    reason: str


def derive_engagement(turns: list[Turn], *, topic_continues: bool = False) -> EngagementEvidence:
    if not turns or turns[-1].is_bot:
        return EngagementEvidence(False, False, False, "no_latest_human")
    latest = turns[-1]
    by_id = {t.message_id: t for t in turns}
    # Only an explicit reply to a bot message demonstrates addressee.
    target = by_id.get(latest.reply_to) if latest.reply_to else None
    addressed = bool(target is not None and target.is_bot)
    # The referenced bot message itself establishes prior participation.
    ongoing = addressed
    if not addressed:
        return EngagementEvidence(False, False, False, "no_verified_reply_to_bot")
    # Explicit topical check is still required; a reply may change subject.
    if not topic_continues:
        return EngagementEvidence(True, True, False, "topic_unverified")
    return EngagementEvidence(ongoing, addressed, True, "verified_reply_chain_and_topic")
