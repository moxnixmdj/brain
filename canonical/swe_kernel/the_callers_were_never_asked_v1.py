"""The callers were never asked: real arguments from real call sites, outside the changed module and its test.

WHAT THE LAST SIX ROUNDS LEFT
-----------------------------
Every source of the discriminating input has now been priced against the same residual work -- the parts a change's
own suite accepts without pinning: input shape (round 17), the value a condition wants (18), the repository's own
documents (19), the language's protocol operations (20), and the author's own statement (21, names 50-55% and
specifies 0 of 19).

One source was never asked, and it is the only one that is not the author talking about the change: **the code that
calls the changed function.** Callers are real usage. They pass concrete arguments, they are written by the same
people for the same program, and they sit outside both the changed module and the test that failed to pin it.

    round 19 asked the repository for DOCUMENTS      (data files and test literals)
    round 22 asks the repository for CALL SITES      (arguments a program actually passes)

WHY THAT IS A DIFFERENT QUESTION
--------------------------------
A test literal is chosen to make an assertion readable; a call-site argument is chosen because the program needs
that value to do its work. Round 19 found documents could enter a parser but not separate the two states; a call
site is different in kind, because a caller exists only if that argument was believed correct against the OLD
behaviour -- precisely the tension a behaviour change creates.

WHAT IT DOES
------------
    callables   every function or class the changed module defines, plus every callable the failing test calls
    call sites  every `.py` file in the repository except the changed module and the changed test, parsed, looking
                for a call of one of those names with LITERAL arguments
    candidates  (callable, literal argument tuple) pairs, de-duplicated
    pin         the candidate is called at the fixed state and at the reverted state; only a candidate whose
                outcomes DIFFER is turned into an assertion, and the assertion must pass at fixed and fail at the
                reverted part before it counts

WHAT IS NOT DONE
----------------
No model, no network at measurement time, no stored knowledge. Arguments are harvested, never invented: a call site
that passes only names or expressions contributes nothing. Everything that runs, runs in a child process against a
materialised checkout that is restored afterwards.
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import checkability_by_differential_pin_v1 as C  # noqa: E402  the two-state prober
from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import pins_from_the_reverted_part_v1 as SYN  # noqa: E402
from canonical.swe_kernel import reach_the_changed_site_v1 as R  # noqa: E402
from canonical.swe_kernel import the_smallest_question_that_makes_this_checkable_v1 as Q  # noqa: E402
from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS  # noqa: E402

SCHEMA = "BRAIN_THE_CALLERS_WERE_NEVER_ASKED_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
MAX_PARTS = 3
MAX_CANDIDATES = 40
MAX_FILES = 400
PIN_TEST_NAME = "test_round22_caller_pin.py"
SKIP_DIRS = {".git", ".hg", ".venv", "venv", "node_modules", "__pycache__", "build", "dist", ".tox", ".mypy_cache"}


def defined_names(source: str) -> list[str]:
    """What the changed module itself defines. Only those can be called by a caller through their own name."""
    try:
        parsed = ast.parse(source)
    except SyntaxError:
        return []
    return [node.name for node in parsed.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]


def _literal(node: ast.AST) -> Any:
    """A literal, or nothing. A caller that passes a name states no value, and nothing is invented here."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bytes)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant) \
            and isinstance(node.operand.value, (int, float)):
        return -node.operand.value
    return None


def harvest_call_sites(tree: pathlib.Path, source_rel: str, test_rel: str,
                       names: Sequence[str], limit: int = MAX_CANDIDATES) -> list[dict[str, Any]]:
    """Every literal argument the repository passes to one of `names`, from any file that is not the change or its test."""
    wanted = set(names)
    found: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    scanned = 0
    for path in sorted(tree.rglob("*.py")):
        if scanned >= MAX_FILES or len(found) >= limit:
            break
        rel = str(path.relative_to(tree))
        if rel in (source_rel, test_rel) or any(part in SKIP_DIRS for part in path.parts):
            continue
        scanned += 1
        try:
            parsed = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(parsed):
            if not isinstance(node, ast.Call):
                continue
            target = node.func
            name = target.id if isinstance(target, ast.Name) else (target.attr if isinstance(target, ast.Attribute) else None)
            if name not in wanted or not node.args:
                continue
            literals = [_literal(argument) for argument in node.args]
            if any(value is None for value in literals):
                continue                       # the caller passed something that is not a literal: states no value
            key = (name, json.dumps(literals, default=repr))
            if key in seen:
                continue
            seen.add(key)
            found.append({"name": name, "args": literals, "site": rel})
    return found[:limit]


def module_of(source_rel: str) -> str:
    """The import path of the changed module, read from where it lives. `src/pkg/mod.py` -> `pkg.mod`."""
    parts = [piece for piece in source_rel.replace("\\", "/").split("/") if piece]
    if parts and parts[0] in ("src", "lib"):
        parts = parts[1:]
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def candidates_for(call_sites: Sequence[Mapping[str, Any]],
                   seeds: Sequence[Mapping[str, Any]],
                   defined_in: Sequence[str] = (),
                   module: str | None = None) -> list[dict[str, Any]]:
    """A harvested call becomes a probe only when a module that defines it is known how to import.

    The changed module's OWN definitions map to it: a repository file that calls `utils.parse_wheel_filename` names a
    function this change edited, whether or not the failing test ever touched it. The first version of this mapped
    only the names the test called, so 168 harvested call sites produced exactly one candidate.
    """
    by_name: dict[str, str] = {}
    for seed in seeds:
        by_name.setdefault(seed["function"], seed["module"])
    if module:
        for name in defined_in:
            by_name.setdefault(name, module)
    calls, seen = [], set()
    for site in call_sites:
        module = by_name.get(str(site["name"]))
        if module is None:
            continue
        tokens = []
        for argument in site["args"]:
            if isinstance(argument, str):
                tokens.append("=" + argument)
            elif isinstance(argument, bytes):
                continue
            else:
                try:
                    tokens.append("@json:" + json.dumps(argument))
                except (TypeError, ValueError):
                    continue
        if not tokens or len(tokens) != len(site["args"]):
            continue
        key = (module, site["name"], tuple(tokens))
        if key in seen:
            continue
        seen.add(key)
        calls.append({"module": module, "function": site["name"], "args": tokens, "site": site["site"]})
    return calls


def judge_part(tree: pathlib.Path, source_rel: str, fixed: str, mutant: str,
               calls: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Probe every harvested call at both states; a pin must pass at fixed and fail at the reverted part."""
    if not calls:
        return {"state": "REFUSED__NO_LITERAL_CALL_SITE", "candidates": 0}
    target = tree / source_rel
    original = target.read_bytes()
    try:
        target.write_text(fixed, encoding="utf-8")
        at_fixed = C.probe(tree, list(calls))
        target.write_text(mutant, encoding="utf-8")
        at_mutant = C.probe(tree, list(calls))
    finally:
        target.write_bytes(original)
    if not at_fixed or len(at_fixed) != len(at_mutant):
        return {"state": "REFUSED__PROBE_FAILED", "candidates": len(calls)}
    differences = [(call, left, right) for call, left, right in zip(calls, at_fixed, at_mutant)
                   if C._signature(left) != C._signature(right)]
    pin_file = tree / PIN_TEST_NAME
    verified: dict[str, Any] | None = None
    try:
        for call, left, right in differences:
            source = Q._pin_source(call, left, fixed)
            if source is None:
                continue
            pin_file.write_text(source, encoding="utf-8")
            if not G.try_candidate(tree, source_rel, PIN_TEST_NAME, fixed)["passed"]:
                continue
            if G.try_candidate(tree, source_rel, PIN_TEST_NAME, mutant)["passed"]:
                continue
            verified = {"callable": f"{call['module']}.{call['function']}", "args": call["args"],
                        "found_at": call["site"], "fixed": C._signature(left),
                        "reverted": C._signature(right), "assertion": source}
            break
    finally:
        pin_file.unlink(missing_ok=True)
    return {"state": "PINNED_BY_A_CALLER" if verified else "NO_SEPARATING_CALL", "candidates": len(calls),
            "differences": len(differences), "pin": verified}


def audit_task(task: Mapping[str, Any], grammar: Sequence[Mapping[str, Any]], cap: int = MAX_PARTS) -> dict[str, Any]:
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    entry = next((g for g in grammar if g["sha"] == task["sha"] and g["source"] == source_rel), None)
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel}
    if entry is None:
        return {**row, "state": PINS.REFUSED_NO_GRAMMAR}
    fixed, defective = entry["repaired"], entry["defective"]
    if G.try_candidate(tree, source_rel, test_rel, defective)["passed"] or \
            not G.try_candidate(tree, source_rel, test_rel, fixed)["passed"]:
        return {**row, "state": R.REFUSED_CONTROL}
    test_source = (tree / test_rel).read_text(encoding="utf-8", errors="replace") \
        if (tree / test_rel).is_file() else ""
    seeds = [{"module": call["module"], "function": call["function"]}
             for call in SYN.calls_from_the_test(test_source)
             if isinstance(call.get("module"), str) and isinstance(call.get("function"), str)]
    names = sorted(set(defined_names(fixed)) | {seed["function"] for seed in seeds})
    sites = harvest_call_sites(tree, source_rel, test_rel, names)
    calls = candidates_for(sites, seeds, defined_names(fixed), module_of(source_rel))
    def _is_test(path: str) -> bool:
        name = path.rsplit("/", 1)[-1]
        return name.startswith("test_") or name.endswith("_test.py") or "/tests/" in path or "/test/" in path

    row.update({"defined": len(defined_names(fixed)), "call_sites": len(sites), "candidates": len(calls),
                "call_sites_in_tests": sum(1 for site in sites if _is_test(str(site["site"]))),
                "call_sites_in_source": sum(1 for site in sites if not _is_test(str(site["site"])))})
    judged: list[dict[str, Any]] = []
    for part in PINS.hunks(defective, fixed):
        if len(judged) >= cap:
            break
        if not PINS.is_behavioural(fixed, part) or PINS.typing_only(fixed, part):
            continue
        mutant = PINS.revert(fixed, defective, part)
        if G.try_candidate(tree, source_rel, test_rel, mutant)["passed"] is False:
            continue                        # the suite already pins this part
        verdict = judge_part(tree, source_rel, fixed, mutant, calls)
        verdict["part_head"] = str(part.get("added") or "").strip()[:120] or "(removal)"
        judged.append(verdict)
    pinned = sum(1 for item in judged if item["state"] == "PINNED_BY_A_CALLER")
    return {**row, "parts": judged, "unpinned_parts": len(judged), "pinned": pinned,
            "state": "PINNED_BY_A_CALLER" if pinned else (PINS.FULLY_PINNED if not judged else "NO_SEPARATING_CALL")}


def measure(tasks: Sequence[Mapping[str, Any]], grammar: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [audit_task(task, grammar) for task in tasks]
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    parts = [item for row in rows for item in (row.get("parts") or [])]
    pinned = [item for item in parts if item["state"] == "PINNED_BY_A_CALLER"]
    return {
        "schema": SCHEMA, "rows": rows, "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "kill_criterion": "if caller-harvested arguments do not pin strictly more residual parts than the six "
                          "sources already spent (0 added by rounds 18-21), the source is dead",
        "totals": {
            "tasks": len(rows), "states": states, "parts_audited": len(parts), "parts_pinned": len(pinned),
            "call_sites_harvested": sum(row.get("call_sites") or 0 for row in rows),
            "call_sites_in_tests": sum(row.get("call_sites_in_tests") or 0 for row in rows),
            "call_sites_in_source": sum(row.get("call_sites_in_source") or 0 for row in rows),
            "candidates_probed": sum(item.get("candidates") or 0 for item in parts),
            "separating_calls": sum(item.get("differences") or 0 for item in parts),
            "gain_over_the_six_spent_sources": len(pinned),
            "certified_share_before": 0.762,
            "certified_share_after": round((32 + len(pinned)) / 42, 3) if parts else None,
        },
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    won = [(row, item) for row in report["rows"] for item in (row.get("parts") or [])
           if item["state"] == "PINNED_BY_A_CALLER"]
    detail = "; ".join(f"{row['repo'].split('/')[-1]} {row['sha'][:8]}: {(item['pin'] or {}).get('args')} "
                       f"from {(item['pin'] or {}).get('found_at')}" for row, item in won)
    return (f"{totals['tasks']} real fixes: {totals['parts_audited']} parts the suite accepts without. "
            f"{totals['call_sites_harvested']} literal call sites were found in the repositories' own code "
            f"({totals['call_sites_in_tests']} of them in a test, {totals['call_sites_in_source']} in source), giving "
            f"{totals['candidates_probed']} candidate calls. {totals['separating_calls']} of them separate the two "
            f"states; {totals['parts_pinned']} parts pinned by a caller. Gain over the six spent sources: "
            f"+{totals['gain_over_the_six_spent_sources']}. Certified share {totals['certified_share_before']} -> "
            f"{totals['certified_share_after']}." + (f" {detail}" if detail else ""))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path,
                        default=pathlib.Path("canonical/corpus/real_fix_commits_20261116_V1.json"))
    parser.add_argument("--hist", type=pathlib.Path, default=pathlib.Path("/tmp/hist"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/histwork"))
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--limit", type=int, default=24)
    args = parser.parse_args(argv)
    from canonical.swe_kernel import structural_rewrite_induction_v1 as SHAPE
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
