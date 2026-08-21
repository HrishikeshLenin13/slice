"""
soundness.py — flags constructs that make static call-graph resolution
unreliable, so the slicer can say "I can't guarantee this is complete"
instead of silently under-including.

This is deliberately conservative: it is fine to over-flag (fall back to
full-file context more often than strictly necessary). It must never
under-flag, because a missed dynamic-dispatch site is exactly the failure
mode this project exists to rule out.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

DYNAMIC_BUILTINS = {"eval", "exec", "getattr", "setattr", "delattr", "globals", "locals", "vars"}
DYNAMIC_ATTR_HOOKS = {"__getattr__", "__setattr__", "__getattribute__", "__call__"}
DYNAMIC_IMPORT_CALLS = {"import_module", "__import__"}


@dataclass
class SoundnessReport:
    sound: bool = True
    reasons: list[str] = field(default_factory=list)

    def flag(self, reason: str) -> None:
        self.sound = False
        self.reasons.append(reason)


def check_function(node: ast.AST) -> SoundnessReport:
    """Scan a single function/method body for constructs that break static
    call-graph resolution. Returns a report; sound=False means "do not trust
    the computed slice for this symbol without a human/full-file fallback."
    """
    report = SoundnessReport()

    # First pass: find local variables bound to a subscript expression
    # (`handler = HANDLERS[action]`) — the classic dispatch-table pattern.
    # A later call through one of these names is a dynamic dispatch even
    # though the call site itself is a plain `Name` call, so a single-pass
    # walk over Call nodes alone would miss it.
    subscript_bound_names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Assign) and isinstance(child.value, ast.Subscript):
            for t in child.targets:
                if isinstance(t, ast.Name):
                    subscript_bound_names.add(t.id)

    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            callee = child.func
            if isinstance(callee, ast.Name) and callee.id in DYNAMIC_BUILTINS:
                report.flag(f"call to builtin `{callee.id}()` at line {child.lineno} "
                            f"— target is not statically knowable")
            if isinstance(callee, ast.Attribute) and callee.attr in DYNAMIC_IMPORT_CALLS:
                report.flag(f"dynamic import via `.{callee.attr}()` at line {child.lineno}")
            # Direct call through a subscript: `TABLE[key](...)`
            if isinstance(callee, ast.Subscript):
                report.flag(f"call through a computed/subscripted callable at line "
                            f"{child.lineno} (e.g. dispatch table) — target not statically fixed")
            # Indirect: `handler = TABLE[key]` earlier, then `handler(...)`
            if isinstance(callee, ast.Name) and callee.id in subscript_bound_names:
                report.flag(f"call to `{callee.id}()` at line {child.lineno} whose value came "
                            f"from a subscript lookup (dispatch table) — target not statically fixed")

        if isinstance(child, ast.FunctionDef) and child.name in DYNAMIC_ATTR_HOOKS:
            report.flag(f"defines `{child.name}` at line {child.lineno} — attribute "
                        f"access on instances of this class is not statically resolvable")

    return report


def check_module_star_imports(star_imports: list[str]) -> SoundnessReport:
    report = SoundnessReport()
    for mod in star_imports:
        report.flag(f"`from {mod} import *` — names entering this module's "
                     f"namespace are not statically enumerable")
    return report
