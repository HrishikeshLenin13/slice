"""
tokens.py — approximate token counting.

Uses tiktoken if it happens to be installed; otherwise falls back to a
chars/4 heuristic (a commonly-cited rough average for English/code text).
The fallback is clearly labeled as approximate in every report — do not
treat these numbers as exact model-specific token counts.
"""

from __future__ import annotations

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        return len(_ENC.encode(text))

    METHOD = "tiktoken(cl100k_base)"

except ImportError:
    def count_tokens(text: str) -> int:
        return max(1, len(text) // 4) if text else 0

    METHOD = "heuristic(chars/4, approximate)"
