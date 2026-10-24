# Slice

**The first LLM context system that proves what it's leaving out, instead of guessing.**

Every context-compression tool that exists today — RAG rerankers, embedding
search, LLMLingua-style prompt compression, Cursor's own retrieval — treats
context selection as a *retrieval* problem: find the chunks that look most
relevant and send those. That's probabilistic. It optimizes for "similar,"
not "necessary," and it never tells you when the guess might be wrong.

Slice treats context selection as a **compiler problem** instead. When an
agent needs to edit `foo()`, Slice doesn't search for text that looks like
`foo()` — it parses the codebase into a dependency graph and computes the
exact transitive closure of symbols `foo()` can actually touch: its
callees, its callers, the types it references, the globals it reads. This
is the same class of reachability analysis a compiler runs for dead-code
elimination, applied to prompt construction instead of codegen.

Where that analysis can't be closed statically — dynamic dispatch,
`eval`/`exec`, `getattr` with a runtime name, `from x import *` — Slice
says so explicitly instead of silently omitting the true dependency. That
honesty is the actual contribution here, not the compression ratio.

## Quickstart

```bash
git clone https://github.com/HrishikeshLenin13/slice.git
cd slice
python -m unittest discover -s tests -v   # 20 tests, stdlib only, no install needed

python examples/demo.py                    # the whole pitch in ~30 lines of output
```

Or as a CLI against your own repo:

```bash
python -m slice_ctx analyze /path/to/repo --target pkg.module.ClassName.method
```

```
target: pkg.module.ClassName.method
sound: True
included: 6 symbols (2 callees, 1 callers, 1 types, 1 globals)
tokens [heuristic(chars/4, approximate)]: slice=329  naive_full_file=523  reduction=37.1%
```

Add `--session .slice_session.json` and re-run on a later turn: files whose
content hasn't changed since last sent report `unchanged` and cost zero
tokens; changed files send a unified diff instead of a full resend.

Save a text or JSON report with `--output report.json --json`. The default remains stdout.

## How it works

**1. Dependency-graph slicing, not embedding search** (`parser.py`,
`graph.py`, `slicer.py`). The codebase is parsed into an AST-derived symbol
table, then a call graph is built via best-effort static name resolution:
same-module names resolve directly, imported names resolve through each
module's explicit import map, `self.foo()` resolves against the enclosing
class (and its statically-known bases), and `var.foo()` resolves when
`var`'s type is inferable from a parameter annotation or a local
`var = ClassName(...)`. Given a target symbol, `slicer.py` walks the graph
outward — callees transitively, callers at the call-site level, every
class in a type position, every global actually read — and returns exactly
that closure, nothing more.

**2. A soundness certificate, not a confidence score** (`soundness.py`).
Every function in a slice is scanned for constructs that break static
resolution: `eval`/`exec`, `getattr`/`setattr` with computed names,
dispatch through a subscripted table (`HANDLERS[key](...)`, including the
indirect form where the lookup and the call are on different lines),
`globals()`/`locals()`, `__getattr__`/`__call__` overrides, and unresolvable
star-imports. A slice is `sound: True` only if *every* symbol it pulled in
passed this check. The checker is deliberately conservative — false
positives (flagging safe code) are acceptable, false negatives (missing a
real dynamic-dispatch site) are the one failure mode this project exists
to rule out. See [Honest limitations](#honest-limitations) below for what
that conservatism costs in practice.

**3. Diff-based context across turns, not full-file resends**
(`session.py`). A session cache stores a content hash per file. On repeat
requests: unchanged content costs a few marker tokens, changed content
sends a `difflib` unified diff instead of the whole file again — the same
idea git/rsync use for not re-transmitting unchanged bytes, applied to
prompt construction.

**4. Model-agnostic by construction.** All of the above happens in the
context-assembly layer, before anything reaches a model. It works
identically whichever backend consumes the output.

## Honest limitations

This is worth stating plainly rather than burying:

- **Python only, for now.** The AST parsing and resolution are
  Python-specific. The graph/slicer/session/soundness architecture doesn't
  assume Python, but a real second-language front-end (e.g. via
  tree-sitter) hasn't been built.
- **"Best-effort name resolution," not a type checker.** Cross-module
  resolution follows explicit imports; it doesn't do full type inference.
  `var.method()` resolves when `var`'s type is evident from a parameter
  annotation or a local `var = ClassName(...)` — anything requiring real
  flow-sensitive type inference falls through to `unresolved_calls`
  (reported, not hidden) rather than a guess.
- **The soundness checker over-flags on purpose, and that's visible in the
  numbers.** Running `benchmarks/bench_tokens.py` against this repo's own
  source: 66 functions/methods, **mean token reduction 66.6%, median
  67.7%**, and **48/66 (73%) certified sound**. The other 27% are flagged
  almost entirely because `parser.py` and `graph.py` use
  `getattr(node, "lineno", 1)`-style *safe, default-valued* lookups — which
  are harmless in practice but syntactically identical to genuinely dynamic
  dispatch, so the checker (correctly, per its own stated policy) flags
  them anyway rather than trying to distinguish "safe" getattr from
  "unsafe" getattr. That's the trade-off stated above, made visible on the
  project's own code instead of asserted in the abstract.
- **No end-to-end agent-loop benchmark yet.** `benchmarks/bench_tokens.py`
  measures the compression claim directly (slice tokens vs. naive
  full-file-dump tokens) and is the number quoted above. It does **not**
  measure edit-quality or task success — an actual SWE-bench-style
  comparison (does an agent using Slice-selected context succeed as often
  as one given the naive baseline, at what fraction of the tokens) would
  require wiring this into a real agent harness, which hasn't been done.
  The architecture here (a `SliceResult` with an explicit `sound` flag) is
  built specifically so that comparison is easy to run later — it just
  isn't a claim this README makes yet.

## Project layout

```
slice_ctx/
  parser.py      AST parsing -> Symbol table
  graph.py       best-effort static resolution -> call/type/global graph
  soundness.py   dynamic-construct detection (the certificate logic)
  slicer.py      graph traversal -> minimal closure for a target symbol
  session.py     content-hash cache -> diff-based reuse across turns
  tokens.py      token counting (tiktoken if available, else an approximation)
  cli.py         `python -m slice_ctx analyze ...`
tests/
  test_slicer.py            20 tests, stdlib unittest, no dependencies
  fixtures/sample_project/  a small project with a sound target and two
                             deliberately-unsound ones (dispatch table,
                             getattr) used throughout the tests
benchmarks/
  bench_tokens.py  the reduction/soundness numbers quoted above, on any repo
examples/
  demo.py          the whole pitch, runnable, no arguments needed
```

## Why this project

It reuses two areas of prior, real work rather than starting cold: AST/IR
parsing (from Helix) and graph-traversal algorithms (from Atlas). It's
benchmarkable on its own terms — token reduction and soundness rate are
both concrete, reproducible numbers, not vibes. And the specific claim —
*a slice that certifies its own completeness where it can, and admits when
it can't* — isn't something the existing RAG/embedding-search tools in
this space do; they compress and hope.

## License

MIT — see [LICENSE](LICENSE).
