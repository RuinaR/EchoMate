"""Conservative autonomous participation gate.

Frequency controls chances to consider speaking, never an obligation to speak.
The caller supplies contextual assessments; this module makes the final
allow/silence decision without sending messages or calling an LLM.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random


class SilenceReason(str, Enum):
    DISABLED = "disabled"
    OUTSIDE_SCOPE = "outside_scope"
    BOT_MESSAGE = "bot_message"
    OPT_OUT = "opt_out"
    COOLDOWN = "cooldown"
    INACTIVE = "inactive"
    SENSITIVE = "sensitive_moment"
    NO_CONTRIBUTION = "no_useful_contribution"
    INTERRUPTION = "inappropriate_interruption"
    RANDOM_GATE = "frequency_gate"
    SPEAK = "speak"


@dataclass(frozen=True)
class ParticipationPolicy:
    enabled: bool = False
    allowed_channel_ids: frozenset[int] = frozenset()
    allowed_thread_ids: frozenset[int] = frozenset()
    # Probability only gates eligible opportunities, not mandatory responses.
    opportunity_probability: float = 0.2
    cooldown_seconds: float = 180.0
    max_idle_seconds: float = 1800.0

    def __post_init__(self):
        if not 0 <= self.opportunity_probability <= 1:
            raise ValueError("opportunity_probability must be 0..1")
        if self.cooldown_seconds < 0 or self.max_idle_seconds < 0:
            raise ValueError("time thresholds must be nonnegative")


@dataclass(frozen=True)
class ContextAssessment:
    # Produced by separate current-context assessor, not inferred historical profiles.
    is_sensitive_moment: bool = False
    has_useful_contribution: bool = False
    interruption_is_appropriate: bool = False


@dataclass(frozen=True)
class Decision:
    speak: bool
    reason: SilenceReason


def decide(policy: ParticipationPolicy, assessment: ContextAssessment, *,
           channel_id: int, thread_id: int | None, is_bot_message: bool,
           opted_out: bool, seconds_since_last_speech: float,
           seconds_since_last_human_message: float,
           rng: random.Random | None = None) -> Decision:
    def no(reason: SilenceReason) -> Decision:
        return Decision(False, reason)
    if not policy.enabled:
        return no(SilenceReason.DISABLED)
    if channel_id not in policy.allowed_channel_ids and thread_id not in policy.allowed_thread_ids:
        return no(SilenceReason.OUTSIDE_SCOPE)
    if is_bot_message:
        return no(SilenceReason.BOT_MESSAGE)
    if opted_out:
        return no(SilenceReason.OPT_OUT)
    if seconds_since_last_speech < policy.cooldown_seconds:
        return no(SilenceReason.COOLDOWN)
    if seconds_since_last_human_message > policy.max_idle_seconds:
        return no(SilenceReason.INACTIVE)
    # The following conditions veto speaking regardless of frequency.
    if assessment.is_sensitive_moment:
        return no(SilenceReason.SENSITIVE)
    if not assessment.has_useful_contribution:
        return no(SilenceReason.NO_CONTRIBUTION)
    if not assessment.interruption_is_appropriate:
        return no(SilenceReason.INTERRUPTION)
    if (rng or random.Random()).random() >= policy.opportunity_probability:
        return no(SilenceReason.RANDOM_GATE)
    return Decision(True, SilenceReason.SPEAK)
