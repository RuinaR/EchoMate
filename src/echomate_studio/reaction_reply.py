"""Choose one conversational response: text OR a Unicode reaction.

This pure decision layer does not call Discord and never sends both.
The caller supplies contextual engagement and a semantic emoji candidate.
"""
from __future__ import annotations
from dataclasses import dataclass
from .reactions import ReactionPolicy, CUSTOM

@dataclass(frozen=True)
class ResponseChoice:
    kind: str
    emoji: str | None = None

def choose_conversation_response(*, text_reply: str | None,
                                 suggested_emoji: str | None,
                                 ongoing_engagement: bool,
                                 addressed_to_bot: bool,
                                 topic_continues: bool,
                                 policy: ReactionPolicy,
                                 channel_id: int,
                                 thread_id: int | None,
                                 author_is_bot: bool = False,
                                 opted_out: bool = False) -> ResponseChoice:
    """An explicit, verified conversational reaction can replace a text reply.

    No randomness: model/context selector supplies an emoji or None.
    Unsupported Unicode candidates and opt-outs are rejected. Discord
    add-reaction permission and the outgoing message remain adapter concerns.
    """
    reaction_allowed = (policy.enabled and not author_is_bot and not opted_out
                        and (channel_id in policy.allowed_channel_ids
                             or thread_id in policy.allowed_thread_ids)
                        and ongoing_engagement and addressed_to_bot
                        and topic_continues)
    if (reaction_allowed and isinstance(suggested_emoji, str)
            and suggested_emoji in policy.emojis and not CUSTOM.search(suggested_emoji)):
        return ResponseChoice("reaction", suggested_emoji)
    if text_reply:
        return ResponseChoice("text")
    return ResponseChoice("silent")
