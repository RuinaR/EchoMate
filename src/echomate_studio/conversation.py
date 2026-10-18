"""Local text-only baseline: context from current chat, style from explicit settings."""
from __future__ import annotations

import re

from .ollama_client import chat

CUSTOM_EMOJI = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
MEDIA_LINK = re.compile(r"https?://\S+", re.I)
IMAGE_MD = re.compile(r"!\[[^]]*\]\([^)]*\)")
MENTION = re.compile(r"<@!?\d+>")


def sanitize_output(value: str) -> str:
    """Enforce no Discord custom emojis, links, mentions or media markup."""
    for pattern in (IMAGE_MD, CUSTOM_EMOJI, MEDIA_LINK, MENTION):
        value = pattern.sub("", value)
    # Control codes (excluding line feeds/tabs) must not reach Discord.
    value = "".join(c for c in value if c in "\n\t" or ord(c) >= 32)
    return re.sub(r"[^\S\n]+", " ", value).strip()


def build_messages(context: list[dict], *, style: str = "짧고 편안한 한국어 구어체",
                   history_limit: int = 16) -> list[dict]:
    if history_limit < 1:
        raise ValueError("history_limit must be positive")
    if not context:
        raise ValueError("context must include a user message")
    system = (
        "너는 Discord에서 활동하는 EchoMate AI 봇이다. 현재 대화에 자연스럽게 반응하되 "
        "스스로 실제 게임을 실행하거나 접속할 수 있는 것처럼 말하지 마라. "
        "말투와 별개로 질문의 의도, 이전 대화에서 결정된 사항, 누구에게 하는 말인지부터 판단하라. "
        "상대가 단순히 웃거나 맞장구치면 과도하게 분석하거나 장황한 안내를 하지 마라. "
        "확인하지 못한 현실 사실은 꾸며내지 말고, 질문에 답할 정보가 충분하면 쓸데없이 되묻지 마라. "
        "기본은 친근한 한국어 채팅체의 짧은 한 문장이다. "
        "실제 내용이 복잡할 때만 필요한 만큼 설명하고 이모지나 유행어를 억지로 쓰지 마라. "
        "URL, 미디어, Discord 커스텀 이모지, 스티커, 첨부파일을 출력하지 마라. "
        f"말투 참고사항(내용·사실보다 우선하지 않음): {style}"
    )
    trimmed = context[-history_limit:]
    for msg in trimmed:
        if msg.get("role") not in {"user", "assistant"} or not isinstance(msg.get("content"), str):
            raise ValueError("invalid context message")
    if trimmed[-1]["role"] != "user":
        raise ValueError("latest context message must be user")
    return [{"role": "system", "content": system}, *trimmed]


def generate(context: list[dict], *, style: str = "짧고 편안한 한국어 구어체",
             model: str = "qwen3.5:9b-q4_K_M",
             base_url: str = "http://127.0.0.1:11434") -> str:
    raw = chat(build_messages(context, style=style), model=model, base_url=base_url, max_tokens=128)
    return sanitize_output(raw)
