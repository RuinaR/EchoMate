"""Pure policy gate for future Discord reactions; no live Discord access."""
from __future__ import annotations

from dataclasses import dataclass, field
import random
import re

CUSTOM = re.compile(r"<a?:[^:>]+:\d+>")
# A small conservative default set of common Unicode emoji; customizable within Unicode.
DEFAULT_EMOJIS = ("😂", "👍", "❤️", "😭", "😮", "🎉", "😄")


@dataclass(frozen=True)
class ReactionPolicy:
    enabled: bool = False
    allowed_channel_ids: frozenset[int] = field(default_factory=frozenset)
    allowed_thread_ids: frozenset[int] = field(default_factory=frozenset)
    probability: float = 0.08
    cooldown_seconds: float = 300.0
    emojis: tuple[str, ...] = DEFAULT_EMOJIS

    def __post_init__(self) -> None:
        if not 0 <= self.probability <= 1:
            raise ValueError("reaction probability must be between 0 and 1")
        if self.cooldown_seconds < 0:
            raise ValueError("reaction cooldown must not be negative")
        if any(not emoji or CUSTOM.search(emoji) for emoji in self.emojis):
            raise ValueError("custom Discord emojis are forbidden")


def choose_reaction(policy: ReactionPolicy, *, channel_id: int, thread_id: int | None,
                    is_bot_message: bool, is_own_message: bool,
                    opted_out: bool, seconds_since_reaction: float,
                    rng: random.Random | None = None) -> str | None:
    """Probability gate; call once per eligible incoming message. Never sends anything."""
    if not policy.enabled or is_bot_message or is_own_message or opted_out:
        return None
    if channel_id not in policy.allowed_channel_ids and thread_id not in policy.allowed_thread_ids:
        return None
    if seconds_since_reaction < policy.cooldown_seconds or not policy.emojis:
        return None
    generator = rng or random.Random()
    if generator.random() >= policy.probability:
        return None
    return generator.choice(policy.emojis)
