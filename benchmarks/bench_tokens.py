"""
bench_tokens.py — walks every function/method in a repo, computes its
slice, and compares slice-token-count against the naive full-file-dump
baseline a RAG-style tool would send. Prints a summary table.

This is a token-count benchmark, not an edit-quality benchmark: it
measures the compression claim directly and honestly. It does *not*
claim SWE-bench-style task-success numbers — wiring this into an actual
agent loop (so "did the edit succeed" can be measured against a slice vs.
a naive baseline) is exactly the kind of follow-on evaluation this repo
is structured to support, but it hasn't been run, and the README does not
claim otherwise.

Usage:
    python benchmarks/bench_tokens.py <repo_root>
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slice_ctx.parser import parse_repo
from slice_ctx.graph import RepoGraph
from slice_ctx.slicer import slice_for, render_slice
from slice_ctx.tokens import count_tokens, METHOD


def run(repo_root: str) -> None:
    modules, symbols = parse_repo(repo_root)
    graph = RepoGraph(modules, symbols)

    targets = [sid for sid, s in symbols.items() if s.kind in ("function", "method")]
    if not targets:
        print("no functions/methods found under", repo_root)
        return

    file_cache: dict[str, str] = {}
    rows = []
    for sid in sorted(targets):
        result = slice_for(graph, sid)
        rendered = render_slice(graph, result)
        slice_tok = count_tokens(rendered)

        files = set()
        for included_sid in result.included:
            files.add(graph.symbols[included_sid].file_path)
        for fp in files:
            if fp not in file_cache:
                with open(fp, "r", encoding="utf-8") as f:
                    file_cache[fp] = f.read()
        naive_text = "\n".join(file_cache[fp] for fp in files)
        naive_tok = count_tokens(naive_text)

        reduction = 100 * (1 - slice_tok / naive_tok) if naive_tok else 0.0
        rows.append((sid, slice_tok, naive_tok, reduction, result.sound))

    print(f"token method: {METHOD}\n")
    print(f"{'symbol':<70} {'slice':>8} {'naive':>8} {'reduction':>10} {'sound':>6}")
    print("-" * 106)
    for sid, slice_tok, naive_tok, reduction, sound in rows:
        short = sid if len(sid) <= 70 else "…" + sid[-69:]
        print(f"{short:<70} {slice_tok:>8} {naive_tok:>8} {reduction:>9.1f}% {str(sound):>6}")

    reductions = [r[3] for r in rows]
    sound_count = sum(1 for r in rows if r[4])
    print("-" * 106)
    print(f"n={len(rows)}  mean reduction={statistics.mean(reductions):.1f}%  "
          f"median={statistics.median(reductions):.1f}%  "
          f"sound={sound_count}/{len(rows)} ({100*sound_count/len(rows):.0f}%)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python benchmarks/bench_tokens.py <repo_root>")
        raise SystemExit(1)
    run(sys.argv[1])
