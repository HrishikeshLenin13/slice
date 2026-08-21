"""
Slice: a static-analysis-driven context compiler for LLM coding agents.

Instead of retrieving "similar" text (embedding/RAG search), Slice computes
the exact transitive dependency closure a model needs to safely edit a given
symbol, using the same class of reachability analysis a compiler uses for
dead-code elimination. Where that analysis can't be closed statically
(dynamic dispatch, eval/exec, reflection, star-imports), Slice says so
explicitly instead of silently guessing.
"""

__version__ = "0.1.0"
