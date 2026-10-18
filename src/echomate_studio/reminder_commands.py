"""Recognize explicit reminder management requests without assuming free-text intent."""
from __future__ import annotations
import re
from .reminders import ReminderStore

_LIST = frozenset(("내 예약 확인", "내 예약 보여줘", "예약 확인", "내 알림 확인", "예약 목록"))
_CANCEL_ALL = frozenset(("내 예약 전부 취소", "내 예약 모두 취소", "예약 전부 취소", "예약 모두 취소"))
_CANCEL_ONE = re.compile(r"(?:내\s*)?(?:예약|알림)\s*#?([1-9][0-9]*)\s*취소(?:해줘)?")

def handle_reminder_management(store: ReminderStore, *, content: str,
                               guild_id: int, channel_id: int, requester_id: int,
                               allowed_channels: frozenset[int]) -> dict:
    """Return structured result, never modify another person's reminders."""
    if channel_id not in allowed_channels:
        return {"status":"outside_scope"}
    text=content.strip()
    if text in _LIST:
        return {"status":"listed","reminders":store.list_pending(
            guild_id=guild_id,requester_id=requester_id)}
    if text in _CANCEL_ALL:
        return {"status":"cancelled_all","count":store.cancel_all(
            guild_id=guild_id,requester_id=requester_id)}
    match=_CANCEL_ONE.fullmatch(text)
    if match:
        done=store.cancel(guild_id=guild_id,requester_id=requester_id,
                          reminder_id=int(match.group(1)))
        return {"status":"cancelled" if done else "not_found"}
    return {"status":"not_supported"}
