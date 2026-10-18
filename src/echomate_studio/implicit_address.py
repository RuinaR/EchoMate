"""Strict validation for implicit conversation addressee decisions."""
from __future__ import annotations
import json
from dataclasses import dataclass

@dataclass(frozen=True)
class ImplicitAddress:
    addressed_to_bot: bool
    topic_continues: bool

def parse_implicit_address(raw: str) -> ImplicitAddress:
    if not isinstance(raw, str):
        raise ValueError("response must be text")
    obj = json.loads(raw)
    if not isinstance(obj, dict) or set(obj) != {"addressed_to_bot", "topic_continues"}:
        raise ValueError("unexpected fields")
    if any(type(obj[k]) is not bool for k in obj):
        raise ValueError("values must be booleans")
    return ImplicitAddress(obj["addressed_to_bot"], obj["topic_continues"])
