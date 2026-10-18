"""Import smoke test for the local persona training environment.

No network, model weights, messages or training samples are accessed.
"""
from __future__ import annotations

import importlib
import sys

PACKAGES = ("numpy", "torch", "transformers", "peft", "trl",
            "accelerate", "bitsandbytes", "datasets")


def check(importer=importlib.import_module):
    failures = []
    for package in PACKAGES:
        try:
            importer(package)
        except Exception as exc:
            failures.append((package, type(exc).__name__, str(exc)[:200]))
    return failures


def main():
    failures = check()
    if failures:
        for name, error, detail in failures:
            print(f"IMPORT FAILED: {name}: {error}: {detail}", file=sys.stderr)
        return 1
    print("Training stack imports OK:", ", ".join(PACKAGES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
