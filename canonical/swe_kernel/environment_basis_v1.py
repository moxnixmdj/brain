"""The knowledge base is the environment. This measures how much reach that actually buys.

THE ARGUMENT, STATED BEFORE ANY NUMBER
-------------------------------------
A pretrained model is a compressed knowledge house: it generalises to what it saw. An agent that refuses
weights must generalise some other way, and there is exactly one honest alternative that is not a smaller
knowledge house -- **recombine what the live environment contains**. For a closed world (a machine, a
process, a repository) everything needed to act is expressible in terms of the objects present: their
methods, their attributes, the modules already imported, the values observed at the failure. No name has to
be remembered from a corpus, because every name is introspectable at the moment of use.

That claim is falsifiable in one specific place, so this module tests exactly there:

    round 11's proposer offered `module.Class(x).attribute` for modules the target imports, and reached
    ONE commit in seventeen. Everything else was reported as REFUSED__NO_PARTITION -- no separating term,
    not "no bug".

If the environment-as-knowledge-base claim is true, the refusals should fall when the supply widens to
expressions over the LIVE VALUES -- `x.attr`, `x.method()`, `module.function(x)`, `module.Class(x).attr`,
`x.method().attr` -- because those are legal at the seat without adding an import and require nothing that
was not already present in the process.

WHAT IS AND IS NOT WIDENED
-------------------------
Widened: the *supply of terms*. Side-effect-free, zero-required-argument accessors and one-argument public
functions, depth <= 2, taken by real introspection of the values and of the target's own imported modules.

Not widened, deliberately: the seats (still the guards of the functions the failing parameter names), the
judge (still the commit's own test at its parent), the operator set (`or`/`and`), and the separation filter
(a term must be TRUE on every failing value and FALSE on every passing sibling). A wider supply that also
widened the judge would measure nothing: the judge is what makes any of this a fact.

THE COST THAT DECIDES WHETHER IT IS USABLE
------------------------------------------
Term generation and separation are in-process and free (no subprocess, no test run). Only terms that survive
separation reach the judge, so the expensive resource -- one test execution per candidate -- is spent on
hypotheses that already explain the observed differential. This module reports both counts, because a
mechanism that reaches four commits by running a thousand suites is not a capability, it is a lottery.

Model calls 0, network calls 0. Authority NONE.
"""

from __future__ import annotations

import ast
import inspect
import json
import pathlib
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import operand_invention_v1 as OPERAND  # noqa: E402
from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE  # noqa: E402

SCHEMA = "BRAIN_ENVIRONMENT_BASIS_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0

TERM_CAP = 64
TRIAL_CAP = 24
DEPTH = 2
# Names whose invocation is not a question about the value. Kept short and explicit: a deny list that grows
# without bound would silently become the real hypothesis space.
_DENY = ("write", "dump", "save", "remove", "unlink", "system", "popen", "open", "commit", "send",
         "exec", "eval", "compile", "exit", "kill", "format", "format_map", "encode")

SOLVED = "SOLVED__THE_ENVIRONMENT_SUPPLIED_THE_TERM"
REFUSED_NO_TERM = "REFUSED__NO_SEPARATING_TERM"
REFUSED_NO_PARTITION = "REFUSED__NO_PARTITION"
OUT_OF_BUDGET = "OUT_OF_BUDGET"

_SAFE_TYPES = (str, bytes, int, float, bool, type(None), list, tuple, dict, set, frozenset)


def _atoms(value: Any) -> list[str]:
    """A parameter is often a list of the things the code walks; the predicate lives on the atom."""
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str):
        return [value]
    return []


def _evaluate(template: str, value: str) -> Any:
    """One template, one value, no builtins beyond what a template provably needs."""
    try:
        return eval(template, {"__builtins__": {"len": len, "str": str, "repr": repr, "ord": ord,
                                                "sorted": sorted, "tuple": tuple, "list": list,
                                                "set": set, "bool": bool, "int": int}},
                    {"x": value})
    except Exception:  # noqa: BLE001 - a template the value cannot accept is not evidence about the value
        return None


def _shape(value: str) -> list[str]:
    """Every side-effect-free expression of depth <= 2 over one live string, from the value's own type."""
    found: list[str] = ["(x)", "len((x))"]
    attrs = sorted(a for a in dir(type(value)) if not a.startswith("_") and a not in _DENY)
    for name in attrs:
        try:
            member = getattr(type(value), name, None)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(member, property):
            found.append(f"(x).{name}")
            continue
        if not callable(member):
            continue
        try:
            signature = inspect.signature(member)
        except (TypeError, ValueError):
            continue
        parameters = list(signature.parameters.values())
        # read through the TYPE, a method still declares `self`; the live value already supplies it
        if parameters and parameters[0].name in ("self", "cls"):
            parameters = parameters[1:]
        required = [p for p in parameters
                    if p.default is p.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
        if required:
            continue
        found.append(f"(x).{name}()")
    # depth 2: an attribute or zero-argument method of whatever depth 1 produced
    for base in list(found)[:24]:
        try:
            produced = eval(base, {"__builtins__": {"len": len}}, {"x": value})
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(produced, _SAFE_TYPES):
            continue
        for name in sorted(a for a in dir(type(produced)) if not a.startswith("_") and a not in _DENY)[:12]:
            member = getattr(type(produced), name, None)
            if isinstance(member, property):
                found.append(f"({base}).{name}")
    return found


def _module_terms(source: str, value: str) -> list[str]:
    """One-argument public functions and classes of the target's OWN imports, applied to the live value."""
    found: list[str] = []
    for local, module in OPERAND.imported_modules(source):
        for name in sorted(n for n in dir(module) if not n.startswith("_")):
            thing = getattr(module, name, None)
            if isinstance(thing, type):
                found.append(f"{local}.{name}((x))")
                continue
            if not callable(thing):
                continue
            try:
                signature = inspect.signature(thing)
            except (TypeError, ValueError):
                continue
            required = [p for p in signature.parameters.values()
                        if p.default is p.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            if len(required) != 1:
                continue
            found.append(f"{local}.{name}((x))")
    return found


def environment_terms(failing: Sequence[Any], passing: Sequence[Any], source: str,
                      cap: int = TERM_CAP) -> dict[str, Any]:
    """Terms that separate the observed failing values from their passing siblings, taken from the live API.

    Separation is decided by evaluation, not by reading: a term qualifies only if it is truthy for every
    failing value and falsy for every passing value, element-wise over list parameters.
    """
    atoms_failing = [atom for value in failing for atom in _atoms(value)]
    atoms_passing = [atom for value in passing for atom in _atoms(value)]
    if not atoms_failing or not atoms_passing:
        return {"terms": [], "considered": 0, "evaluations": 0, "atoms": (len(atoms_failing), len(atoms_passing))}

    seeds = list(dict.fromkeys(atoms_failing[:4] + atoms_passing[:4]))
    templates: list[str] = []
    for seed in seeds:
        templates.extend(_shape(seed))
    templates.extend(_module_terms(source, atoms_failing[0]))
    templates = list(dict.fromkeys(templates))

    terms: list[str] = []
    evaluations = 0

    def marks(template: str) -> bool:
        nonlocal evaluations
        hot = False
        for atom in atoms_failing:
            evaluations += 1
            if not bool(_evaluate(template, atom)):
                return False
            hot = True
        if not hot:
            return False
        for atom in atoms_passing:
            evaluations += 1
            if bool(_evaluate(template, atom)):
                return False
        return True

    for template in templates:
        if marks(template):
            terms.append(template)
            if len(terms) >= cap:
                break
    return {"terms": terms, "considered": len(templates), "evaluations": evaluations,
            "atoms": (len(atoms_failing), len(atoms_passing))}


def repair_with_basis(task: Mapping[str, Any], cap: int = TRIAL_CAP) -> dict[str, Any]:
    """Widen the supply, keep every other constraint, judge with the commit's own tests."""
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel}
    if not (tree / source_rel).is_file():
        return {**row, "state": REFUSED_NO_PARTITION, "solved": False}
    source = (tree / source_rel).read_text(encoding="utf-8", errors="replace")
    test_source = (tree / test_rel).read_text(encoding="utf-8", errors="replace") if (tree / test_rel).is_file() else ""
    found = OPERAND.differential(test_source, task.get("failed_nodes") or [], source)
    if not found["parameters"]:
        return {**row, "state": REFUSED_NO_PARTITION, "solved": False, "narrow_terms": 0}
    widened = environment_terms(found["failing"], _passing_values(found, test_source, source), source)
    # UNION, never replacement: the narrow supply is the baseline this round is measured against, and a
    # widening that deletes a term the baseline already had is not a widening.
    basis = {**widened, "terms": list(dict.fromkeys(list(found["terms"]) + list(widened["terms"])))}
    row.update({"narrow_terms": len(found["terms"]), "basis_terms": basis["terms"],
                "considered": basis["considered"], "evaluations": basis["evaluations"]})
    if not basis["terms"]:
        return {**row, "state": REFUSED_NO_TERM, "solved": False}

    seats = OPERAND.sites_from_parameter(source, found["parameters"])[:4]
    trials = 0
    for template in basis["terms"]:
        for line_of, condition in seats:
            term = OPERAND.bind(template, line_of, source)
            for operator in ("or", "and"):
                candidate = OPERAND.rewritten(source, line_of, condition, term, operator)
                if candidate is None:
                    continue
                trials += 1
                row["trials"] = trials
                if G.try_candidate(tree, source_rel, test_rel, candidate)["passed"]:
                    return {**row, "state": SOLVED, "solved": True, "at_line": line_of,
                            "condition": condition, "term": term, "operator": operator, "trials": trials}
                if trials >= cap:
                    return {**row, "state": OUT_OF_BUDGET, "solved": False, "trials": trials}
    return {**row, "state": REFUSED_NO_TERM, "solved": False, "trials": trials}


def _passing_values(found: Mapping[str, Any], test_source: str, source: str) -> list[Any]:
    """The passing siblings, recovered the same way `differential` built its counts."""
    tables = OPERAND.parametrized_values(test_source)
    passing: list[Any] = []
    for parameter in found["parameters"]:
        name, key = parameter.split(".", 1)
        table = tables.get(name) or {}
        column = table.get(key) or []
        failing = set()
        for value in found["failing"]:
            for position, candidate in enumerate(column):
                if candidate == value:
                    failing.add(position)
        passing.extend(value for position, value in enumerate(column) if position not in failing)
    return passing


def measure(tasks: Sequence[Mapping[str, Any]], cap: int = TRIAL_CAP) -> dict[str, Any]:
    rows = [repair_with_basis(task, cap) for task in tasks]
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    return {
        "schema": SCHEMA, "rows": rows, "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "totals": {
            "tasks": len(rows), "states": states,
            "solved": sum(1 for row in rows if row.get("solved")),
            "narrow_terms_total": sum(row.get("narrow_terms") or 0 for row in rows),
            "basis_terms_total": sum(len(row.get("basis_terms") or []) for row in rows),
            "templates_considered": sum(row.get("considered") or 0 for row in rows),
            "evaluations": sum(row.get("evaluations") or 0 for row in rows),
            "test_executions": sum(row.get("trials") or 0 for row in rows),
        },
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    solved = [row for row in report["rows"] if row.get("solved")]
    detail = "; ".join(f"{row['repo'].split('/')[-1]} {row['sha'][:8]} via `{row['term']}` at line "
                       f"{row['at_line']} after {row['trials']} execution(s)" for row in solved)
    return (f"{totals['tasks']} real fix commits, supply widened to the live environment API: "
            f"{totals['solved']} solved, {totals['basis_terms_total']} separating terms from "
            f"{totals['templates_considered']} templates ({totals['evaluations']} in-process evaluations, "
            f"{totals['test_executions']} test executions). States: "
            + ", ".join(f"{state} {count}" for state, count in sorted(totals["states"].items()))
            + (f". {detail}" if detail else "") + ".")


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path,
                        default=pathlib.Path("canonical/corpus/real_fix_commits_20261116_V1.json"))
    parser.add_argument("--hist", type=pathlib.Path, default=pathlib.Path("/tmp/hist"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/histwork"))
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--limit", type=int, default=9)
    args = parser.parse_args(argv)
    tasks = SHAPE.prepare_corpus(args.manifest, args.hist, args.work, limit=args.limit)
    report = measure(tasks)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
