"""Offline manual probe of dialogue-based silence decisions (no Discord API)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone

from .context_assessor import assess
from .dialogue_state import DialogueState, Turn
from .participation import ParticipationPolicy, decide


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3.5:9b-q4_K_M")
    parser.add_argument("--message", action="append", required=True,
                        help="Repeated synthetic sample chat lines; only local Ollama is called")
    args = parser.parse_args()
    state = DialogueState()
    now = datetime.now(timezone.utc)
    for index, text in enumerate(args.message):
        state.append(channel_id=1, thread_id=None, turn=Turn(
            str(index), str(index % 2), text, now + timedelta(seconds=index)))
    _, context = state.recent_context(channel_id=1, thread_id=None,
                                       now=now + timedelta(seconds=len(args.message)))
    evaluation = assess(context, model=args.model)
    result = decide(
        ParticipationPolicy(enabled=True, allowed_channel_ids=frozenset({1}),
                            opportunity_probability=1.0, cooldown_seconds=0),
        evaluation, channel_id=1, thread_id=None, is_bot_message=False,
        opted_out=False, seconds_since_last_speech=3600,
        seconds_since_last_human_message=1)
    print(json.dumps({"assessment": evaluation.__dict__,
                      "speak": result.speak, "reason": result.reason.value},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
