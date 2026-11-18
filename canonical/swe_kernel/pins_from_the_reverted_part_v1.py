"""The unpinned part is the recipe for the assertion that pins it. This composes the pieces that exist.

WHY THIS ROUND EXISTS
---------------------
Round 15 measured what a real suite certifies: 30 of 42 behavioural parts of real fixes are required, and six
of sixteen fixes carry a part the suite would accept without. Its next step was the only one that raises that
number instead of describing it -- synthesise the assertion that would pin each unpinned part.

Before writing anything, the tree was searched, and it already owns the two halves under non-obvious names:

    checkability_by_differential_pin_v1   canonical signatures of a module's calls; determinism measured
    test_oracle_strength_measure_..._v1   surviving mutants turned into concrete next assertions

Neither reaches a real fix, because both invent their own inputs from the artifact's literals, and a literal
harvested from a module is almost never the input that reaches a specific error path. The inputs that DO
reach it are already recorded in the corpus: they are the ones the human's own failing test drives through
the code.

So this is a composition, not an organ:

    inputs      the calls the failing test makes into the changed file, captured by a pytest plugin
                (`_pins_trace_plugin`) that lives in THIS repository and writes nothing into the tree
    comparison  canonical outcome signatures per call -- the tree's own idea, reused
    mutant      one part of the human's own change reverted (round 15's instrument)
    assertion   the first call whose outcome DIFFERS between fix and mutant, emitted as the assertion that
                would have caught the revert, with the argument text taken from the recipe itself
    verdict     the assertion must PASS on the fix and FAIL on the mutant. Anything else is not a pin.

WHY THE VERDICT IS THE WHOLE POINT
----------------------------------
An assertion that "looks right" is worth nothing; the tree has been burned by that before. A candidate is
counted only if it is green on the fixed state and red on the reverted state, judged by the same runner that
judges everything else. A part is then `PINNED_BY_SYNTHESIS` only if at least one such assertion exists.

Model calls 0, network calls 0. Authority NONE.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE  # noqa: E402
from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS  # noqa: E402

SCHEMA = "BRAIN_PINS_FROM_THE_REVERTED_PART_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
MAX_PARTS = 3
MAX_ASSERTIONS = 2

PINNED_BY_SYNTHESIS = "PINNED_BY_SYNTHESIS"
NOT_PINNED = "NOT_PINNED__NO_OBSERVABLE_DIFFERENCE"
REFUSED_RECEIVER = "REFUSED__RECEIVER_NOT_RECONSTRUCTIBLE"
REFUSED_CONTROL = "REFUSED__CONTROL_BROKEN"
REFUSED_TRACE = "REFUSED__NO_TRACE"

_REPO = pathlib.Path(__file__).resolve().parents[2]

_PROBE = r'''
import importlib, json, os, re, sys

ADDRESS = re.compile(r"0x[0-9a-fA-F]{6,}")
REQUEST = json.loads(os.environ["PINS_REQUEST"])
_MODULES = {}
out = []
for item in REQUEST["calls"]:
    module = _MODULES.setdefault(item["module"], importlib.import_module(item["module"]))
    target = getattr(module, item["function"], None)
    if target is None or not callable(target):
        out.append("MISSING")
        continue
    results = []
    for _ in range(2):
        try:
            value = target(*item["args"])
            text = ADDRESS.sub("0xADDR", repr(value))[:160]
            results.append("RETURNED:" + text)
        except BaseException as exc:
            message = ADDRESS.sub("0xADDR", str(exc))[:160]
            results.append("RAISED:%s:%s" % (type(exc).__name__, message))
    out.append(results[0] if results[0] == results[1] else "UNSTABLE:" + results[0][:80])
print(json.dumps(out))
'''


def module_of(source_rel: str) -> str:
    """The importable name of the changed file, from its path inside the tree."""
    parts = list(pathlib.Path(source_rel).with_suffix("").parts)
    if parts and parts[0] in ("src", "lib"):
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def calls_from_the_test(test_source: str, cap: int = 12) -> list[dict[str, Any]]:
    """The arguments the human's own test passes, and the module it passes them to -- real inputs, never invented.

    The call surface is derived from the TEST's own imports, not from the artifact's public surface: the
    tree's `public_callables` skips any function with keyword-only arguments, which silently excluded every
    usable call in the corpus (tomli's `loads(s, *, parse_float=...)`). A test that says
    `tomli.loads("val=.")` is the most reliable statement of what the code must do; nothing else needs to be
    invented.
    """
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return []
    modules: dict[str, str] = {}
    froms: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                froms[alias.asname or alias.name] = (node.module, alias.name)
    found: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        module = function = None
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                and node.func.value.id in modules:
            module, function = modules[node.func.value.id], node.func.attr
        elif isinstance(node.func, ast.Name) and node.func.id in froms:
            module, function = froms[node.func.id]
        if not module or not function:
            continue
        try:
            args = [ast.literal_eval(argument) for argument in node.args]
        except (ValueError, SyntaxError):
            continue
        if not args or len(args) > 3:
            continue
        found.append({"module": module, "function": function, "args": args})
    unique: list[dict[str, Any]] = []
    seen = set()
    for item in found:
        key = (item["module"], item["function"], repr(item["args"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= cap:
            break
    return unique


def outcomes(tree: pathlib.Path, calls: Sequence[Mapping[str, Any]]) -> list[str]:
    """One child process, full exception text (address-stripped), repeated once to prove stability."""
    if not calls:
        return []
    script = pathlib.Path(tempfile.mkdtemp(prefix="pinsprobe-")) / "probe.py"
    script.write_text(_PROBE, encoding="utf-8")
    env = G._env_for(tree)
    env["PINS_REQUEST"] = json.dumps({"calls": [dict(call) for call in calls]})
    try:
        done = subprocess.run([sys.executable, str(script)], cwd=str(tree), env=env,
                              capture_output=True, text=True, timeout=180)
        return json.loads(done.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError, IndexError, OSError):
        return ["PROBE_FAILED"] * len(calls)


def _assertion(call: Mapping[str, Any], outcome: str) -> str | None:
    args = ", ".join(repr(argument) for argument in call["args"])
    expression = f"_m.{call['function']}({args})"
    kind, _, rest = outcome.partition(":")
    if kind == "RAISED":
        exc, _, message = rest.partition(":")
        if not exc.isidentifier() or not message:
            return None
        return (f"with pytest.raises(_exc({exc!r}), match=re.escape({message!r})):\n"
                f"        {expression}")
    if kind == "RETURNED" and rest and not rest.startswith("<"):
        try:
            ast.literal_eval(rest)
        except (ValueError, SyntaxError):
            return None
        return f"assert {expression} == {rest}"
    return None


def _testfile(assertion: str, module: str) -> str:
    return ("import builtins\nimport re\nimport pytest\nimport " + module + " as _m\n\n\n"
            "def _exc(name):\n    return getattr(_m, name, getattr(builtins, name, Exception))\n\n\n"
            "def test_pin():\n    "
            + assertion + "\n")


def pin_part(tree: pathlib.Path, source_rel: str, test_rel: str, fixed: str, mutant: str,
             calls: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """One reverted part, judged by whether a synthesised assertion is green on the fix and red on the mutant."""
    target = tree / source_rel
    original = target.read_bytes()
    synth = tree / "_pins_synth_test.py"
    try:
        target.write_text(fixed, encoding="utf-8")
        hot = outcomes(tree, calls)
        target.write_text(mutant, encoding="utf-8")
        cold = outcomes(tree, calls)
        differing = [(call, hot[index]) for index, call in enumerate(calls)
                     if index < len(hot) and index < len(cold) and hot[index] != cold[index]
                     and not hot[index].startswith(("UNSTABLE", "PROBE_FAILED"))]
        if not differing:
            return {"state": NOT_PINNED, "differences": 0, "assertions_tried": 0}
        tried = 0
        for call, outcome in differing[:MAX_ASSERTIONS]:
            assertion = _assertion(call, outcome)
            if assertion is None:
                continue
            tried += 1
            synth.write_text(_testfile(assertion, call["module"]), encoding="utf-8")
            target.write_text(fixed, encoding="utf-8")
            green = G.run_test(tree, synth.name)["passed"]
            target.write_text(mutant, encoding="utf-8")
            red = not G.run_test(tree, synth.name)["passed"]
            if green and red:
                return {"state": PINNED_BY_SYNTHESIS, "assertion": assertion.splitlines()[-1].strip(),
                        "observes": f"{call['function']}({call['args']!r})", "outcome": outcome[:120]}
        if differing and not tried:
            return {"state": REFUSED_RECEIVER, "differences": len(differing), "assertions_tried": 0,
                    "example": differing[0][1][:160]}
        return {"state": NOT_PINNED, "differences": len(differing), "assertions_tried": tried}
    finally:
        target.write_bytes(original)
        synth.unlink(missing_ok=True)


def audit_task(task: Mapping[str, Any], grammar: Sequence[Mapping[str, Any]],
               cap: int = MAX_PARTS) -> dict[str, Any]:
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    entry = next((g for g in grammar if g["sha"] == task["sha"] and g["source"] == source_rel), None)
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel}
    if entry is None:
        return {**row, "state": PINS.REFUSED_NO_GRAMMAR}
    fixed, defective = entry["repaired"], entry["defective"]
    if G.try_candidate(tree, source_rel, test_rel, defective)["passed"] or \
            not G.try_candidate(tree, source_rel, test_rel, fixed)["passed"]:
        return {**row, "state": REFUSED_CONTROL}
    test_source = (tree / test_rel).read_text(encoding="utf-8", errors="replace") \
        if (tree / test_rel).is_file() else ""
    module = module_of(source_rel)
    calls = calls_from_the_test(test_source)
    row["calls_from_the_test"] = len(calls)
    judged: list[dict[str, Any]] = []
    for part in PINS.hunks(defective, fixed):
        if len(judged) >= cap:
            break
        if not PINS.is_behavioural(fixed, part) or PINS.typing_only(fixed, part):
            continue
        mutant = PINS.revert(fixed, defective, part)
        if G.try_candidate(tree, source_rel, test_rel, mutant)["passed"] is False:
            continue                                   # already pinned by the suite; round 15 counted it
        verdict = pin_part(tree, source_rel, test_rel, fixed, mutant, calls)
        judged.append({**verdict, "part_head": part["added"][:160]})
    pinned = sum(1 for item in judged if item["state"] == PINNED_BY_SYNTHESIS)
    return {**row, "unpinned_parts": len(judged), "pinned_by_synthesis": pinned, "parts": judged,
            "state": PINNED_BY_SYNTHESIS if pinned else (NOT_PINNED if judged else PINS.FULLY_PINNED)}


def measure(tasks: Sequence[Mapping[str, Any]], grammar: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [audit_task(task, grammar) for task in tasks]
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    unpinned = sum(row.get("unpinned_parts") or 0 for row in rows)
    pinned = sum(row.get("pinned_by_synthesis") or 0 for row in rows)
    parts = [item for row in rows for item in (row.get("parts") or [])]
    return {
        "schema": SCHEMA, "rows": rows, "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "totals": {"tasks": len(rows), "states": states, "unpinned_parts_audited": unpinned,
                   "pinned_by_synthesis": pinned,
                   "share_of_unpinned_pinned": (round(pinned / unpinned, 3) if unpinned else None),
                   "refused_receiver": sum(1 for item in parts if item["state"] == REFUSED_RECEIVER),
                   "no_observable_difference": sum(1 for item in parts if item["state"] == NOT_PINNED)},
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    won = [row for row in report["rows"] if row.get("pinned_by_synthesis")]
    detail = "; ".join(f"{row['repo'].split('/')[-1]} {row['sha'][:8]}: "
                       + " | ".join(item["assertion"] for item in row["parts"]
                                    if item["state"] == PINNED_BY_SYNTHESIS) for row in won)
    return (f"{totals['tasks']} real fixes, {totals['unpinned_parts_audited']} parts the suite accepts without: "
            f"{totals['pinned_by_synthesis']} pinned by a synthesised assertion "
            f"({totals['share_of_unpinned_pinned']}); refusals {totals['refused_receiver']} receiver, "
            f"{totals['no_observable_difference']} no-difference. States: "
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
    grammar = json.loads(args.manifest.read_text(encoding="utf-8"))["grammar"]
    report = measure(tasks, grammar)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
