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
    return value.strip()


def build_messages(context: list[dict], *, style: str = "짧고 편안한 한국어 구어체",
                   history_limit: int = 16) -> list[dict]:
    if history_limit < 1:
        raise ValueError("history_limit must be positive")
    if not context:
        raise ValueError("context must include a user message")
    system = (
        "너는 EchoMate라는 AI 디스코드 봇이다. 사람이거나 실제 대화 참여자인 척하지 않는다. "
        "아래 입력을 현재 대화 상황으로 이해하고 그 내용에 맞게 자연스럽게 답하라. "
        "사실을 꾸며내지 마라. 출력은 텍스트와 일반 유니코드 이모지만 사용한다. "
        "URL, GIF, 스티커, 커스텀 디스코드 이모지, 파일 첨부, 이미지 마크다운을 사용하지 마라. "
        f"목표 답변 스타일: {style}"
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
    raw = chat(build_messages(context, style=style), model=model, base_url=base_url)
    return sanitize_output(raw)
