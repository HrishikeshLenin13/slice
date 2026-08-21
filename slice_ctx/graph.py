"""
graph.py — resolves references *between* Symbols to build the dependency
graph the slicer walks.

Resolution strategy (deliberately simple and auditable, not full type
inference):
  1. Same-module names resolve directly against the module's symbol table.
  2. Imported names resolve via the module's explicit import map
     (`import x`, `from x import y`).
  3. `self.foo()` resolves against the enclosing class (and, best-effort,
     its statically-known bases).
  4. `var.foo()` resolves if `var` was assigned `ClassName(...)` earlier in
     the *same function body* (simple intra-procedural type hint).
  5. Anything else is left unresolved rather than guessed — an unresolved
     call is not the same as an *unsound* one (see soundness.py): it just
     means the graph has a gap, and the slicer will report that gap.

This is intentionally a "best-effort name resolution" pass, not a type
checker. It resolves the large majority of straight-line, non-dynamic
Python code correctly, which is exactly the subset the soundness pass
(soundness.py) certifies as safe to slice.
"""

from __future__ import annotations

import ast
import builtins

from .parser import ModuleInfo, Symbol
from .soundness import check_function, check_module_star_imports, SoundnessReport

BUILTIN_NAMES = set(dir(builtins))


def _flatten_annotation_names(node: ast.AST | None) -> list[str]:
    """Pull every bare Name out of a (possibly subscripted/generic) annotation,
    e.g. `Dict[str, Foo]` -> ['Dict', 'str', 'Foo']."""
    names: list[str] = []
    if node is None:
        return names
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.append(child.id)
        elif isinstance(child, ast.Attribute):
            names.append(child.attr)
    return names


def _assigned_names(fn_node: ast.AST) -> set[str]:
    """Approximate the set of local names bound within a function (params,
    assignment targets, comprehension vars, for-loop vars) so we don't
    mistake locals for module globals when resolving Name loads."""
    names: set[str] = set()
    if isinstance(fn_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for a in fn_node.args.args + fn_node.args.posonlyargs + fn_node.args.kwonlyargs:
            names.add(a.arg)
        if fn_node.args.vararg:
            names.add(fn_node.args.vararg.arg)
        if fn_node.args.kwarg:
            names.add(fn_node.args.kwarg.arg)
    for child in ast.walk(fn_node):
        if isinstance(child, ast.Assign):
            for t in child.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            names.add(child.target.id)
        elif isinstance(child, (ast.For, ast.AsyncFor)) and isinstance(child.target, ast.Name):
            names.add(child.target.id)
        elif isinstance(child, (ast.comprehension,)) and isinstance(child.target, ast.Name):
            names.add(child.target.id)
        elif isinstance(child, ast.With):
            for item in child.items:
                if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                    names.add(item.optional_vars.id)
    return names


def _local_type_hints(fn_node: ast.AST, resolve_name) -> dict[str, str]:
    """Best-effort intra-procedural type hints for `var.method()` resolution:
      - parameter annotations: `def f(cart: Cart)` -> {'cart': '<Cart id>'}
      - local instantiation: `var = ClassName(...)` -> {'var': '<Class id>'}
    """
    hints: dict[str, str] = {}

    if isinstance(fn_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for a in list(fn_node.args.args) + list(fn_node.args.posonlyargs) + list(fn_node.args.kwonlyargs):
            if a.annotation is not None:
                for n in _flatten_annotation_names(a.annotation):
                    sid = resolve_name(n)
                    if sid:
                        hints[a.arg] = sid
                        break

    for child in ast.walk(fn_node):
        if isinstance(child, ast.Assign) and isinstance(child.value, ast.Call):
            callee = child.value.func
            if isinstance(callee, ast.Name):
                sid = resolve_name(callee.id)
                if sid:
                    for t in child.targets:
                        if isinstance(t, ast.Name):
                            hints[t.id] = sid
    return hints


class RepoGraph:
    def __init__(self, modules: dict[str, ModuleInfo], symbols: dict[str, Symbol]):
        self.modules = modules
        self.symbols = symbols
        self.callers: dict[str, set[str]] = {sid: set() for sid in symbols}
        self.soundness: dict[str, SoundnessReport] = {}
        self.module_soundness: dict[str, SoundnessReport] = {}
        self._build()

    # -- resolution helpers --------------------------------------------------

    def _resolver_for(self, module: str):
        mod_info = self.modules[module]

        def resolve_name(name: str) -> str | None:
            local_id = f"{module}.{name}"
            if local_id in self.symbols:
                return local_id
            if name in mod_info.import_map:
                target = mod_info.import_map[name]
                if target in self.symbols:
                    return target
                # points outside the parsed repo (stdlib / third-party) — not a graph node
                return None
            return None

        return resolve_name

    def _class_owner(self, sym: Symbol) -> Symbol | None:
        if sym.kind != "method":
            return None
        class_id = f"{sym.module}.{sym.qualname.split('.')[0]}"
        return self.symbols.get(class_id)

    # -- main pass -------------------------------------------------------------

    def _build(self):
        for module, mod_info in self.modules.items():
            self.module_soundness[module] = check_module_star_imports(mod_info.star_imports)

        for sid, sym in self.symbols.items():
            resolve_name = self._resolver_for(sym.module)

            if sym.kind == "class":
                for base in sym.node.bases:
                    base_names = _flatten_annotation_names(base)
                    for bn in base_names:
                        resolved = resolve_name(bn)
                        if resolved:
                            sym.bases.add(resolved)
                            sym.type_refs.add(resolved)
                continue  # classes themselves don't have a "body" to walk for calls

            if sym.kind == "global":
                continue

            # function or method: full pass
            self.soundness[sid] = check_function(sym.node)

            local_names = _assigned_names(sym.node)
            local_type_hints = _local_type_hints(sym.node, resolve_name)
            owner_class = self._class_owner(sym)

            # annotations -> type_refs
            fn = sym.node
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for a in list(fn.args.args) + list(fn.args.posonlyargs) + list(fn.args.kwonlyargs):
                    for n in _flatten_annotation_names(a.annotation):
                        r = resolve_name(n)
                        if r and self.symbols[r].kind == "class":
                            sym.type_refs.add(r)
                for n in _flatten_annotation_names(fn.returns):
                    r = resolve_name(n)
                    if r and self.symbols[r].kind == "class":
                        sym.type_refs.add(r)

            for child in ast.walk(sym.node):
                # calls
                if isinstance(child, ast.Call):
                    callee = child.func
                    target_id = None

                    if isinstance(callee, ast.Name):
                        target_id = resolve_name(callee.id)
                        if target_id is None and callee.id not in local_names \
                                and callee.id not in BUILTIN_NAMES:
                            sym.unresolved_calls.add(callee.id)

                    elif isinstance(callee, ast.Attribute):
                        if isinstance(callee.value, ast.Name) and callee.value.id == "self" and owner_class:
                            mid = f"{sym.module}.{owner_class.qualname}.{callee.attr}"
                            if mid in self.symbols:
                                target_id = mid
                            else:
                                # best-effort: check statically-known bases
                                for base_id in owner_class.bases:
                                    base_sym = self.symbols.get(base_id)
                                    if base_sym:
                                        cand = f"{base_sym.module}.{base_sym.qualname}.{callee.attr}"
                                        if cand in self.symbols:
                                            target_id = cand
                                            break
                                if target_id is None:
                                    sym.unresolved_calls.add(f"self.{callee.attr}")
                        elif isinstance(callee.value, ast.Name) and callee.value.id in local_type_hints:
                            base_sym = self.symbols[local_type_hints[callee.value.id]]
                            cand = f"{base_sym.module}.{base_sym.qualname}.{callee.attr}"
                            if cand in self.symbols:
                                target_id = cand
                            else:
                                sym.unresolved_calls.add(f"{callee.value.id}.{callee.attr}")
                        else:
                            name_hint = getattr(callee.value, "id", "<expr>")
                            sym.unresolved_calls.add(f"{name_hint}.{callee.attr}")

                    if target_id:
                        target_sym = self.symbols[target_id]
                        if target_sym.kind == "class":
                            sym.type_refs.add(target_id)
                        else:
                            sym.calls.add(target_id)
                            self.callers.setdefault(target_id, set()).add(sid)

                # global reads (same-module or imported, e.g. `from x import SOME_CONST`)
                elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                    if child.id not in local_names:
                        gid = resolve_name(child.id)
                        if gid and self.symbols[gid].kind == "global":
                            sym.global_refs.add(gid)

    def is_sound(self, sid: str) -> bool:
        sym = self.symbols.get(sid)
        if sym is None:
            return False
        if sym.kind in ("function", "method"):
            rep = self.soundness.get(sid)
            if rep and not rep.sound:
                return False
        if self.module_soundness.get(sym.module) and not self.module_soundness[sym.module].sound:
            return False
        return True

    def soundness_reasons(self, sid: str) -> list[str]:
        sym = self.symbols.get(sid)
        if sym is None:
            return [f"unknown symbol: {sid}"]
        reasons = []
        rep = self.soundness.get(sid)
        if rep:
            reasons += rep.reasons
        mrep = self.module_soundness.get(sym.module)
        if mrep:
            reasons += mrep.reasons
        return reasons
