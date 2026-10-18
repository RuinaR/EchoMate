"""Model proposals are data. Only this deterministic gate authorizes an action."""
from dataclasses import dataclass
from enum import Enum
import json
import re


class Kind(str,Enum):
    SILENCE="SILENCE"
    TEXT="TEXT"
    REACTION="REACTION"
    TEXT_REACTION="TEXT_REACTION"
    STICKER="STICKER"
    MEDIA="MEDIA"
    TEXT_MEDIA="TEXT_MEDIA"


@dataclass(frozen=True)
class Action:
    kind: Kind
    text: str=""
    asset: str=""


def parse_action(raw):
    fenced=re.fullmatch(r"\s*```(?:json)?\s*\n?([\s\S]*?)\n?```\s*",raw)
    if fenced:raw=fenced.group(1)
    d=json.loads(raw)
    if not isinstance(d,dict) or set(d)!={"kind","text","asset"} or any(not isinstance(v,str) for v in d.values()):
        raise ValueError("Invalid action proposal")
    return Action(Kind(d["kind"]),d["text"],d["asset"])


def validate_action(action,cfg,mode,permissions,catalog,library,guild_id):
    if action.kind in {Kind.MEDIA,Kind.TEXT_MEDIA}:return False
    if mode=="silent" or not permissions.get("view",False):return False
    if action.kind==Kind.SILENCE:return True
    text=action.kind in {Kind.TEXT,Kind.TEXT_REACTION,Kind.TEXT_MEDIA}
    react=action.kind in {Kind.REACTION,Kind.TEXT_REACTION}
    media=action.kind in {Kind.MEDIA,Kind.TEXT_MEDIA}
    sticker=action.kind==Kind.STICKER
    if mode=="reaction" and action.kind!=Kind.REACTION:return False
    if text and (not cfg["text"] or not permissions.get("send",False) or not action.text or len(action.text)>1900):return False
    # A small defense in depth, not a comprehensive personal-data detector.
    if text and re.search(r"(?:hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|-----BEGIN .*PRIVATE KEY)",action.text):return False
    if react and (not cfg["reactions"] or not permissions.get("react",False) or action.asset not in catalog.get("reactions",{}) or '<' in action.asset or re.search(r'\d{8,}',action.asset)):return False
    if sticker and (not cfg["stickers"] or not permissions.get("send",False) or action.asset not in catalog.get("stickers",{})):return False
    if not (react or media or sticker) and action.asset:return False
    if not text and action.text:return False
    return True
