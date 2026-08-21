"""
parser.py — turns a directory of .py files into a table of Symbols.

A Symbol is anything a slice can be built around or reference:
  - module-level function
  - class
  - method (class-qualified)
  - module-level variable/constant

This module does *only* extraction. Graph-building lives in graph.py,
dynamic-construct detection lives in soundness.py.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field


@dataclass
class Symbol:
    id: str                      # fully-qualified id, e.g. "pkg.mod.Class.method"
    kind: str                    # "function" | "class" | "method" | "global"
    module: str                  # dotted module path, e.g. "pkg.mod"
    file_path: str                # absolute/relative path on disk
    qualname: str                 # name within the module, e.g. "Class.method"
    lineno: int
    end_lineno: int
    source: str                   # exact source text of this symbol
    node: ast.AST = field(repr=False)

    # populated by graph.py after all files are parsed
    calls: set[str] = field(default_factory=set)          # resolved callee ids
    unresolved_calls: set[str] = field(default_factory=set)  # best-effort names we couldn't resolve
    type_refs: set[str] = field(default_factory=set)      # class ids referenced (annotations/instantiation)
    global_refs: set[str] = field(default_factory=set)    # module-level var ids read
    bases: set[str] = field(default_factory=set)          # base class ids (for classes)


@dataclass
class ModuleInfo:
    module: str
    file_path: str
    tree: ast.Module
    source: str
    # local name -> what it refers to, best-effort:
    #   "mod.sub" for `import mod.sub`
    #   "mod.sub" for `from mod import sub` where sub is a module
    #   "mod.sub.name" for `from mod.sub import name`
    import_map: dict[str, str] = field(default_factory=dict)
    star_imports: list[str] = field(default_factory=list)  # modules star-imported (unresolvable)


def _module_name_for(root: str, file_path: str) -> str:
    rel = os.path.relpath(file_path, root)
    if rel.endswith("__init__.py"):
        rel = rel[: -len("__init__.py")].rstrip("/\\")
    else:
        rel = rel[: -len(".py")]
    parts = [p for p in rel.replace("\\", "/").split("/") if p]
    return ".".join(parts) if parts else os.path.splitext(os.path.basename(file_path))[0]


def _get_source_segment(source_lines: list[str], node: ast.AST) -> str:
    seg = ast.get_source_segment("\n".join(source_lines), node)
    if seg is not None:
        return seg
    # fallback: slice by line numbers
    start = getattr(node, "lineno", 1) - 1
    end = getattr(node, "end_lineno", start + 1)
    return "\n".join(source_lines[start:end])


def discover_py_files(repo_root: str) -> list[str]:
    out = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [
            d for d in dirnames
            if d not in (".git", "__pycache__", "venv", ".venv", "node_modules", ".slice")
        ]
        for fn in filenames:
            if fn.endswith(".py"):
                out.append(os.path.join(dirpath, fn))
    return sorted(out)


def parse_module(repo_root: str, file_path: str) -> tuple[ModuleInfo, dict[str, Symbol]]:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source, filename=file_path)
    module = _module_name_for(repo_root, file_path)
    lines = source.splitlines()

    mod_info = ModuleInfo(module=module, file_path=file_path, tree=tree, source=source)
    symbols: dict[str, Symbol] = {}

    # --- imports (module-level only; good enough for best-effort resolution) ---
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                mod_info.import_map[local] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            if any(a.name == "*" for a in node.names):
                mod_info.star_imports.append(node.module)
                continue
            for alias in node.names:
                local = alias.asname or alias.name
                mod_info.import_map[local] = f"{node.module}.{alias.name}"

    # --- module-level functions & classes & globals ---
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sid = f"{module}.{node.name}"
            symbols[sid] = Symbol(
                id=sid, kind="function", module=module, file_path=file_path,
                qualname=node.name, lineno=node.lineno, end_lineno=node.end_lineno,
                source=_get_source_segment(lines, node), node=node,
            )
        elif isinstance(node, ast.ClassDef):
            sid = f"{module}.{node.name}"
            symbols[sid] = Symbol(
                id=sid, kind="class", module=module, file_path=file_path,
                qualname=node.name, lineno=node.lineno, end_lineno=node.end_lineno,
                source=_get_source_segment(lines, node), node=node,
            )
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    mid = f"{module}.{node.name}.{item.name}"
                    symbols[mid] = Symbol(
                        id=mid, kind="method", module=module, file_path=file_path,
                        qualname=f"{node.name}.{item.name}", lineno=item.lineno,
                        end_lineno=item.end_lineno, source=_get_source_segment(lines, item),
                        node=item,
                    )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    sid = f"{module}.{t.id}"
                    symbols[sid] = Symbol(
                        id=sid, kind="global", module=module, file_path=file_path,
                        qualname=t.id, lineno=node.lineno, end_lineno=node.end_lineno,
                        source=_get_source_segment(lines, node), node=node,
                    )

    return mod_info, symbols


def parse_repo(repo_root: str) -> tuple[dict[str, ModuleInfo], dict[str, Symbol]]:
    modules: dict[str, ModuleInfo] = {}
    all_symbols: dict[str, Symbol] = {}
    for fp in discover_py_files(repo_root):
        mod_info, symbols = parse_module(repo_root, fp)
        modules[mod_info.module] = mod_info
        all_symbols.update(symbols)
    return modules, all_symbols
