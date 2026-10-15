"""
session.py — the second half of the cost story: once a file has been sent
to the model once in a session, never resend it in full again. Track a
content hash per file; on the next request, either say "unchanged" (a few
tokens) or send a unified diff since last seen (typically far fewer tokens
than the whole file), and update the cache.

This mirrors how git/rsync avoid re-transmitting unchanged bytes — applied
to LLM context instead of network transfer.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, asdict


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class ContextUnit:
    file_path: str
    status: str          # "new" | "unchanged" | "changed"
    hash: str
    payload: str          # full content ("new"), "" ("unchanged"), or unified diff ("changed")


class Session:
    """Persists to a JSON file so context state survives across separate
    CLI invocations / agent turns, not just within one process."""

    def __init__(self, path: str):
        self.path = path
        self._state: dict[str, dict] = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError):
                saved = {}
            # A cache is expendable; corrupted entries must trigger full
            # context instead of crashing or falsely suppressing changed code.
            if isinstance(saved, dict):
                for file_path, entry in saved.items():
                    if not isinstance(entry, dict):
                        continue
                    content = entry.get("content")
                    if isinstance(content, str) and entry.get("hash") == _hash(content):
                        self._state[file_path] = {"hash": entry["hash"], "content": content}

    def save(self) -> None:
        # Replace only after a complete write, so an interrupted/failed save
        # never truncates the last successful session. Keep the temp file on
        # the same filesystem for atomic os.replace semantics.
        directory = os.path.dirname(os.path.abspath(self.path))
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=directory,
                prefix=".slice-session-", delete=False,
            ) as f:
                temp_path = f.name
                json.dump(self._state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.path)
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)

    def get_context_unit(self, file_path: str, content: str) -> ContextUnit:
        h = _hash(content)
        prior = self._state.get(file_path)

        if prior is None:
            self._state[file_path] = {"hash": h, "content": content}
            return ContextUnit(file_path, "new", h, content)

        if prior["hash"] == h:
            return ContextUnit(file_path, "unchanged", h, "")

        old_content = prior.get("content", "")
        diff = "".join(difflib.unified_diff(
            old_content.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"{file_path} (last seen)",
            tofile=f"{file_path} (now)",
        ))
        self._state[file_path] = {"hash": h, "content": content}
        return ContextUnit(file_path, "changed", h, diff)

    def as_dict(self) -> dict:
        return {k: {"hash": v["hash"]} for k, v in self._state.items()}
