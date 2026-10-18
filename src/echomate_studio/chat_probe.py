"""Manual local baseline chat probe; prints only the reply, never raw context logs."""
from __future__ import annotations

import argparse
import time
import json
from pathlib import Path

from .style_profile import profile_to_style

from .conversation import generate
from .ollama_client import OllamaError


def main() -> None:
    p = argparse.ArgumentParser(description="EchoMate local Ollama baseline")
    p.add_argument("--model", default="qwen3.5:9b-q4_K_M")
    p.add_argument("--base-url", default="http://127.0.0.1:11434")
    p.add_argument("--style", default="짧고 자연스러운 한국어 채팅체, 과한 존댓말이나 장문은 피함")
    p.add_argument("--profile", type=Path, help="Aggregate local style-profile JSON")
    p.add_argument("--timing", action="store_true", help="Print total generation time in seconds")
    p.add_argument("--message", required=True, help="Local test input; not sent to Discord")
    args = p.parse_args()
    try:
        style = profile_to_style(json.loads(args.profile.read_text(encoding="utf-8"))) if args.profile else args.style
        start = time.perf_counter()
        result = generate([{"role": "user", "content": args.message}],
                          style=style, model=args.model, base_url=args.base_url)
    except (OllamaError, ValueError, OSError, KeyError, TypeError) as exc:
        p.exit(1, f"Local baseline failed: {exc}\n")
    print(result)
    if args.timing:
        print(f"[local_generation_seconds={time.perf_counter() - start:.2f}]")


if __name__ == "__main__":
    main()
