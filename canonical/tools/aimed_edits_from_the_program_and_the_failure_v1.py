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


def _subscript_rule(node_src: str, atoms: Sequence[str], forms: Sequence[str],
                    attributes: Sequence[str], callables: Sequence[str],
                    symbols: Sequence[str], context: dict[str, Any] | None = None) -> list[str]:
    if "Subscript" not in forms:
        return []
    small = list(atoms)[:MAX_ATOMS]
    texts: list[str] = []
    if "Subscript" in forms:
        for container in small:
            for bound in small:
                texts.extend((f"{container}[{bound}]", f"{container}[{bound}:]",
                              f"{container}[:{bound}]"))
            for bound in small[:4]:
                texts.append(f"({node_src})[{bound}:]")
    return texts


def _prepend_rule(node_src: str, atoms: Sequence[str], forms: Sequence[str],
                  attributes: Sequence[str], callables: Sequence[str],
                  symbols: Sequence[str], context: dict[str, Any] | None = None) -> list[str]:
    """A missing term in front of the site's own expression.

    `powerset`'s fix is `rest_subsets + [[first] + subset ...]`: the program's own `+` around its
    own comprehension -- not a commutation, and not reachable by replacing an atom alone.
    """
    if "BinOp" not in forms or not symbols:
        return []
    small = list(atoms)[:MAX_ATOMS]
    return [text for symbol in symbols for name in small
            for text in (f"{name} {symbol} ({node_src})", f"({node_src}) {symbol} {name}")]


def _attribute_rule(node_src: str, atoms: Sequence[str], forms: Sequence[str],
                    attributes: Sequence[str], callables: Sequence[str],
                    symbols: Sequence[str], context: dict[str, Any] | None = None) -> list[str]:
    if "Attribute" not in forms:
        return []
    return [f"{name}.{attribute}" for name in list(atoms)[:MAX_ATOMS] for attribute in attributes]


def _call_rule(node_src: str, atoms: Sequence[str], forms: Sequence[str],
               attributes: Sequence[str], callables: Sequence[str],
               symbols: Sequence[str], context: dict[str, Any] | None = None) -> list[str]:
    if "Call" not in forms:
        return []
    small = list(atoms)[:MAX_ATOMS]
    texts = [f"{name}({other})" for name in callables for other in small]
    texts += [f"{name}({node_src})" for name in small[:4]]
    return texts


def _ifexp_rule(node_src: str, atoms: Sequence[str], forms: Sequence[str],
                attributes: Sequence[str], callables: Sequence[str],
                symbols: Sequence[str], context: dict[str, Any] | None = None) -> list[str]:
    if "IfExp" not in forms:
        return []
    small = list(atoms)[:MAX_ATOMS]
    return [f"{name} if {other} else {node_src}" for name in small[:4] for other in small[:4]]


def _nest_rule(node_src: str, atoms: Sequence[str], forms: Sequence[str],
               attributes: Sequence[str], callables: Sequence[str],
               symbols: Sequence[str], context: dict[str, Any] | None = None) -> list[str]:
    """One level of nesting, using the site's own expression: `return []` -> `return [[]]`."""
    if "List" not in forms and "Tuple" not in forms:
        return []
    return [f"[{node_src}]", f"({node_src},)"]


def _boolop_rule(node_src: str, atoms: Sequence[str], forms: Sequence[str],
                 attributes: Sequence[str], callables: Sequence[str],
                 symbols: Sequence[str], context: dict[str, Any] | None = None) -> list[str]:
    if "BoolOp" not in forms:
        return []
    small = list(atoms)[:MAX_ATOMS]
    return [text for name in small[:4] for other in small[:4]
            for text in (f"{name} and {other}", f"{name} or {other}")]


def statement_of(tree: ast.AST, site_text: str) -> ast.stmt | None:
    """The innermost statement whose source contains this site: a fix is local."""
    best: tuple[ast.stmt, int] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.stmt):
            continue
        try:
            source = ast.unparse(node)
        except Exception:  # noqa: BLE001
            continue
        if site_text in source and (best is None or len(source) < best[1]):
            best = (node, len(source))
    return best[0] if best is not None else None


def _size(text: str) -> int:
    """How many nodes this expression has, or a refusal. The budget is spent in nodes."""
    try:
        return sum(1 for _ in ast.walk(ast.parse(text, mode="eval").body))
    except SyntaxError:
        return 10 ** 6


def material_of(tree: ast.AST, site_text: str, limit: int = 40) -> list[str]:
    """Every expression the statement around the site contains -- complete, so nothing is missed.

    An earlier version kept a fixed number of "most promising" expressions and the set of fixes it
    could reach changed with the cap: `len(arr)` fell off the list and `len(arr) <= 1` became
    unreachable while `perm[i] < perm[j]` became reachable. Whatever a cap decides, it is not a
    measurement. The pool is therefore *complete* for the statement, and the bound is on the size of
    what may be built from it, which is a property of the answer rather than of a list index.
    """
    statement = statement_of(tree, site_text)
    nodes = list(ast.walk(statement)) if statement is not None else list(ast.walk(tree))
    texts: list[str] = []
    for node in nodes:
        if not isinstance(node, ast.expr) or isinstance(node, ast.Starred):
            continue
        try:
            text = ast.unparse(node)
        except Exception:  # noqa: BLE001
            continue
        if len(text) > 60 or text == site_text or text in texts:
            continue
        texts.append(text)
    for literal in ("None", "True", "False"):
        if literal not in texts:
            texts.append(literal)
    texts.sort(key=_size)
    return texts[:limit]


def _recombine_rule(node_src: str, atoms: Sequence[str], forms: Sequence[str],
                    attributes: Sequence[str], callables: Sequence[str],
                    symbols: Sequence[str], context: dict[str, Any] | None = None) -> list[str]:
    """Recombine the site with the program's own material under the language's own expression forms.

    Every published fix that escaped the earlier rungs had the same shape -- the site's expression and
    a *neighbouring* expression, joined by a form the language has and the fix needs: `length + 1` ->
    `max(longest, length + 1)`, `hare.successor is None` -> `hare is None or hare.successor is None`,
    `total < 0` -> `total < 0 or not coins`, `[]` -> `[n]`.

    The vocabulary is Python's expression grammar; the material is the statement the site sits in (a
    fix is local); the bound is a budget of nodes -- no candidate may be more than `BUDGET` nodes
    larger than the site it replaces. Nothing here is a list of fixes, which is exactly what
    `HOLE_SHAPES` was and why it stopped where it did.
    """
    tree = (context or {}).get("tree")
    material = material_of(tree, node_src) if isinstance(tree, ast.AST) else list(atoms)
    site = f"({node_src})"
    site_size = _size(node_src)
    budget = site_size + BUDGET
    texts: list[str] = list(material)  # the site may *be* one of the program's own expressions
    atoms_near = [item for item in list(atoms) + ["None", "True", "False"]
                  if item not in material]
    operand_limit = site_size + 1
    operands = [(text, _size(text)) for text in material + atoms_near if _size(text) <= operand_limit]
    names = list(callables)[:5] + list(BUILTIN_CALLABLES)
    operators = list(COMPARATORS) + ["is", "is not", "in"]
    for one, one_size in operands:
        if 1 + one_size <= budget:
            for name in names:
                texts.append(f"{name}({one})")
            for attribute in attributes:
                texts.append(f"{one}.{attribute}")
            texts += [f"not {one}", f"-{one}", f"[{one}]", f"({one},)"]
    for left, left_size in operands:
        for right, right_size in operands:
            if left == right or 1 + left_size + right_size > budget:
                continue
            for symbol in symbols:
                texts.append(f"{left} {symbol} {right}")
            for operator in operators:
                texts.append(f"{left} {operator} {right}")
            texts += [f"{left} and {right}", f"{left} or {right}",
                      f"{left} and not {right}", f"{left} or not {right}",
                      f"{left}[{right}]", f"[{left}, {right}]", f"({left}, {right})"]
            for name in names:
                texts.append(f"{name}({left}, {right})")
    for one, one_size in operands:
        if 1 + one_size + site_size <= budget:
            for left, right in ((site, one), (one, site)):
                for symbol in symbols:
                    texts.append(f"{left} {symbol} {right}")
                for operator in operators:
                    texts.append(f"{left} {operator} {right}")
                texts += [f"{left} or {right}", f"{left} and {right}",
                          f"{left} or not {right}", f"{left} and not {right}",
                          f"{left}[{right}]"]
                for name in names:
                    texts.append(f"{name}({left}, {right})")
    return texts


BUILTIN_CALLABLES = ("max", "min", "abs", "len", "sorted", "sum")  # the language, not a list of fixes
COMPARATORS = ("<", "<=", ">", ">=", "==", "!=")
#: How many nodes a recombination may add on top of the site it replaces.
BUDGET = 4


def _enclose_rule(node_src: str, atoms: Sequence[str], forms: Sequence[str],
                  attributes: Sequence[str], callables: Sequence[str],
                  symbols: Sequence[str], context: dict[str, Any] | None = None) -> list[str]:
    """The site's own expression *enclosed* by a form the program itself already uses.

    Every piece is read off the artifact: the forms are the node types the program contains, the
    operators are the ones it uses, the callables are the ones it calls, the atoms are its own
    identifiers. Nothing here is a list of fixes.

    This is the rung the hand-written `HOLE_SHAPES` stood in for, and its absence is exactly why 13
    of the 40 published fixes read as "a single edit no class can make": `length + 1` ->
    `max(longest, length + 1)` (lis), `total < 0` -> `total < 0 or not coins` (possible_change),
    `[]` -> `[n]` (get_factors), `k` -> `k - num_lessoreq` (kth), `len(arr) == 0` ->
    `len(arr) <= 1` (mergesort) are all enclosure, and none of them is a new *lesson* -- they are
    the program's own syntax applied to the program's own material.
    """
    small = list(atoms)[:MAX_ATOMS]
    site = f"({node_src})"
    texts: list[str] = []
    if "BinOp" in forms:
        for symbol in symbols:
            texts += [f"{site} {symbol} {name}" for name in small]
            texts += [f"{name} {symbol} {site}" for name in small]
    if "BoolOp" in forms:
        for name in small:
            texts += [f"{site} or {name}", f"{site} and {name}",
                      f"{name} or {site}", f"{name} and {site}",
                      f"{site} or not {name}", f"{site} and not {name}",
                      f"not {name} or {site}", f"not {name} and {site}"]
    if "Compare" in forms:
        for operator in COMPARATORS:
            texts += [f"{site} {operator} {name}" for name in small]
            texts += [f"{name} {operator} {site}" for name in small]
    if "Call" in forms:
        for name in list(callables)[:6] + list(BUILTIN_CALLABLES):
            texts += [f"{name}({site})"]
            texts += [f"{name}({site}, {other})" for other in small]
            texts += [f"{name}({other}, {site})" for other in small]
    if "Subscript" in forms:
        for name in small:
            texts += [f"{site}[{name}]", f"{name}[{site}]"]
    if "List" in forms:
        texts += [f"[{site}]"]
    if "Attribute" in forms:
        texts += [f"{site}.{attribute}" for attribute in attributes]
    if "UnaryOp" in forms:
        texts += [f"not {site}", f"-{site}"]
    return texts


# A class is a rule, and the library is the set of rules that has been learned. Each of the five
# below was read off a certified refusal from a *different* program; that is what makes the
# transfer question answerable.
RULES: dict[str, Callable[..., list[str]]] = {
    "SLICE": _subscript_rule,
    "PREPEND_TERM": _prepend_rule,
    "ATTRIBUTE": _attribute_rule,
    "CALL": _call_rule,
    "IF_EXPRESSION": _ifexp_rule,
    "NEST": _nest_rule,
    "BOOLEAN_OP": _boolop_rule,
}

#: Rungs that are measured but not shipped in the space yet. Keeping them out of `RULES` keeps every
#: shipped receipt describing the code that produced it: turning them on changes the space, so it
#: needs its own solve run, not a quiet edit to a verified number.
EXPERIMENTAL: dict[str, Callable[..., list[str]]] = {
    "ENCLOSE": _enclose_rule,
    "RECOMBINE": _recombine_rule,
}


def aimed_texts(node_src: str, atoms: Sequence[str], forms: Sequence[str],
                attributes: Sequence[str], callables: Sequence[str],
                symbols: Sequence[str] = (), context: dict[str, Any] | None = None,
                extra_classes: bool = False) -> list[str]:
    """Everything this program can build at this site out of forms it already contains."""
    classes = dict(RULES)
    if extra_classes:
        classes.update(EXPERIMENTAL)
    texts: list[str] = []
    for rule in classes.values():
        texts.extend(rule(node_src, atoms, forms, attributes, callables, list(symbols), context))
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


def space_builder(tree: ast.AST, atoms: Sequence[str],
                  extra_classes: bool = False) -> list[dict[str, Any]]:
    """The base space plus the program's own forms, generated over the program's own atoms.

    `extra_classes` adds the experimental rungs -- the language's forms over the program's own
    material -- so a measurement can ask what they would buy without changing what ships.
    """
    classes = dict(RULES)
    if extra_classes:
        classes.update(EXPERIMENTAL)
    forms = forms_of(tree)
    attributes = attributes_of(tree)
    callables = callables_of(tree)

    symbols = binop_symbols_of(tree)

    where: dict[str, str] = {}

    def extra(node_src: str) -> Sequence[str]:
        texts: list[str] = []
        for name, rule in classes.items():
            produced = rule(node_src, atoms, forms, attributes, callables, symbols,
                            {"tree": tree})
            for text in produced:
                where.setdefault(text, name)
            texts.extend(produced)
        return texts

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
    for candidate in space:
        candidate.setdefault("class", "BASE" if candidate["kind"] in {"REPLACE", "OPERATOR",
                                                                     "PERMUTE", "PERMUTE_OPERANDS",
                                                                     "ATOM_SHAPE", "COMPOSE",
                                                                     "INSERT_GUARD"}
                             else candidate["kind"])
        if candidate["kind"] == "REPLACE":
            candidate["class"] = where.get(str(candidate.get("replacement")), "REPLACE")
        if candidate["kind"] == "COMMUTE":
            candidate["class"] = "COMMUTE"
        if candidate["kind"] == "INSERT_STATEMENT":
            candidate["class"] = "INSERT_STATEMENT"
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
