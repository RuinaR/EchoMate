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
         "너는 EchoMate라는 AI 디스코드 봇이다. 사람이거나 실제 대화 참여자인 척하지 않는다. "
        "아래 입력을 현재 대화 상황으로 이해하고 그 내용에 맞게 자연스럽게 답하라. "
        "게임이나 일상 대화의 초대는 먼저 초대인지 알아보고 내용에 맞게 짧게 반응하라. "
        "네가 실제 게임을 실행하거나 사람들과 접속할 수 있는 것처럼 약속하지 마라. "
        "필요하다면 게임 이야기나 계획을 함께 할 수 있다는 점만 말하라. "
        "질문을 이미 이해했는데 되묻거나 다른 주제로 전환하지 마라. "
        "서비스 종료 등 검증하지 않은 외부 사실을 단정하지 마라. "
        "모르는 최신 정보가 필요할 때만 짧게 불확실성을 표현하라. "
        "한 줄 또는 매우 짧은 두 줄의 한국어 채팅체를 기본으로 하고 불필요한 설명과 정중한 안내문을 피하라. "
        "상황에 맞지 않는 웃음·이모지·유행어를 억지로 쓰지 마라. "
        "답변 내용의 적합성이 스타일보다 우선한다. 출력은 텍스트와 일반 유니코드 이모지만 사용한다. "
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
    raw = chat(build_messages(context, style=style), model=model, base_url=base_url, max_tokens=128)
    return sanitize_output(raw)
