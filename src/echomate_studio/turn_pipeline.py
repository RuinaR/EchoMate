"""Offline, testable orchestration of contextual bot speech.

No network events are received here. Caller re-checks the snapshot immediately
before sending. Fail closed on stale state or model/assessment errors.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .dialogue_state import DialogueState
from .participation import ParticipationPolicy, ContextAssessment, Decision, decide
from .conversation import sanitize_output
from .mention_reply import MentionPolicy, mentions_bot, permit_mention_reply
from .engagement import EngagementPolicy, continue_engagement


@dataclass(frozen=True)
class TurnResult:
    reply: str | None
    reason: str
    version: int


def evaluate_turn(*, state: DialogueState, policy: ParticipationPolicy,
                  channel_id: int, thread_id: int | None,
                  now: datetime, seconds_since_last_speech: float,
                  seconds_since_last_human_message: float,
                  assessor: Callable[[list[dict]], ContextAssessment],
                  generator: Callable[[list[dict]], str],
                  rng=None, mention_policy: MentionPolicy | None = None,
                  bot_user_id: int | None = None,
                  latest_message_content: str | None = None,
                  author_is_bot: bool = False, opted_out: bool = False,
                  engagement_policy: EngagementPolicy | None = None,
                  ongoing_engagement: bool = False,
                  addressed_to_bot: bool = False,
                  topic_continues: bool = False) -> TurnResult:
    version, context = state.recent_context(channel_id=channel_id, thread_id=thread_id, now=now)
    if not context or context[-1]["role"] != "user":
        return TurnResult(None, "no_recent_human_context", version)
    # A verified direct mention bypasses autonomous chance and inactivity only.
    # Scope, opt-out and safety assessment still apply; no Discord send here.
    directed = False
    if (mention_policy is not None and bot_user_id is not None
            and latest_message_content is not None
            and mentions_bot(latest_message_content, bot_user_id)):
        directed, reason = permit_mention_reply(
            mention_policy, content=latest_message_content,
            bot_user_id=bot_user_id, channel_id=channel_id, thread_id=thread_id,
            author_is_bot=author_is_bot, opted_out=opted_out,
            seconds_since_last_reply=seconds_since_last_speech)
        if not directed:
            return TurnResult(None, reason, version)
    continuing = False
    if not directed and engagement_policy is not None:
        continuing = continue_engagement(
            engagement_policy, ongoing=ongoing_engagement,
            seconds_since_last_bot_reply=seconds_since_last_speech,
            addressed_to_bot=addressed_to_bot, topic_continues=topic_continues)
        if continuing and (author_is_bot or opted_out or (
            channel_id not in policy.allowed_channel_ids and
            thread_id not in policy.allowed_thread_ids)):
            return TurnResult(None, "engagement_outside_scope", version)
    if not directed and not continuing:
        preliminary = decide(policy, ContextAssessment(False, True, True),
                             channel_id=channel_id, thread_id=thread_id,
                             is_bot_message=author_is_bot, opted_out=opted_out,
                             seconds_since_last_speech=seconds_since_last_speech,
                             seconds_since_last_human_message=seconds_since_last_human_message,
                             rng=rng)
        if not preliminary.speak:
            return TurnResult(None, preliminary.reason.value, version)
    try:
        assessment = assessor(context)
    except Exception:
        return TurnResult(None, "assessor_error", version)
    if not isinstance(assessment, ContextAssessment):
        return TurnResult(None, "invalid_assessment", version)
    if assessment.is_sensitive_moment or (not directed and not assessment.has_useful_contribution) or (
            not directed and not continuing and not assessment.interruption_is_appropriate):
        return TurnResult(None, "context_veto", version)
    if not state.is_current(channel_id=channel_id, thread_id=thread_id, version=version):
        return TurnResult(None, "stale_before_generation", version)
    try:
        reply = sanitize_output(generator(context))
    except Exception:
        return TurnResult(None, "generation_error", version)
    if not reply:
        return TurnResult(None, "empty_response", version)
    if not state.is_current(channel_id=channel_id, thread_id=thread_id, version=version):
        return TurnResult(None, "stale_after_generation", version)
    return TurnResult(reply[:1900], "direct_mention_ready" if directed else ("engaged_ready" if continuing else "ready"), version)
