"""Explicit @mention response eligibility, separate from autonomous participation.

The Discord adapter must pass the bot's *actual* ID from the gateway,
not an inferred display name. This module does not send messages.
"""
from __future__ import annotations
from dataclasses import dataclass
import re

MENTION = re.compile(r"<@!?(\d+)>")

@dataclass(frozen=True)
class MentionPolicy:
    enabled: bool = True
    allowed_channel_ids: frozenset[int] = frozenset()
    allowed_thread_ids: frozenset[int] = frozenset()
    cooldown_seconds: float = 2.0

    def __post_init__(self):
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must not be negative")


def mentions_bot(content: str, bot_user_id: int) -> bool:
    if not isinstance(content, str) or not isinstance(bot_user_id, int) or bot_user_id <= 0:
        return False
    return any(int(match.group(1)) == bot_user_id for match in MENTION.finditer(content))


def permit_mention_reply(policy: MentionPolicy, *, content: str, bot_user_id: int,
                         channel_id: int, thread_id: int | None,
                         author_is_bot: bool, opted_out: bool,
                         seconds_since_last_reply: float) -> tuple[bool, str]:
    if not policy.enabled:
        return False, "mention_replies_disabled"
    if author_is_bot:
        return False, "bot_message"
    if opted_out:
        return False, "opt_out"
    if (channel_id not in policy.allowed_channel_ids and
            thread_id not in policy.allowed_thread_ids):
        return False, "outside_scope"
    if not mentions_bot(content, bot_user_id):
        return False, "not_mentioned"
    if seconds_since_last_reply < policy.cooldown_seconds:
        return False, "mention_cooldown"
    return True, "direct_mention"
