"""Bounded per-channel dialogue continuity; no Discord network or long-term profiles."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque


@dataclass(frozen=True)
class Turn:
    message_id: str
    author_id: str
    content: str
    timestamp: datetime
    is_bot: bool = False
    reply_to: str | None = None


class DialogueState:
    def __init__(self, *, limit: int = 500, max_age_seconds: int = 86400):
        if limit < 1 or max_age_seconds < 1:
            raise ValueError("limit and max age must be positive")
        self.limit = limit
        self.max_age_seconds = max_age_seconds
        self._channels: dict[tuple[int, int | None], Deque[Turn]] = {}
        self._ids: dict[tuple[int, int | None], set[str]] = {}
        self._versions: dict[tuple[int, int | None], int] = {}
        self._max_context_chars = 16000

    def append(self, *, channel_id: int, thread_id: int | None, turn: Turn) -> bool:
        if turn.timestamp.tzinfo is None:
            raise ValueError("timestamps must include timezone")
        key = (channel_id, thread_id)
        history = self._channels.setdefault(key, deque())
        ids = self._ids.setdefault(key, set())
        if turn.message_id in ids:
            return False
        # Never let an out-of-order old event rewind the current conversation.
        if history and turn.timestamp < history[-1].timestamp:
            return False
        history.append(turn)
        ids.add(turn.message_id)
        self._versions[key] = self._versions.get(key, 0) + 1
        self._prune(key, turn.timestamp)
        return True

    def _prune(self, key: tuple[int, int | None], now: datetime) -> None:
        history = self._channels[key]
        ids = self._ids[key]
        while history and (len(history) > self.limit or
                           (now - history[0].timestamp).total_seconds() > self.max_age_seconds):
            ids.remove(history.popleft().message_id)

    def snapshot(self, *, channel_id: int, thread_id: int | None,
                 now: datetime | None = None) -> tuple[int, list[Turn]]:
        key = (channel_id, thread_id)
        if key not in self._channels:
            return self._versions.get(key, 0), []
        at = now or datetime.now(timezone.utc)
        self._prune(key, at)
        return self._versions[key], list(self._channels[key])

    def is_current(self, *, channel_id: int, thread_id: int | None, version: int) -> bool:
        return self._versions.get((channel_id, thread_id), 0) == version

    def recent_context(self, *, channel_id: int, thread_id: int | None,
                       max_chars: int | None = None, now: datetime | None = None) -> tuple[int, list[dict[str, str]]]:
        """Build a bounded prompt window from the newest turns while keeping older RAM history."""
        budget = self._max_context_chars if max_chars is None else max_chars
        if budget < 1:
            raise ValueError("max_chars must be positive")
        version, turns = self.snapshot(channel_id=channel_id, thread_id=thread_id, now=now)
        selected: list[Turn] = []
        used = 0
        for turn in reversed(turns):
            cost = len(turn.content) + len(turn.author_id) + 64
            if selected and used + cost > budget:
                break
            if not selected and cost > budget:
                selected.append(Turn(turn.message_id, turn.author_id,
                                     turn.content[-max(1, budget - 64):],
                                     turn.timestamp, turn.is_bot, turn.reply_to))
                break
            selected.append(turn)
            used += cost
        return version, self.to_model_context(list(reversed(selected)))

    @staticmethod
    def to_model_context(turns: list[Turn]) -> list[dict[str, str]]:
        """Speaker labels prevent multi-user conversation from becoming one user monologue."""
        context = []
        for turn in turns:
            role = "assistant" if turn.is_bot else "user"
            if turn.is_bot:
                content = turn.content
            else:
                content = f"[참여자 {turn.author_id}] {turn.content}"
                if turn.reply_to:
                    content = f"[답장 대상 메시지 {turn.reply_to}] " + content
            context.append({"role": role, "content": content})
        return context
