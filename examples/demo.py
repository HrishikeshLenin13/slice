"""
demo.py — run this to see the whole pitch in ~10 lines of output:
a sound slice, an unsound one that's honestly flagged, and session reuse
across a second "turn" on the same target.

    python examples/demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slice_ctx.parser import parse_repo
from slice_ctx.graph import RepoGraph
from slice_ctx.slicer import slice_for, render_slice
from slice_ctx.session import Session
from slice_ctx.tokens import count_tokens, METHOD

REPO_ROOT = str(Path(__file__).resolve().parent.parent)
SOUND_TARGET = "tests.fixtures.sample_project.module_b.order_total"
UNSOUND_TARGET = "tests.fixtures.sample_project.module_b.dynamic_dispatch"


def main():
    modules, symbols = parse_repo(REPO_ROOT)
    graph = RepoGraph(modules, symbols)

    print(f"# token-count method: {METHOD}\n")

    print(f"## 1. A sound slice for `{SOUND_TARGET}`\n")
    result = slice_for(graph, SOUND_TARGET)
    print(render_slice(graph, result))
    print(f"\n-> sound={result.sound}, {len(result.included)} symbols included\n")
    print("=" * 72)

    print(f"\n## 2. An unsound slice for `{UNSOUND_TARGET}` — flagged, not guessed\n")
    result2 = slice_for(graph, UNSOUND_TARGET)
    print(f"sound={result2.sound}")
    for sid, reasons in result2.unsound_reasons.items():
        for r in reasons:
            print(f"  - {sid}: {r}")
    print("=" * 72)

    print("\n## 3. Session reuse: same target, two turns\n")
    session_path = "/tmp/slice_demo_session.json"
    Path(session_path).unlink(missing_ok=True)
    session = Session(session_path)

    turn1_tokens = 0
    for sid in result.included:
        sym = graph.symbols[sid]
        unit = session.get_context_unit(sym.id, sym.source)
        turn1_tokens += count_tokens(unit.payload)
    session.save()
    print(f"turn 1 (cold):  {turn1_tokens} tokens sent")

    session2 = Session(session_path)
    turn2_tokens = 0
    for sid in result.included:
        sym = graph.symbols[sid]
        unit = session2.get_context_unit(sym.id, sym.source)
        turn2_tokens += count_tokens(unit.payload)
    print(f"turn 2 (nothing changed): {turn2_tokens} tokens sent")


if __name__ == "__main__":
    main()
