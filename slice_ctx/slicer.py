"""
slicer.py — the core "compiler pass": given a target symbol, compute the
minimal set of other symbols the model needs to safely edit it, the way a
compiler computes live variables or reachable code, not the way a search
engine ranks similar documents.

Included by default:
  - the target itself
  - callees, transitively, up to `callee_depth` (default: unlimited)
  - direct callers (default: signature/call-site only, not full body —
    editing foo's internals doesn't require re-reading every caller's
    internals, only how they invoke foo)
  - every class referenced in type positions (annotations, instantiation,
    base classes) reachable from the above
  - every module-level global/constant read, reachable from the above

A slice is marked `sound=True` only if every symbol pulled into it (and the
target itself) passed the soundness check in soundness.py, and no module in
the closure has an unresolvable star-import. `sound=False` slices still
return their best-effort content, but come with an explicit
`unsound_reasons` list — the caller (agent harness) is expected to fall back
to full-file context for the flagged symbols/files rather than trust the
slice blindly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .graph import RepoGraph
from .parser import Symbol


@dataclass
class SliceResult:
    target: str
    included: list[str]                 # symbol ids, in a stable emission order
    callees: list[str]
    callers: list[str]
    type_refs: list[str]
    global_refs: list[str]
    sound: bool
    unsound_reasons: dict[str, list[str]] = field(default_factory=dict)  # symbol id -> reasons
    unresolved: dict[str, list[str]] = field(default_factory=dict)       # symbol id -> unresolved call names

    def symbols_in_order(self) -> list[str]:
        return self.included


def slice_for(
    graph: RepoGraph,
    target_id: str,
    *,
    callee_depth: int | None = None,
    caller_depth: int = 1,
) -> SliceResult:
    if target_id not in graph.symbols:
        raise KeyError(f"unknown symbol: {target_id!r}")

    callees: set[str] = set()
    frontier = {target_id}
    depth = 0
    while frontier:
        if callee_depth is not None and depth >= callee_depth:
            break
        nxt: set[str] = set()
        for sid in frontier:
            sym = graph.symbols[sid]
            for c in sym.calls:
                if c not in callees and c != target_id:
                    nxt.add(c)
        callees |= nxt
        frontier = nxt
        depth += 1

    callers: set[str] = set()
    frontier = {target_id}
    depth = 0
    while frontier:
        if depth >= caller_depth:
            break
        nxt = set()
        for sid in frontier:
            for c in graph.callers.get(sid, set()):
                if c not in callers and c != target_id:
                    nxt.add(c)
        callers |= nxt
        frontier = nxt
        depth += 1

    type_refs: set[str] = set()
    global_refs: set[str] = set()
    for sid in {target_id, *callees, *callers}:
        sym = graph.symbols[sid]
        type_refs |= sym.type_refs
        global_refs |= sym.global_refs
    # base classes of any referenced class also count as type context
    changed = True
    while changed:
        changed = False
        for tid in list(type_refs):
            tsym = graph.symbols.get(tid)
            if tsym and tsym.kind == "class":
                new_bases = tsym.bases - type_refs
                if new_bases:
                    type_refs |= new_bases
                    changed = True

    included_order = [target_id] + sorted(callees) + sorted(callers) + sorted(type_refs) + sorted(global_refs)
    # de-dup while preserving first-seen order
    seen = set()
    included = []
    for sid in included_order:
        if sid not in seen:
            seen.add(sid)
            included.append(sid)

    sound = True
    unsound_reasons: dict[str, list[str]] = {}
    unresolved: dict[str, list[str]] = {}
    for sid in included:
        if not graph.is_sound(sid):
            sound = False
            unsound_reasons[sid] = graph.soundness_reasons(sid)
        sym = graph.symbols[sid]
        if sym.unresolved_calls:
            unresolved[sid] = sorted(sym.unresolved_calls)

    return SliceResult(
        target=target_id,
        included=included,
        callees=sorted(callees),
        callers=sorted(callers),
        type_refs=sorted(type_refs),
        global_refs=sorted(global_refs),
        sound=sound,
        unsound_reasons=unsound_reasons,
        unresolved=unresolved,
    )


def render_slice(graph: RepoGraph, result: SliceResult, *, caller_signature_only: bool = True) -> str:
    """Render a slice as source text grouped by file, the way it would
    actually be handed to a model as context."""
    by_file: dict[str, list[Symbol]] = {}
    for sid in result.included:
        sym = graph.symbols[sid]
        by_file.setdefault(sym.file_path, []).append(sym)

    parts = []
    for file_path in sorted(by_file):
        parts.append(f"# --- {file_path} ---")
        for sym in sorted(by_file[file_path], key=lambda s: s.lineno):
            tag = "TARGET" if sym.id == result.target else sym.kind.upper()
            src = sym.source
            if (
                caller_signature_only
                and sym.id in result.callers
                and sym.id != result.target
                and sym.kind in ("function", "method")
            ):
                first_line = src.splitlines()[0] if src else ""
                src = first_line + "\n    ...  # (caller body omitted; only the call site matters here)"
            parts.append(f"\n# [{tag}] {sym.id}\n{src}")
    return "\n".join(parts)
