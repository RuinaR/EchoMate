"""Conservative automated flags for human-reviewed conversation QA.

Heuristics are advisory: they cannot determine semantic correctness.
"""
from __future__ import annotations
import re


def inspect_reply(prompt: str, reply: str) -> list[str]:
    flags: list[str] = []
    value = reply.strip()
    if not value:
        return ["empty_reply"]
    if len(value) > 120 and len(prompt) < 35:
        flags.append("overlong_for_short_prompt")
    if re.search(r"(들어올게|접속할게|게임.*(실행할게|들어갈게)|같이.*플레이할게)", value):
        flags.append("possible_physical_gameplay_claim")
    if re.search(r"(서비스.*(종료|중단)|공식적으로.*서비스되지)", value):
        flags.append("unverified_service_status_claim")
    if re.search(r"(무슨 게임|게임하자|누구랑 게임)", value) and re.search(r"(힘들|속상|지쳤)", prompt):
        flags.append("possible_topic_drift")
    if re.search(r"[\U0001F300-\U0001FAFF]", value):
        flags.append("unicode_emoji_present")
    return flags
