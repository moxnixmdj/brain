#!/usr/bin/env python3
"""How far does ONE verified repair travel? Three rungs, counted, with the zeros kept.

WHY THIS EXISTS
---------------
`arm_learned_from_its_own_verified_repairs_v1` learns inside a run from its own judged repairs and
records, per task, what the vocabulary proposed. Its headline number is a total. That is not enough
to answer the owner's thesis, because a total hides the distinction that matters:

    a lesson that repairs the bug it came from is MEMORY OF AN INSTANCE;
    a lesson that repairs a different bug is a RULE.

This file separates them. For each repair the corpus judge accepted, one demonstration -- the
defective program and the program the judge accepted, nothing else -- is folded into the repository's
own kernel (`induced_edit_basis_v1`) and pushed up three rungs, each of which costs strictly more
generality than the one below it:

  RUNG 1  SAME BUG           does the lesson fire on its own defective program, and does the judge
                             accept what it proposes? (This is the control: if this is not ~1.0 the
                             kernel is broken and no other number here means anything.)
  RUNG 2  SAME BUG, RENAMED  the defective and repaired programs are both renamed by one consistent
                             permutation of their bound names. A lesson that survives this is about
                             structure; one that does not was about spelling. The renamed program is
                             judged with its names restored, so the corpus test is unchanged.
  RUNG 3  A DIFFERENT BUG    the same single-demonstration vocabulary, canonicalized (α-invariance),
                             is applied to every other bug in the corpus. Fires, survivors of the
                             target's own examples, and judge acceptances are counted for all of them.

The three rungs are a ladder of *transport*, and the number that answers the owner is the top rung:
how many of the other bugs a single demonstration repaired. A zero there is not a failure of the
experiment; it is the finding, and it is reported with the fire counts that produced it so a reader
can see the mechanism was live and simply had nothing to offer.

None of this touches the judge: the answer key is absent from every copy, and the corpus's own test
file is the only authority on what counts as repaired.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import sys
import tempfile
import warnings
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import grammar_closed_repair_v1 as gen  # noqa: E402
import arm_learned_from_its_own_verified_repairs_v1 as learner  # noqa: E402

SCHEMA = "BRAIN_WHAT_ONE_VERIFIED_REPAIR_TRAVELS_V1"
MAX_JUDGED_PER_TARGET = 2


def judge(root: pathlib.Path, name: str, patched: str, verify_timeout: int) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        where = pathlib.Path(tmp)
        info = gen.build_task(root, name, where)
        (where / "python_programs" / f"{name}.py").write_text(patched)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return int(gen.verify_with_corpus_test(where, info["test_path"], verify_timeout)["returncode"])


def scramble(source: str, tag: str) -> str:
    """One consistent permutation of the bound names, so defective and repaired stay aligned."""
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    bound = learner._bound_names(function)
    forward = {name: f"{tag}{index}" for index, name in enumerate(bound)}
    forward[function.name] = f"fn_{tag}"
    for inner in ast.walk(tree):
        if isinstance(inner, ast.Name) and inner.id in forward:
            inner.id = forward[inner.id]
        elif isinstance(inner, ast.arg) and inner.arg in forward:
            inner.arg = forward[inner.arg]
        elif isinstance(inner, ast.FunctionDef) and inner.name in forward:
            inner.name = forward[inner.name]
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n"


def rung_one(root: pathlib.Path, name: str, defective: str, accepted: str, function: str,
             examples: Sequence[Any], per_example_timeout: float, verify_timeout: int) -> dict[str, Any]:
    vocabulary = learner.fold([(name, defective, accepted)])
    proposals = learner.propose(defective, vocabulary)
    accepted_by_examples = [p for p in proposals
                            if _scores(p["source"], function, examples, per_example_timeout)]
    repaired = 0
    for proposal in accepted_by_examples[:MAX_JUDGED_PER_TARGET]:
        if judge(root, name, proposal["source"], verify_timeout) == 0:
            repaired += 1
            break
    return {"templates": len(vocabulary["node"]) + len(vocabulary["leaf"]),
            "fired": len(proposals), "survived_examples": len(accepted_by_examples),
            "repaired": repaired,
            "reproduces_the_accepted_program": any(
                p["source"].strip() == accepted.strip() for p in proposals)}


def rung_two(root: pathlib.Path, name: str, defective: str, accepted: str, function: str,
             examples: Sequence[Any], per_example_timeout: float, verify_timeout: int) -> dict[str, Any]:
    tag = "zq"
    try:
        renamed_defective = scramble(defective, tag)
        renamed_accepted = scramble(accepted, tag)
    except Exception:  # noqa: BLE001
        return {"applicable": False}
    vocabulary = learner.fold([(name, renamed_defective, renamed_accepted)])
    proposals = learner.propose(renamed_defective, vocabulary)
    if not proposals:
        return {"applicable": True, "fired": 0, "survived_examples": 0, "repaired": 0}
    # the renamed program's own test cannot run without a rename-consistent test, so the judge sees
    # the ORIGINAL test file and a program restored to the original names
    restorations = []
    for proposal in proposals:
        restored = _unscramble(proposal["source"], renamed_defective, defective)
        if restored is not None:
            restorations.append(restored)
    survivors = [text for text in restorations if _scores(text, function, examples, per_example_timeout)]
    repaired = 0
    for text in survivors[:MAX_JUDGED_PER_TARGET]:
        if judge(root, name, text, verify_timeout) == 0:
            repaired += 1
            break
    return {"applicable": True, "fired": len(proposals), "restored": len(restorations),
            "survived_examples": len(survivors), "repaired": repaired}


def rung_three(root: pathlib.Path, demo: tuple[str, str, str], others: Sequence[str],
               per_example_timeout: float, verify_timeout: int) -> dict[str, Any]:
    name, defective, accepted = demo
    try:
        canonical_defective, _ = learner.alpha_canonical(defective)
        canonical_accepted, _ = learner.alpha_canonical(accepted)
    except Exception:  # noqa: BLE001
        return {"applicable": False}
    vocabulary = learner.fold([(name, canonical_defective, canonical_accepted)])
    fired_on: list[str] = []
    survived: list[str] = []
    accepted_tasks: list[str] = []
    for other in others:
        source = (root / "python_programs" / f"{other}.py").read_text()
        try:
            canonical_other, reverse = learner.alpha_canonical(source)
        except Exception:  # noqa: BLE001
            continue
        proposals = learner.propose(canonical_other, vocabulary)
        if not proposals:
            continue
        fired_on.append(other)
        examples = gen.examples_of(root, other)
        if not examples:
            continue
        function = learner._function_name(source)
        judged = 0
        for proposal in proposals:
            restored = learner.alpha_restore(proposal["source"], reverse)
            if restored is None:
                continue
            if not _scores(restored, function, examples, per_example_timeout):
                continue
            survived.append(other)
            if judged < MAX_JUDGED_PER_TARGET:
                judged += 1
                if judge(root, other, restored, verify_timeout) == 0:
                    accepted_tasks.append(other)
                    break
    return {"applicable": True, "targets": len(others), "fired_on": sorted(set(fired_on)),
            "survived_examples_on": sorted(set(survived)), "repaired_on": sorted(set(accepted_tasks))}


def _scores(source: str, function: str, examples: Sequence[Any], per_example_timeout: float) -> bool:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return gen.score(source, function, examples, per_example_timeout) == len(examples)
    except Exception:  # noqa: BLE001
        return False


def _unscramble(renamed_proposal: str, renamed_defective: str, defective: str) -> str | None:
    """Invert the permutation by aligning the two programs' bound-name orders."""
    try:
        before = learner._bound_names(_function(renamed_defective))
        after = learner._bound_names(_function(defective))
    except Exception:  # noqa: BLE001
        return None
    if len(before) != len(after):
        return None
    reverse = dict(zip(before, after))
    reverse[_function(renamed_defective).name] = _function(defective).name
    return learner.alpha_restore(renamed_proposal, reverse)


def _function(source: str) -> ast.FunctionDef:
    return next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--pass-jsonl", required=True,
                        help="rows from arm_learned_from_its_own_verified_repairs_v1 --out")
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--per-example-timeout", type=float, default=0.05)
    parser.add_argument("--verify-timeout", type=int, default=120)
    args = parser.parse_args(argv)

    # every per-example timeout in this file is a SIGALRM; without the handler installed a single
    # timeout kills the process instead of being counted as a refusal (it did, at 0.05 s, on the third
    # demonstration -- which is why this line exists and why the rungs report counts, not exits)
    if not gen._install_alarm():
        print("UNMEASURABLE__NO_TIMER", file=sys.stderr)
        return 2
    root = pathlib.Path(args.quixbugs)
    rows = [json.loads(line) for line in pathlib.Path(args.pass_jsonl).read_text().splitlines() if line]
    demonstrations = [(row["task"], (root / "python_programs" / f"{row['task']}.py").read_text(),
                       row["patched"]) for row in rows if row.get("patched")]
    everything = sorted(p.stem for p in (root / "python_programs").glob("*.py")
                        if not p.stem.endswith("_test"))

    results: list[dict[str, Any]] = []
    with pathlib.Path(args.out).open("w") as handle:
        for name, defective, accepted in demonstrations:
            examples = gen.examples_of(root, name)
            function = learner._function_name(defective)
            row: dict[str, Any] = {"task": name, "examples": len(examples)}
            row["rung_1_same_bug"] = rung_one(root, name, defective, accepted, function, examples,
                                              args.per_example_timeout, args.verify_timeout)
            row["rung_2_same_bug_renamed"] = rung_two(root, name, defective, accepted, function,
                                                     examples, args.per_example_timeout,
                                                     args.verify_timeout)
            row["rung_3_a_different_bug"] = rung_three(
                root, (name, defective, accepted), [t for t in everything if t != name],
                args.per_example_timeout, args.verify_timeout)
            results.append(row)
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(f"{name:<26}r1 fired={row['rung_1_same_bug'].get('fired')} "
                  f"repaired={row['rung_1_same_bug'].get('repaired')}  "
                  f"r2 fired={row['rung_2_same_bug_renamed'].get('fired')} "
                  f"repaired={row['rung_2_same_bug_renamed'].get('repaired')}  "
                  f"r3 fired_on={len(row['rung_3_a_different_bug'].get('fired_on') or [])} "
                  f"repaired_on={row['rung_3_a_different_bug'].get('repaired_on')}", flush=True)

    folded = learner.fold([(n, learner.alpha_canonical(d)[0], learner.alpha_canonical(a)[0])
                           for n, d, a in demonstrations])
    summary = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "network_calls_at_run_time": 0,
        "demonstrations": len(demonstrations),
        "rung_1_same_bug": _summarise(results, "rung_1_same_bug"),
        "rung_2_same_bug_renamed": _summarise(results, "rung_2_same_bug_renamed"),
        "rung_3_a_different_bug": _summarise(results, "rung_3_a_different_bug"),
        "cross_demonstration_support": {
            "templates_from_all_demonstrations": len(folded["node"]) + len(folded["leaf"]),
            "templates_supported_by_two_or_more_independent_bugs": sum(
                1 for t in list(folded["node"]) + list(folded["leaf"]) if getattr(t, "support", 0) >= 2),
        },
        "rows": results,
    }
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(summary, indent=1, default=str) + "\n")
    print(json.dumps({k: summary[k] for k in ("demonstrations", "rung_1_same_bug",
                                              "rung_2_same_bug_renamed", "rung_3_a_different_bug",
                                              "cross_demonstration_support")}, indent=1, default=str))
    return 0


def _summarise(results: Sequence[dict[str, Any]], key: str) -> dict[str, Any]:
    rungs = [row[key] for row in results]
    return {"applicable": sum(1 for rung in rungs if rung.get("applicable", True)),
            "fired": sum(int(rung.get("fired", 0) or 0) for rung in rungs),
            "survived_examples": sum(int(rung.get("survived_examples", 0) or 0) for rung in rungs),
            "fired_pairs": sum(len(rung.get("fired_on") or []) for rung in rungs),
            "transfers": sum(len(rung.get("repaired_on") or []) for rung in rungs),
            "repaired": sum(int(rung.get("repaired", 0) or 0) for rung in rungs),
            "tasks_fired_on": sorted({t for rung in rungs for t in (rung.get("fired_on") or [])}),
            "count_tasks_fired_on": len({t for rung in rungs for t in (rung.get("fired_on") or [])}),
            "tasks_repaired": sorted({t for rung in rungs for t in (rung.get("repaired_on") or [])}),
            "reproduces_the_accepted_program": sum(1 for rung in rungs
                                                   if rung.get("reproduces_the_accepted_program"))}


if __name__ == "__main__":
    raise SystemExit(main())
