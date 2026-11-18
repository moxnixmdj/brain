"""Invent the missing operand from the target's own vocabulary, and judge it by the commit's own test.

THE GAP THIS ROUND MEASURED
---------------------------
`closed_loop_trace_abduction_repair_v1` was handed a vocabulary of edit kinds learned from OTHER
repositories' real diffs. It proposed 30 candidates per task for three real repository files, and solved
none. With an EMPTY vocabulary it proposed nothing at all. Reading the candidates showed why: every one
re-instantiates the SOURCE lesson in the SOURCE's own operands -- one candidate for `tomli/_parser.py`
contains the literal `pathlib.PureWindowsPath(path).drive`, which belongs to a `packaging` fix. A lesson
therefore transfers its syntax and loses its meaning: it carries the words of the place it was learned in,
not the place it has to speak in.

So the missing capability is not more experience, and not a cleverer search over edit kinds. It is
**operand invention**: the fix for a real commit usually introduces a name that is absent from the file
-- here `PureWindowsPath` and `.drive` appear nowhere in the target -- and no amount of experience with
other commits supplies a name that the target does not contain. The name is not invented from nothing,
though: it is present in the ENVIRONMENT, in the API of a module the target already imports. `pathlib` is
imported in the target; `PureWindowsPath` and `drive` exist in it; nothing but the file's own scope had to
be consulted.

WHAT WAS MEASURED, ON SEVEN REAL FIX COMMITS
-------------------------------------------
    failing runs that never touch the defective file        7 of 7
    engine with edit-kind lessons from other real commits   0 solved in 90 executions
    engine with an empty vocabulary                         0 proposals at all
    this module                                             1 solved in 1 execution
The solved commit is `pypa/packaging` 022ae6c6. Its test fails two cases -- `C:LICENSE` and
`d:secrets/key.txt` -- with `DID NOT RAISE`. The separating predicate is `pathlib.PureWindowsPath(x).drive`,
which is true for both failing values and false for all six passing siblings; the seat is the guard inside
`_process_license_files`; the bound name is that function's own loop variable, `path`. The candidate raises
`InvalidMetadata` where the commit's own diff adds the same `.drive` check to a neighbouring condition, and
344 tests pass. Nothing in the derivation reads the commit's diff.

An honest limitation, stated here rather than discovered later: the test underdetermines the seat. It
requires `InvalidMetadata` and says nothing about which guard must raise it, so the solver lands on the
first seat that satisfies it. That is identifiability again -- but with a constructive edge, because the
failing parameter still supplies the predicate even when it cannot supply the site.

WHAT THIS MODULE DOES, AND WHAT IT REFUSES TO DO
------------------------------------------------
    hot lines   where the commit's own failing test actually raised, taken from the traceback
    scope       the names the target already has: every name, argument and imported module
    operands    real introspection of those imported modules. No model, no network, no listing written by
                hand, no token from the answer. `getattr` on the real module object is the whole supply.
    candidates  the hot condition written with one invented operand adjoined: `(test) or (term)`,
                `(test) and (term)`. Nothing else is changed.
    judgement   the commit's own test, at its parent, unmodified. One pass is a solve.

Order is deterministic (file order of imports, then attribute name), so a term that the budget never
reaches is reported as out of budget rather than quietly skipped.

REFUSALS, NAMED
---------------
    REFUSED__NO_HOT_LINE       no traceback frame lands in the source file
    REFUSED__NO_CONDITION      the frame is not inside an if/while, so there is no condition to adjoin
    REFUSED__NO_OPERAND        introspection yielded nothing from the target's own imports
    OUT_OF_BUDGET              the candidate list was cut before the tests ran out
"""

from __future__ import annotations

import ast
import importlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE  # noqa: E402

SCHEMA = "BRAIN_OPERAND_INVENTION_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
TRIAL_CAP = 120
OPERAND_CAP = 400

SOLVED = "SOLVED"
NO_SOLVE = "INVENTED_OPERANDS_NEVER_PASS"
REFUSED_NO_HOT = "REFUSED__NO_HOT_LINE"
REFUSED_NO_COND = "REFUSED__NO_CONDITION"
REFUSED_NO_OP = "REFUSED__NO_OPERAND"
OUT_OF_BUDGET = "OUT_OF_BUDGET"

FRAME = re.compile(r'File "([^"]+)", line (\d+)')


def _run_with_tracebacks(tree: pathlib.Path, test_rel: str, timeout_s: int = 180) -> dict[str, Any]:
    """pytest with short tracebacks, because -q alone prints no frame from which to learn the hot line."""
    argv = [sys.executable, "-m", "pytest", test_rel, "-q", "--no-header", "--tb=short",
            "-p", "no:cacheprovider"]
    try:
        proc = subprocess.run(argv, cwd=str(tree), env=G._env_for(tree), capture_output=True, text=True,
                              timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"outcome": "TIMEOUT", "stdout": "", "passed": False}
    return {"outcome": "PASS" if proc.returncode == 0 else "FAIL",
            "stdout": proc.stdout + proc.stderr, "passed": proc.returncode == 0}


def hot_lines(tree: pathlib.Path, test_rel: str, source_rel: str) -> tuple[list[int], str]:
    """The lines of the source file that the failing test actually raised through, innermost last."""
    result = _run_with_tracebacks(tree, test_rel)
    if result.get("passed"):
        return [], result.get("stdout", "")[-800:]
    found: list[int] = []
    for path, line in FRAME.findall(result.get("stdout", "")):
        if pathlib.Path(path).as_posix().endswith(source_rel):
            found.append(int(line))
    return found, result.get("stdout", "")[-800:]


def imported_modules(source: str) -> list[tuple[str, Any]]:
    """The modules the file imports, in file order, as the REAL module objects."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found: list[tuple[str, Any]] = []
    for node in ast.walk(tree):
        names: list[tuple[str, str]] = []
        if isinstance(node, ast.Import):
            names = [(alias.asname or alias.name.split(".")[0], alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [(alias.asname or alias.name, f"{node.module}.{alias.name}") for alias in node.names]
        for local, dotted in names:
            try:
                module = importlib.import_module(dotted)
            except Exception:  # noqa: BLE001 - a module that will not import supplies nothing
                continue
            found.append((local, module))
    return found


def scope_names(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in names:
            names.append(node.id)
        elif isinstance(node, ast.arg) and node.arg not in names:
            names.append(node.arg)
    return names


def operands(source: str, cap: int = OPERAND_CAP) -> list[str]:
    """Terms built from the target's own imports by real introspection. Deterministic order, no peeking."""
    terms: list[str] = []
    in_scope = [name for name in scope_names(source) if not name.startswith("__")]
    strings = [name for name in in_scope if name.isidentifier() and not name.isupper()][:12]
    for local, module in imported_modules(source):
        public = sorted(name for name in dir(module) if not name.startswith("_"))
        for name in public:
            thing = getattr(module, name, None)
            if isinstance(thing, type):
                terms.append(f"{local}.{name}")
                for argument in strings:                      # a term that must be built from something here
                    try:
                        instance = thing(getattr(builtins_scope(source, argument), argument, argument))
                    except Exception:  # noqa: BLE001
                        continue
                    attrs = sorted(a for a in dir(instance) if not a.startswith("_"))
                    for attribute in attrs[:6]:
                        try:
                            value = getattr(instance, attribute)
                        except Exception:  # noqa: BLE001
                            continue
                        if isinstance(value, (str, bool, type(None))):
                            terms.append(f"{local}.{name}({argument}).{attribute}")
            elif isinstance(thing, (str, bool)):
                terms.append(f"{local}.{name}")
            if len(terms) >= cap:
                return terms[:cap]
    return terms[:cap]


def builtins_scope(source: str, name: str) -> Any:
    """The real value of a module-level literal, when the file defines one. Otherwise the name itself."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return name
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == name:
                try:
                    return ast.literal_eval(node.value)
                except Exception:  # noqa: BLE001
                    return name
    return name


def conditions(source: str, lines: Sequence[int]) -> list[tuple[int, str]]:
    """(line, condition text) for the innermost if/while that contains each hot line."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found: list[tuple[int, str]] = []
    for line in lines:
        best: tuple[int, ast.If | ast.While] | None = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While)) and node.lineno <= line <= (node.end_lineno or node.lineno):
                if best is None or node.lineno >= best[0]:
                    best = (node.lineno, node)
        if best is not None:
            text = ast.unparse(best[1].test)
            if (best[0], text) not in found:
                found.append((best[0], text))
    return found


def parametrized_values(test_source: str) -> dict[str, dict[str, list[Any]]]:
    """Every pytest.mark.parametrize list in the test file, as real values. One list per parameter name."""
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return {}
    found: dict[str, dict[str, list[Any]]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        table: dict[str, list[Any]] = {}
        decorators = getattr(node, "decorator_list", [])
        for decorator in decorators:
            if not isinstance(decorator, ast.Call) or not decorator.args:
                continue
            name = ast.unparse(decorator.func)
            if not name.endswith("parametrize"):
                continue
            who = decorator.args[0]
            names = ([part.strip() for part in who.value.split(",") if part.strip()]
                     if isinstance(who, ast.Constant) and isinstance(who.value, str)
                     else [item.value for item in getattr(who, "elts", []) if isinstance(item, ast.Constant)])
            values: list[Any] = []
            try:
                values = ast.literal_eval(decorator.args[1])
            except Exception:  # noqa: BLE001 - a computed parametrize list supplies nothing
                continue
            if not isinstance(values, (list, tuple)):
                continue
            if len(names) == 1 and not isinstance(values[0], (list, tuple)):
                table.setdefault(names[0], []).extend(values)
            else:
                for position, key in enumerate(names):
                    table.setdefault(key, []).extend(
                        [row[position] for row in values if isinstance(row, (list, tuple)) and len(row) > position])
        if table:
            found.setdefault(node.name, {}).update(table)
    return found


def failed_index(node_id: str) -> int | None:
    """pytest's trailing index of a parametrized case: `...[license_files4]` -> 4."""
    inside = node_id.rsplit("[", 1)[-1].rstrip("]") if "[" in node_id else ""
    digits = re.search(r"(\d+)$", inside)
    return int(digits.group(1)) if digits else None


def _marks_builder(thing, atoms):
    """Truth of one attribute, read element-wise, for every parameter value -- None when unusable."""
    def marks_of(attribute: str, failing: Sequence[Any], passing: Sequence[Any]) -> list[bool] | None:
        marks = []
        for value in list(failing) + list(passing):
            pieces = atoms(value)
            if not pieces:
                return None
            seen = False
            for piece in pieces:
                try:
                    seen = seen or bool(getattr(thing(piece), attribute))
                except Exception:  # noqa: BLE001 - a piece this class cannot read is not this term's evidence
                    continue
            marks.append(seen)
        return marks
    return marks_of


def separating_terms(failing: Sequence[Any], passing: Sequence[Any], source: str,
                     cap: int = OPERAND_CAP) -> list[str]:
    """Terms that are TRUE on every failing value and FALSE on every passing one -- the differential made
    into a predicate, with the words taken from the target's own imports rather than from any answer."""
    if not failing or not passing:
        return []
    terms: list[str] = []
    for local, module in imported_modules(source):
        for name in sorted(n for n in dir(module) if not n.startswith("_")):
            thing = getattr(module, name, None)
            if not isinstance(thing, type):
                continue
            def atoms(value):
                """A parameter is often a list of the things the code walks; the predicate lives on the atom."""
                return [item for item in value if isinstance(item, str)] if isinstance(value, (list, tuple)) \
                    else ([value] if isinstance(value, str) else [])

            marks_of = _marks_builder(thing, atoms)
            if marks_of is None:
                continue
            for attribute in sorted(a for a in dir(thing) if not a.startswith("_")):
                marks = marks_of(attribute, failing, passing)
                if marks is None:
                    continue
                cut = len(failing)
                if all(marks[:cut]) and not any(marks[cut:]):
                    terms.append(f"{local}.{name}(x).{attribute}")
                if len(terms) >= cap:
                    return terms[:cap]
    return terms[:cap]


def differential(test_source: str, failed_nodes: Sequence[str], source: str) -> dict[str, Any]:
    """What the failing test's own parameters say about the missing check. Only the parametrize table of the
    test function that actually failed is used -- a value from an unrelated test would be a guess dressed
    as evidence."""
    tables = parametrized_values(test_source)
    failing: list[Any] = []
    passing: list[Any] = []
    used: list[str] = []
    for node_id in failed_nodes:                      # every failing case of a table is excluded from the
        index = failed_index(node_id)                  # negatives -- a sibling failure inside the negative
        name = node_id.split("[")[0].split("::")[-1]   # set makes every predicate look non-separating, which
        table = tables.get(name)                       # is how a real differential silently returns nothing
        if table is None or index is None:
            continue
        broken = {failed_index(other) for other in failed_nodes
                  if other.split("[")[0].split("::")[-1] == name}
        for key, column in table.items():
            if index >= len(column):
                continue
            used.append(f"{name}.{key}")
            failing.append(column[index])
            passing.extend(value for position, value in enumerate(column) if position not in broken)
    return {"parameters": sorted(set(used)), "failing": failing[:6], "passing_count": len(passing),
            "terms": separating_terms(failing, passing, source)}


def sites_from_parameter(source: str, parameters: Sequence[str]) -> list[tuple[int, str]]:
    """The guards that could be missing a check, found without a traceback: when nothing raises, the only
    thread from the failing test to the defective site is the name of the parameter that carries the bad
    value. Every if/while inside a function whose name speaks of that parameter is a candidate seat."""
    stems = set()
    for dotted in parameters:
        name = dotted.split(".")[-1]
        stems.update({name.lower(), name.rstrip("s").lower()})
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    seats: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(stem and stem in node.name.lower() for stem in stems):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, (ast.If, ast.While)):
                text = ast.unparse(inner.test)
                if (inner.lineno, text) not in seats:
                    seats.append((inner.lineno, text))
    return seats[:4]


def bind(term: str, seat_line: int, source: str) -> str:
    """The term speaks the environment's words; the instance must speak the seat's. A term reading `(x)` is
    bound to the innermost loop variable that carries the value at that seat, and only then to an argument."""
    if "(x)" not in term:
        return term
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return term.replace("(x)", "(value)")
    best: tuple[int, str] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            continue
        start = getattr(node, "lineno", 0)
        end = getattr(node, "end_lineno", start) or start
        if not (start <= seat_line <= end):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if best is None or start >= best[0]:
            best = (start, node.target.id)
    if best is not None:
        return term.replace("(x)", f"({best[1]})")
    for node in ast.walk(tree):                       # no loop: the seat's own function decides
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.lineno <= seat_line <= (node.end_lineno or node.lineno):
            for argument in node.args.args[1:] or node.args.args:
                return term.replace("(x)", f"({argument.arg})")
    return term.replace("(x)", "(value)")


def rewritten(source: str, line_of: int, condition: str, term: str, operator: str) -> str | None:
    """The module with the one condition at `line_of` adjoined by the invented term."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While)) and node.lineno == line_of and ast.unparse(node.test) == condition:
            node.test = ast.parse(f"({condition}) {operator} ({term})", mode="eval").body
            ast.fix_missing_locations(tree)
            return ast.unparse(tree) + "\n"
    return None


def invent(task: Mapping[str, Any], cap: int = TRIAL_CAP) -> dict[str, Any]:
    """One real fix commit: what the failing test's own parameters say, made into a check at a real seat."""
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel, "test": test_rel}
    if not (tree / source_rel).is_file():
        return {**row, "state": REFUSED_NO_HOT}
    source = (tree / source_rel).read_text(encoding="utf-8", errors="replace")
    test_source = (tree / test_rel).read_text(encoding="utf-8", errors="replace") if (tree / test_rel).is_file() else ""
    found = differential(test_source, task.get("failed_nodes") or [], source)
    terms = found["terms"]
    row.update(parameters=found["parameters"], failing=found["failing"], passing=found["passing_count"],
               terms=len(terms), term=terms[0] if terms else None)
    if not terms:
        return {**row, "state": REFUSED_NO_OP}
    seats = sites_from_parameter(source, found["parameters"])
    row["seats"] = [line for line, _ in seats]
    if not seats:                                       # no parameter thread: fall back to the traceback
        lines, tail = hot_lines(tree, test_rel, source_rel)
        seats = conditions(source, lines)
        row["seats"] = [line for line, _ in seats]
        row["from_traceback"] = bool(seats)
        if not seats:
            return {**row, "state": REFUSED_NO_HOT, "tail": tail}
    row["trials"] = 0
    for line_of, condition in seats:
        for raw in terms:
            term = bind(raw, line_of, source)
            for operator in ("or", "and"):
                candidate = rewritten(source, line_of, condition, term, operator)
                if candidate is None:
                    continue
                row["trials"] += 1
                if G.try_candidate(tree, source_rel, test_rel, candidate)["passed"]:
                    return {**row, "state": SOLVED, "operand": term, "operator": operator,
                            "at_line": line_of, "condition": condition}
                if row["trials"] >= cap:
                    return {**row, "state": OUT_OF_BUDGET}
    return {**row, "state": NO_SOLVE}


def measure(tasks: Sequence[Mapping[str, Any]], cap: int = TRIAL_CAP) -> dict[str, Any]:
    rows = [invent(task, cap=cap) for task in tasks]
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    solved = states.get(SOLVED, 0)
    return {"schema": SCHEMA, "rows": rows, "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
            "authority": "NONE -- sandbox measurement, not independent verification",
            "totals": {"tasks": len(rows), "states": states, "solved": solved,
                       "solved_fraction": round(solved / len(rows), 4) if rows else 0.0,
                       "trials": sum(row.get("trials", 0) for row in rows)}}


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    won = [row for row in report["rows"] if row["state"] == SOLVED]
    detail = "; ".join(f"{row['repo'].split('/')[-1]} line {row.get('at_line')}: {row.get('operand')} "
                       f"{row.get('operator')}" for row in won)
    return (f"{totals['tasks']} real fix commits, operands invented from each target's own imports by real "
            f"introspection: {totals['solved']} solved ({totals['solved_fraction']}) in {totals['trials']} "
            f"executions. States: " + ", ".join(f"{s} {c}" for s, c in sorted(totals["states"].items()))
            + (f". Solved by: {detail}" if detail else "") + ".")


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path,
                        default=pathlib.Path("canonical/corpus/real_fix_commits_20261116_V1.json"))
    parser.add_argument("--hist", type=pathlib.Path, default=pathlib.Path("/tmp/hist"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/histwork"))
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--limit", type=int, default=9)
    parser.add_argument("--cap", type=int, default=TRIAL_CAP)
    parser.add_argument("--only", default="")
    args = parser.parse_args(argv)
    tasks = SHAPE.prepare_corpus(args.manifest, args.hist, args.work, limit=args.limit)
    if args.only:
        tasks = [task for task in tasks if any(bit in task["sha"] for bit in args.only.split(","))]
    report = measure(tasks, cap=args.cap)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
