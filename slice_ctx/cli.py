"""
cli.py — `python -m slice_ctx analyze ...`
"""

from __future__ import annotations

import argparse
import json
import sys
import io
import os
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from .parser import parse_repo
from .graph import RepoGraph
from .slicer import slice_for, render_slice
from .session import Session
from .tokens import count_tokens, METHOD


def _naive_baseline(graph: RepoGraph, result) -> tuple[str, int]:
    """What a naive tool sends: the *whole file* for every symbol in the
    slice (this is what 'dump relevant files into the prompt' means in
    practice), deduplicated by file."""
    seen_files = {}
    for sid in result.included:
        sym = graph.symbols[sid]
        if sym.file_path not in seen_files:
            with open(sym.file_path, "r", encoding="utf-8") as f:
                seen_files[sym.file_path] = f.read()
    text = "\n".join(f"# --- {fp} ---\n{content}" for fp, content in seen_files.items())
    return text, count_tokens(text)


def cmd_analyze(args: argparse.Namespace) -> int:
    modules, symbols = parse_repo(args.repo)
    graph = RepoGraph(modules, symbols)

    if args.target not in symbols:
        print(f"error: symbol {args.target!r} not found.", file=sys.stderr)
        candidates = [s for s in symbols if args.target.split(".")[-1] in s]
        if candidates:
            print("did you mean one of:", file=sys.stderr)
            for c in sorted(candidates)[:10]:
                print(f"  {c}", file=sys.stderr)
        return 1

    result = slice_for(graph, args.target, callee_depth=args.callee_depth, caller_depth=args.caller_depth)
    rendered = render_slice(graph, result)

    slice_tokens = count_tokens(rendered)
    naive_text, naive_tokens = _naive_baseline(graph, result)

    session_note = None
    if args.session:
        session = Session(args.session)
        units = []
        for sid in result.included:
            sym = graph.symbols[sid]
            unit = session.get_context_unit(sym.id, sym.source)
            units.append(unit)
        session.save()
        session_tokens = sum(count_tokens(u.payload) for u in units)
        session_note = {
            "new": sum(1 for u in units if u.status == "new"),
            "unchanged": sum(1 for u in units if u.status == "unchanged"),
            "changed": sum(1 for u in units if u.status == "changed"),
            "tokens_with_session_reuse": session_tokens,
        }

    report = {
        "target": result.target,
        "included_symbols": result.included,
        "counts": {
            "callees": len(result.callees),
            "callers": len(result.callers),
            "type_refs": len(result.type_refs),
            "global_refs": len(result.global_refs),
        },
        "sound": result.sound,
        "unsound_reasons": result.unsound_reasons,
        "unresolved_calls": result.unresolved,
        "tokens": {
            "method": METHOD,
            "slice": slice_tokens,
            "naive_full_file_baseline": naive_tokens,
            "reduction_pct": round(100 * (1 - slice_tokens / naive_tokens), 1) if naive_tokens else 0.0,
        },
        "session": session_note,
    }

    limit = getattr(args, "max_symbols", None)
    exceeded = limit is not None and len(result.included) > limit
    if limit is not None: report["budget"] = {"limit":limit,"included":len(result.included),"exceeded":exceeded}
    if getattr(args, "include_source", False):
        report["source"] = rendered
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(rendered)
        print("\n" + "=" * 72)
        print(f"target: {result.target}")
        print(f"sound: {result.sound}" + ("" if result.sound else "  (see --json for reasons)"))
        print(f"included: {len(result.included)} symbols "
              f"({len(result.callees)} callees, {len(result.callers)} callers, "
              f"{len(result.type_refs)} types, {len(result.global_refs)} globals)")
        print(f"tokens [{METHOD}]: slice={slice_tokens}  naive_full_file={naive_tokens}  "
              f"reduction={report['tokens']['reduction_pct']}%")
        if session_note:
            print(f"session reuse: {session_note['new']} new, {session_note['unchanged']} unchanged, "
                  f"{session_note['changed']} changed -> {session_note['tokens_with_session_reuse']} tokens "
                  f"if this were a repeat turn")
        if not result.sound:
            print("\nWARNING: this slice is not certified sound. Fall back to full-file context for:")
            for sid, reasons in result.unsound_reasons.items():
                for r in reasons:
                    print(f"  - {sid}: {r}")

    if getattr(args, "strict", False) and not result.sound: return 3
    return 4 if exceeded else 0


def cmd_symbols(args: argparse.Namespace) -> int:
    _, symbols = parse_repo(args.repo)
    ids = sorted(sid for sid in symbols if args.query.casefold() in sid.casefold() and (not args.kind or symbols[sid].kind == args.kind) and (not args.module or symbols[sid].module == args.module or symbols[sid].module.startswith(args.module + ".")))
    total = len(ids)
    selected = ids[args.offset:None if args.limit is None else args.offset + args.limit]
    values = [{"id":sid,"kind":symbols[sid].kind,"module":symbols[sid].module,"path":symbols[sid].file_path,"line":symbols[sid].lineno,"end_line":symbols[sid].end_lineno} for sid in selected] if args.details else selected
    report = {"symbols":values,"total":total}
    if args.offset or args.limit is not None:
        report.update(offset=args.offset, returned=len(selected), has_more=args.offset+len(selected)<total)
        if not args.json and (args.offset or len(selected)<total): print(f"showing {len(selected)} of {total} symbols (offset {args.offset})",file=sys.stderr)
    print(json.dumps(report,indent=2) if args.json else "\n".join(selected))
    return 0


def non_negative_depth(value: str) -> int:
    depth = int(value)
    if depth < 0:
        raise argparse.ArgumentTypeError("depth must be non-negative")
    return depth


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="slice_ctx", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="compute a dependency slice for one symbol")
    p_analyze.add_argument("repo", help="path to the repo root")
    p_analyze.add_argument("--target", required=True,
                            help="dotted symbol id, e.g. pkg.module.ClassName.method")
    p_analyze.add_argument("--callee-depth", type=non_negative_depth, default=None,
                            help="transitive callee depth (default: unlimited)")
    p_analyze.add_argument("--caller-depth", type=non_negative_depth, default=1,
                            help="transitive caller depth (default: 1, signature-only)")
    p_analyze.add_argument("--session", default=None,
                            help="path to a session cache file for diff-based reuse")
    p_analyze.add_argument("--json", action="store_true", help="emit JSON report instead of text")
    p_analyze.add_argument("--output", help="write the report to a UTF-8 file instead of stdout")
    p_analyze.add_argument("--max-symbols", type=non_negative_depth, help="exit 4 when a complete report exceeds this symbol budget")
    p_analyze.add_argument("--include-source", action="store_true", help="include rendered context in JSON reports")
    p_analyze.add_argument("--strict", action="store_true", help="exit 3 for an uncertified slice without hiding its report")
    p_analyze.set_defaults(func=cmd_analyze)

    listing = sub.add_parser("symbols", help="list known symbol IDs before choosing a target")
    listing.add_argument("repo")
    listing.add_argument("--query", default="")
    listing.add_argument("--module", help="exact module or dotted module subtree")
    listing.add_argument("--kind", choices=["function","class","method","global"])
    listing.add_argument("--json", action="store_true")
    listing.add_argument("--details", action="store_true",help="include kind, module and source locations; requires --json")
    listing.add_argument("--limit",type=non_negative_depth)
    listing.add_argument("--offset",type=non_negative_depth,default=0)
    listing.add_argument("--output")
    listing.set_defaults(func=cmd_symbols)
    args = parser.parse_args(argv)
    if getattr(args,"details",False) and not args.json: parser.error("--details requires --json")
    if not Path(args.repo).is_dir():
        parser.error(f"repo is not a directory: {args.repo}")
    try:
        if args.output:
            output = io.StringIO()
            with redirect_stdout(output): status = args.func(args)
            if status == 1: return status
            destination = Path(args.output)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=destination.parent,delete=False) as stream:
                    temporary = Path(stream.name);stream.write(output.getvalue())
                os.replace(temporary,destination)
            finally:
                if temporary and temporary.exists(): temporary.unlink()
            return status
        return args.func(args)
    except (OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
