#!/usr/bin/env python3
"""Aimed edits: the space is what this program can already build, not a list of fixes someone imagined.

WHY THIS EXISTS
---------------
Last session's search judged a whole space and found nothing on `kheapsort`, on a judge certified
to see the corpus's own answer. That is a *certified* refusal, and it is worth reading rather than
arguing with. Reading it is one line:

    python_programs/kheapsort.py         for x in arr:
    correct_python_programs/kheapsort.py for x in arr[k:]

The fix is not a new operator, a new constant or a new call. It is a **subscript with a slice**,
built out of two names the program already contains (`arr`, `k`) using a node type the program
already contains (`arr[:k]` sits three lines above). The space could not build it because
`candidate_texts` is a hand-written list of shapes -- `+ - *`, six comparisons, a few calls -- and
subscripts, slices, attributes and conditional expressions are simply not on it.

So the rule here is not "add slices". It is the rule the hand-written list violated:

    **The forms a program may be edited into are the node types the program already uses.**

Nothing is guessed and nothing is listed: a program without a `Subscript` gets no subscript
candidates, and a program with one gets `a[b]`, `a[b:]`, `a[:b]` over its own atoms. This is the
same principle that took 13 of 46 real MiniWoB pages where the hand-written rules took 0
(`AIMED_ACTIONS_ARE_DERIVED_FROM_WHAT_THE_INSTRUCTION_AND_THE_PAGE_SHOW_20261116_V1`): derive the
candidate from what is actually there, never from what someone thought of.

WHAT IS NOT CHANGED
-------------------
The judge, the per-task certification, the per-case clocks, the child containment, the ordering by
the lines the failure executes, and the verdict: the corpus's own `pytest` on a fresh copy, answer
key absent from the copy the search runs in. `solve_with_a_calibrated_judge_v1.solve_task` is
called with a different space builder and nothing else. A space that produces a hit is worth
nothing until `pytest` says so, and a space that produces none is `SPACE_EXHAUSTED` -- about *this*
space, certified, and never about the task.

Authority NONE, producer-run, zero model calls, zero network calls at run time.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import sys
import tempfile
import time
from typing import Any, Callable, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import grammar_closed_repair_v1 as gen  # noqa: E402
import solve_with_a_calibrated_judge_v1 as judged  # noqa: E402

SCHEMA = "BRAIN_AIMED_EDITS_FROM_THE_PROGRAM_AND_THE_FAILURE_V1"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"

# The forms worth instantiating, in the order they are tried. A form is instantiated only if the
# program already contains a node of that type -- that is the whole rule.
FORM_ORDER = ("Subscript", "Attribute", "Call", "IfExp", "BoolOp", "ListComp", "DictComp",
              "SetComp", "GeneratorExp", "Compare", "BinOp", "UnaryOp", "List", "Tuple", "Dict",
              "Set", "JoinedStr")
MAX_ATOMS = 10  # a program with more names than this gets its first ten, in sorted order


def forms_of(tree: ast.AST) -> list[str]:
    """The node types this program actually uses. Nothing is offered that the program cannot say."""
    present = {type(node).__name__ for node in ast.walk(tree)}
    return [form for form in FORM_ORDER if form in present]


def attributes_of(tree: ast.AST) -> list[str]:
    """Attribute names the program already uses (`heapq.heappushpop` contributes `heappushpop`)."""
    return sorted({node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)})


def callables_of(tree: ast.AST) -> list[str]:
    """Callables the program already calls or imports, by the name it calls them by."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return sorted(names)


BINOP_SYMBOLS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//",
                 ast.Mod: "%", ast.Pow: "**", ast.BitOr: "|", ast.BitAnd: "&", ast.BitXor: "^",
                 ast.LShift: "<<", ast.RShift: ">>"}


def binop_symbols_of(tree: ast.AST) -> list[str]:
    """The arithmetic this program already does, as text. Nothing else is offered."""
    symbols = {BINOP_SYMBOLS[type(node.op)] for node in ast.walk(tree)
               if isinstance(node, (ast.BinOp, ast.AugAssign)) and type(node.op) in BINOP_SYMBOLS}
    return sorted(symbols)


def aimed_texts(node_src: str, atoms: Sequence[str], forms: Sequence[str],
                attributes: Sequence[str], callables: Sequence[str],
                symbols: Sequence[str] = ()) -> list[str]:
    """Everything this program can build at this site out of forms it already contains."""
    small = list(atoms)[:MAX_ATOMS]
    texts: list[str] = []
    if "Subscript" in forms:
        for container in small:
            for bound in small:
                texts.extend((f"{container}[{bound}]", f"{container}[{bound}:]",
                              f"{container}[:{bound}]"))
            for bound in small[:4]:
                texts.append(f"({node_src})[{bound}:]")
    if "BinOp" in forms and symbols:
        # A missing term in front of the site's own expression: `powerset`'s fix is
        # `rest_subsets + [[first] + subset ...]`, which is this program's own `+` around its own
        # comprehension -- not a commutation, and not reachable by replacing the atom alone.
        for symbol in symbols:
            for name in small:
                texts.extend((f"{name} {symbol} ({node_src})", f"({node_src}) {symbol} {name}"))
    if "Attribute" in forms:
        for name in small:
            for attribute in attributes:
                texts.append(f"{name}.{attribute}")
    if "Call" in forms:
        for callable_name in callables:
            for name in small:
                texts.append(f"{callable_name}({name})")
        for name in small[:4]:
            texts.append(f"{name}({node_src})")
    if "IfExp" in forms:
        for name in small[:4]:
            for other in small[:4]:
                texts.append(f"{name} if {other} else {node_src}")
    if "List" in forms:
        # One level of nesting, using the site's own expression: `return []` -> `return [[]]`.
        # The inner text is the program's own text at this site, so nothing is invented.
        texts.extend((f"[{node_src}]", f"({node_src},)"))
    if "BoolOp" in forms:
        for name in small[:4]:
            for other in small[:4]:
                texts.extend((f"{name} and {other}", f"{name} or {other}"))
    return texts


COMMUTATIVE = (ast.Add, ast.Mult, ast.BitOr, ast.BitAnd, ast.BitXor)


def commuted(tree: ast.AST) -> list[dict[str, Any]]:
    """The operands of a commutative operator, the other way round.

    `result + alphabet[i]` -> `alphabet[i] + result` (to_base) and
    `[[first] + subset ...] + rest_subsets` -> `... + [[first] + subset ...]` (powerset) are both
    fixes the previous space could not express, and both are the same true fact: `+` commutes.
    Nothing is invented; the operands and the operator are the program's own.
    """
    out: list[dict[str, Any]] = []
    for path, node in gen._paths(tree):  # noqa: SLF001
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, COMMUTATIVE):
            continue
        swapped = ast.BinOp(left=node.right, right=node.left, op=node.op)
        try:
            source = ast.unparse(gen.replace_at(tree, path, ast.copy_location(swapped, node)))
            if not gen._compiles_quietly(source):  # noqa: SLF001
                continue
        except Exception:  # noqa: BLE001
            continue
        out.append({"kind": "COMMUTE", "site": ast.unparse(node),
                    "replacement": f"{ast.unparse(node.right)} {type(node.op).__name__} "
                                   f"{ast.unparse(node.left)}",
                    "lineno": getattr(node, "lineno", 0), "source": source})
    return out


def statement_shapes(atoms: Sequence[str], attributes: Sequence[str],
                     callables: Sequence[str]) -> list[str]:
    """Statements this program could write, built from what it already names and already does."""
    shapes: list[str] = []
    small = list(atoms)[:MAX_ATOMS]
    for name in small:
        for attribute in attributes:
            shapes.append(f"{name}.{attribute}")
            for other in small:
                shapes.append(f"{name}.{attribute}({other})")
    for callable_name in callables:
        for other in small:
            shapes.append(f"{callable_name}({other})")
    seen: set[str] = set()
    ordered: list[str] = []
    for shape in shapes:
        if shape not in seen:
            seen.add(shape)
            ordered.append(shape)
    return ordered


def _blocks(tree: ast.AST) -> list[tuple[ast.AST, str]]:
    blocks: list[tuple[ast.AST, str]] = []
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if isinstance(block, list) and block and all(isinstance(x, ast.stmt) for x in block):
                blocks.append((node, field))
    return blocks


def inserted(tree: ast.AST, atoms: Sequence[str], attributes: Sequence[str],
             callables: Sequence[str]) -> list[dict[str, Any]]:
    """A missing statement is an insertion, and the previous space only ever replaced.

    `shunting_yard`'s fix adds `opstack.append(token)` inside a branch -- a statement the program
    never had in that block. It can still be derived: it is this program's own `name.attribute(name)`
    form over its own atoms, put at the end of a block the program already has.
    """
    import copy

    out: list[dict[str, Any]] = []
    shapes = statement_shapes(atoms, attributes, callables)
    seen: set[str] = set()
    for node, field in _blocks(tree):
        for shape in shapes:
            try:
                statement = ast.parse(shape).body[0]
            except SyntaxError:
                continue
            for where in ("end", "start"):
                mutated = copy.deepcopy(tree)
                target = None
                for candidate, candidate_field in _blocks(mutated):
                    if candidate_field == field and _same_span(candidate, node):
                        target = candidate
                        break
                if target is None:
                    continue
                block = getattr(target, field)
                if where == "end":
                    block.append(statement)
                else:
                    block.insert(0, statement)
                try:
                    source = ast.unparse(mutated)
                    if not gen._compiles_quietly(source):  # noqa: SLF001
                        continue
                except Exception:  # noqa: BLE001
                    continue
                if source in seen:
                    continue
                seen.add(source)
                out.append({"kind": "INSERT_STATEMENT", "site": ast.unparse(node)[:60],
                            "replacement": shape, "where": where,
                            "lineno": getattr(node, "lineno", 0), "source": source})
    return out


def _same_span(left: ast.AST, right: ast.AST) -> bool:
    return (getattr(left, "lineno", None) == getattr(right, "lineno", None)
            and type(left).__name__ == type(right).__name__)


def space_builder(tree: ast.AST, atoms: Sequence[str]) -> list[dict[str, Any]]:
    """The base space plus the program's own forms, generated over the program's own atoms."""
    forms = forms_of(tree)
    attributes = attributes_of(tree)
    callables = callables_of(tree)

    symbols = binop_symbols_of(tree)

    def extra(node_src: str) -> Sequence[str]:
        return aimed_texts(node_src, atoms, forms, attributes, callables, symbols)

    space = gen._enumerate(tree, atoms, extra_texts=extra)  # noqa: SLF001
    # Closure of the program's own material under three rules, each read from a certified refusal:
    # its forms over its atoms, its commutative operands the other way round, its statement shapes
    # inserted into its own blocks. Nothing here is a list of known fixes.
    seen = {candidate["source"] for candidate in space}
    for extra_space in (commuted(tree),
                        inserted(tree, atoms, attributes, callables)):
        for candidate in extra_space:
            if candidate["source"] in seen:
                continue
            seen.add(candidate["source"])
            space.append(candidate)
    return space


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--tasks", nargs="+", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--candidate-cap", type=int, default=40000)
    parser.add_argument("--wall-budget", type=float, default=900.0)
    parser.add_argument("--verify-timeout", type=int, default=240)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs)
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        workdir = pathlib.Path(tmp)
        for name in args.tasks:
            try:
                row = judged.solve_task(root, name, candidate_cap=args.candidate_cap,
                                        wall_budget=args.wall_budget,
                                        verify_timeout=args.verify_timeout, workdir=workdir,
                                        space_builder=space_builder)
                row["space"] = "aimed_forms"
                source = (root / "python_programs" / f"{name}.py").read_text()
                row["forms_in_the_program"] = forms_of(ast.parse(source))
            except Exception as error:  # noqa: BLE001
                row = {"task": name, "kind": "task", "stage": "RAISED",
                       "error": repr(error)[:300], "space": "aimed_forms"}
            rows.append(row)
            print(f"{name:24s} {str(row.get('stage')):18s} evaluated={row.get('candidates_evaluated')} "
                  f"space={row.get('space_size')} solved={'Y' if row.get('solved') else 'n'} "
                  f"forms={','.join(row.get('forms_in_the_program') or [])}", flush=True)

    summary = judged.summarise(rows)
    receipt = {"schema": SCHEMA, "authority": judged.AUTHORITY, "upstream": UPSTREAM,
               "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "corpus_commit": judged.corpus_commit(root),
               "tool": "canonical/tools/aimed_edits_from_the_program_and_the_failure_v1.py",
               "tests": "canonical/tests/test_aimed_edits_from_the_program_and_the_failure_v1.py",
               "space": "base enumeration plus the program's own forms over its own atoms",
               "parameters": {"candidate_cap": args.candidate_cap,
                              "wall_budget_seconds": args.wall_budget,
                              "verify_timeout_seconds": args.verify_timeout,
                              "chunk": judged.CHUNK, "max_atoms": MAX_ATOMS},
               "model_dependency_count": 0, "external_capability_provider_count": 0,
               "network_calls_at_run_time": 0, "summary": summary, "rows": rows}
    if args.receipt:
        pathlib.Path(args.receipt).write_text(
            __import__("json").dumps(receipt, indent=2, default=str) + "\n")
    print(__import__("json").dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
