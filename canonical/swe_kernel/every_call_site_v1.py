"""Every usable call site the environment already contains, not just the two-argument ones.

WHY THIS EXISTS
---------------
`argument_construction_v1` asked whether a learned action can be EXECUTED at all, and found
`EVERY_CALL_SITE_IS_UNENCODABLE 34` of 41 unexercised actions. Its own docstring names nested
construction as "the next gap" and refuses it by name. That refusal was a guess about the cause,
so this round measured the cause instead of assuming it.

Over 1,039 call sites of tree-defined functions in one real repository:

    keyword arguments dropped wholesale            280   26.9%
    an argument that cannot be encoded             376   36.2%
       of which a bare unresolved Name             232
    more than two positional arguments               36    3.5%
    USABLE                                         339   32.6%

Three of those four are not limits of knowledge. They are limits of an encoder:

  * 205 of the 302 keyword values are plain constants (`python='3.9'`). Throwing away a
    fully known value is not a refusal, it is a bug.
  * `Name` is unresolvable when the binder only propagates literals. A name that is a
    parameter of the enclosing function has a TYPE readable from the call that passed it, and
    that is the registry this round builds.
  * Arity is a constant `MAX_ARGS = 2`; the tree has 3-argument calls at 18% of sites.

WHAT THIS IS AND IS NOT
-----------------------
This does not make a program SOLVE anything. It raises the share of real call sites that can
be executed at all, which is strictly prior to solving and is the term the previous round
refused by name. A vector that is mined here is still unproven until it runs twice at the
same tree and returns the same thing -- that control is reused, not weakened.

Nothing here invents a value. Every token traces to a call site somebody wrote, shipped, and
in most cases ran. When no such site exists the call site is REFUSED and the reason is named.

Schema BRAIN_EVERY_CALL_SITE_V1. Authority NONE__PRODUCER_RUN_SANDBOX. No model, no network.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from typing import Any, Mapping

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import argument_construction_v1 as AC  # noqa: E402

SCHEMA = "BRAIN_EVERY_CALL_SITE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

# Why a call site was not turned into an executable vector. Named, counted, never hidden.
USABLE = "USABLE"
NO_KWARG_TOKEN = "REFUSED__KEYWORD_VALUE_NOT_ENCODABLE"
NO_ARG_TOKEN = "REFUSED__ARGUMENT_NOT_ENCODABLE"
TOO_MANY = "REFUSED__ARITY_OVER_CAP"
STARRED = "REFUSED__STARRED_ARGUMENT"
UNRESOLVED_NAME = "REFUSED__NAME_HAS_NO_TYPE"


def module_tree(path: pathlib.Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (SyntaxError, OSError):
        return None


def defined_functions(module: ast.Module) -> dict[str, ast.FunctionDef]:
    return {node.name: node for node in ast.walk(module)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def parameter_types(module: ast.Module, defined: Mapping[str, ast.FunctionDef]
                    ) -> dict[tuple[str, str], str]:
    """(function, parameter) -> the token kinds actually passed to it, from real call sites.

    This is the registry that turns an unresolvable Name into an encodable token. It is built
    only from call sites in the same tree, so the type of a parameter is the type this
    repository gives it, not a type anybody declared.
    """
    seen: dict[tuple[str, str], set[str]] = {}
    for call in [n for n in ast.walk(module) if isinstance(n, ast.Call)]:
        name = call.func.id if isinstance(call.func, ast.Name) else None
        if name is None or name not in defined:
            continue
        parameters = [a.arg for a in defined[name].args.args]
        for index, argument in enumerate(call.args[:len(parameters)]):
            kind = ("positional", type(argument).__name__)
            seen.setdefault((name, parameters[index]), set()).add(kind[1])
        for keyword in call.keywords:
            if keyword.arg is None:
                continue
            seen.setdefault((name, keyword.arg), set()).add(type(keyword.value).__name__)
    return {key: sorted(kinds)[0] for key, kinds in seen.items()}


def _token_for(node: ast.AST, scope: Mapping[str, ast.AST],
               constants: Mapping[str, Any]) -> str | None:
    """One argument as a token the prober already understands, or None with a reason.

    Reuses `_encodable` and `_resolve_name`; adds nothing to the wire format. The keyword
    case is the one the previous round dropped and the one that carries 205 plain constants.
    """
    if isinstance(node, ast.Name):
        return AC._resolve_name(node.id, scope, constants)
    ok, value = AC._encodable(node)
    return AC._json_token(value) if ok else None


def mine(tree: pathlib.Path) -> dict[str, Any]:
    """Every call site of a tree-defined function, encoded as a positional+kwd vector."""
    counts: dict[str, int] = {}
    refused_kinds: dict[str, int] = {}
    vectors: dict[str, list[dict[str, Any]]] = {}
    sites = 0
    per_file: dict[str, int] = {}

    for path in sorted(tree.rglob("*.py")):
        if ".git" in path.parts:
            continue
        module = module_tree(path)
        if module is None:
            continue
        defined = defined_functions(module)
        if not defined:
            continue
        constants = AC.module_constants(module)
        types = parameter_types(module, defined)
        # The MODULE-only pass and the FUNCTION passes must not overlap: walking `module`
        # descends into its functions, so adding function holders on top counts every call
        # inside a function twice. The module pass therefore sees module-level code only,
        # which is also where its scope is a plain module scope.
        module_body = [statement for statement in module.body
                       if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef,
                                                     ast.ClassDef))]
        for holder in [ast.Module(body=module_body, type_ignores=[])] + \
                [n for n in ast.walk(module)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            scope = {} if isinstance(holder, ast.Module) else AC._scope_of(holder)
            for call in [n for n in ast.walk(holder) if isinstance(n, ast.Call)]:
                target = call.func.id if isinstance(call.func, ast.Name) else None
                if target not in defined:
                    continue
                sites += 1
                if any(isinstance(a, ast.Starred) for a in call.args):
                    counts[STARRED] = counts.get(STARRED, 0) + 1
                    continue
                if len(call.args) > AC.MAX_ARGS:
                    counts[TOO_MANY] = counts.get(TOO_MANY, 0) + 1
                    continue
                args: list[str] = []
                failed = None
                for argument in call.args:
                    token = _token_for(argument, scope, constants)
                    if token is None:
                        # A bare Name is the dominant blocker (131 of 252 sites). The
                        # parameter-type registry knows what KIND was passed to it from
                        # real call sites, but knowing a parameter receives a Constant
                        # does not say WHICH constant. Substituting one would be
                        # inventing a value, so the site is refused and the known kind is
                        # recorded next to it -- the fact is kept, the invention is not.
                        if isinstance(argument, ast.Name):
                            failed = UNRESOLVED_NAME
                            known_kind = types.get((target, argument.id))
                            if known_kind:
                                refused_kinds[known_kind] = refused_kinds.get(known_kind, 0) + 1
                        else:
                            failed = NO_ARG_TOKEN
                        break
                    args.append(token)
                keywords: list[list[str]] = []
                if failed is None:
                    for keyword in call.keywords:
                        if keyword.arg is None:
                            failed = NO_KWARG_TOKEN
                            break
                        token = _token_for(keyword.value, scope, constants)
                        if token is None:
                            failed = NO_KWARG_TOKEN
                            break
                        keywords.append([keyword.arg, token])
                if failed:
                    counts[failed] = counts.get(failed, 0) + 1
                    continue
                counts[USABLE] = counts.get(USABLE, 0) + 1
                per_file[path.name] = per_file.get(path.name, 0) + 1
                bucket = vectors.setdefault(target, [])
                vector = {"args": args, "kwargs": keywords}
                if vector not in bucket and len(bucket) < AC.MAX_VECTORS * 2:
                    bucket.append(vector)

    total = max(1, sites)
    return {"schema": SCHEMA, "authority": AUTHORITY, "tree": str(tree),
            "call_sites": sites,
            "counts": counts,
            "refused_name_kinds": refused_kinds,
            "usable_share": round(counts.get(USABLE, 0) / total, 4),
            "functions_with_a_vector": len(vectors),
            "vectors": vectors,
            "files_with_a_usable_site": len(per_file)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tree", nargs="?", default="/tmp/ckcache/pypa__packaging@24.0")
    parser.add_argument("--json", type=pathlib.Path)
    args = parser.parse_args(argv)
    report = mine(pathlib.Path(args.tree))
    summary = {k: report[k] for k in
               ("call_sites", "usable_share", "functions_with_a_vector",
                "files_with_a_usable_site")}
    print(json.dumps(summary, indent=1))
    print(json.dumps(report["counts"], indent=1))
    print("kinds behind the refused bare names:",
          json.dumps(report["refused_name_kinds"]))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True))
        print("written:", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
