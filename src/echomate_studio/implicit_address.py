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

def assess_implicit_address(turns, *, model="gemma3:12b", base_url="http://127.0.0.1:11434") -> ImplicitAddress:
    """Classify only when a bot has participated and latest message lacks reply_to."""
    from .ollama_client import chat, OllamaError
    fail = ImplicitAddress(False, False)
    if len(turns) < 2 or turns[-1].is_bot or turns[-1].reply_to:
        return fail
    recent = turns[-12:]
    if not any(t.is_bot for t in recent[:-1]):
        return fail
    lines = [("EchoMate" if t.is_bot else "participant") + ": " + t.content[:400] for t in recent]
    instruction = (
        "Return JSON with exactly two boolean keys addressed_to_bot and topic_continues. "
        "Judge whether the latest human message addresses EchoMate and continues the same topic. "
        "Mere proximity or a recent bot message is not proof. When unsure return both false."
    )
    try:
        raw = chat([{"role":"system","content":instruction},
                    {"role":"user","content":"\\n".join(lines)}],
                   model=model,base_url=base_url,temperature=0.0,max_tokens=100)
        return parse_implicit_address(raw)
    except (OllamaError, ValueError, TypeError, KeyError):
        return fail
