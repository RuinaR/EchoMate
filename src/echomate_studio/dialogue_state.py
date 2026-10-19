"""Bounded per-channel dialogue continuity; no Discord network or long-term profiles."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque
import json


@dataclass(frozen=True)
class Turn:
    message_id: str
    author_id: str
    content: str
    timestamp: datetime
    is_bot: bool = False
    reply_to: str | None = None
    context_metadata: str | None = None


class DialogueState:
    @staticmethod
    def context_metadata(turn,latest):
        if latest or not turn.context_metadata:return turn.context_metadata
        try:
            value=json.loads(turn.context_metadata)
            if not isinstance(value,dict):return turn.context_metadata
            value={k:v for k,v in value.items() if k not in ('configured_bot_name','bot_names')}
            return json.dumps(value,ensure_ascii=False) if value else None
        except ValueError:return turn.context_metadata
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

    def merge_actual(self,*,channel_id,thread_id,turns):
        """Merge only source-linked real turns from an explicitly shared flow."""
        key=(channel_id,thread_id);history=list(self._channels.get(key,()))
        actual={t.message_id:t for t in history}
        for turn in turns:actual.setdefault(turn.message_id,turn)
        if len(actual)==len(history):return
        merged=sorted(actual.values(),key=lambda t:t.timestamp)
        self._channels[key]=deque(merged);self._ids[key]=set(actual)
        self._versions[key]=self._versions.get(key,0)+1
        if merged:self._prune(key,merged[-1].timestamp)

    def change_message(self,*,channel_id,thread_id,message_id,content=None):
        """Invalidate in-flight snapshots; preserve unrelated actual history."""
        from dataclasses import replace
        key=(channel_id,thread_id)
        history=self._channels.get(key)
        if history is None:return
        self._channels[key]=deque(replace(t,content=content[:8000]) if t.message_id==message_id else t
                                  for t in history if t.message_id!=message_id or content is not None)
        self._ids[key]={t.message_id for t in self._channels[key]}
        self._versions[key]=self._versions.get(key,0)+1

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
            cost = len(turn.content) + len(turn.author_id) + 64 + len(self.context_metadata(turn,not selected) or '')
            if selected and used + cost > budget:
                break
            if not selected and cost > budget:
                extra=turn.context_metadata if len(turn.context_metadata or '')<max(0,budget-64) else None
                selected.append(Turn(turn.message_id, turn.author_id,
                                     turn.content[-max(1, budget - 64 - len(extra or '')):],
                                     turn.timestamp, turn.is_bot, turn.reply_to,extra))
                break
            selected.append(turn)
            used += cost
        return version, self.to_model_context(list(reversed(selected)))

    @staticmethod
    def to_model_context(turns: list[Turn]) -> list[dict[str, str]]:
        """Speaker labels prevent multi-user conversation from becoming one user monologue."""
        context = []
        for index,turn in enumerate(turns):
            role = "assistant" if turn.is_bot else "user"
            if turn.is_bot:
                content = turn.content
            else:
                content = f"[참여자 {turn.author_id}] {turn.content}"
                if turn.reply_to:
                    content = f"[답장 대상 메시지 {turn.reply_to}] " + content
            metadata=DialogueState.context_metadata(turn,index==len(turns)-1)
            if metadata:
                content+='\n[관측된 이벤트 메타데이터 / 실제 발언 인용이 아님] '+metadata
            context.append({"role": role, "content": content})
        return context
