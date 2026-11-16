#!/usr/bin/env python3
"""Learning from its own verified repairs, inside the run -- and one invariance, tested, as the lever.

WHY THIS EXISTS
---------------
`COMPOSED_REPAIR_ONE_RUN_20261116_V1` ran three vocabularies under one judge and repaired 24 of 40.
Its third arm was a **replay**: the learned kinds came from a record whose lesson corpus is not in
this repository, so that arm could re-cite a lesson but never re-learn one. The strongest number this
project ever quoted for "learned" capability therefore rests, at exactly one point, on a record
rather than on a mechanism.

This closes that hole with the kernel that already exists -- `induced_edit_basis_v1` -- and with one
addition that is a principle rather than a fact: **bound names are α-renameable.** A program that
counts bits is not about `n`; a repair that turns `x ^= x - 1` into `x &= x - 1` is not about `x`.
The kernel generalizes an edit by anti-unifying the two sides of ONE demonstration, so with one
demonstration per kind there is nothing to anti-unify and every template comes out LITERAL: its
precondition is the demonstration's exact spelling. Renaming every *bound* name (parameters and
assignment targets -- never globals or builtins, which are free) to a canonical `n0, n1, ...` before
inducing, and canonicalizing the target the same way before matching, makes the precondition
structural. One function, no bug knowledge, and the difference between memory of an instance and a
rule becomes measurable instead of arguable.

WHAT THE RUN MEASURES, IN ONE PASS, WITH NO LOOKAHEAD
-----------------------------------------------------
Task order is fixed. The vocabulary may only be built from repairs the corpus's own pytest accepted
on tasks EARLIER in the same pass, so every task is repaired cold with respect to the tasks after it:
no answer key, no record, no cross-corpus lesson. Two arms read that vocabulary:

  ALPHA_LEARNED_THIS_RUN  templates induced from α-renamed demonstrations, matched against the
                          α-renamed target, candidate mapped back to the target's real names
  LEARNED_THIS_RUN        the same kernel on raw sources (the literal-precondition control)

Both run FIRST, before the three known arms, because if they ran last a win would be invisible. Each
row records, per arm, how many templates existed, how many candidates were proposed, how many
survived the program's own examples, and how many the corpus judge refused -- so a null result is a
counted null and not an absence of instrumentation. Every accepted repair carries the exact program
the judge accepted (`patched`), and that artifact -- never a reconstruction of it -- is the lesson.

WHAT THIS CANNOT CLAIM
----------------------
- A win on a bug the three arms already repair is a COST win; the receipt labels it.
- Templates substitute inside an existing node. A fix that needs a new statement is proposed-and-
  refused, never approximated.
- Firing rates are reported including the zeros, per template, so "how far one demonstration
  travels" is answered with a distribution and not with the best case.

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
import time
import warnings
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import grammar_closed_repair_v1 as gen  # noqa: E402
import rerun_the_learned_arms_repairs_v1 as replay  # noqa: E402
import synthesized_expression_from_the_failure_v1 as synth  # noqa: E402
from canonical.swe_kernel import induced_edit_basis_v1 as basis  # noqa: E402

SCHEMA = "BRAIN_ARM_LEARNED_IN_ONE_RUN_V1"
ARMS = ("ALPHA_LEARNED_THIS_RUN", "LEARNED_THIS_RUN", "SYNTHESIZED_FROM_THE_FAILURE",
        "REWRITE_FAMILIES", "RECORDED_LEARNED_REPAIR")
MAX_CANDIDATES = 60
CANON = "n{}"


def judged(root: pathlib.Path, name: str, patched: str, verify_timeout: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        where = pathlib.Path(tmp)
        info = gen.build_task(root, name, where)
        (where / "python_programs" / f"{name}.py").write_text(patched)
        return gen.verify_with_corpus_test(where, info["test_path"], verify_timeout)


def _function_name(source: str) -> str:
    tree = ast.parse(source)
    return next(n.name for n in tree.body if isinstance(n, ast.FunctionDef))


# --------------------------------------------------------------------------------------------------
# α-invariance: the principle, and the only addition this file makes to the kernel
# --------------------------------------------------------------------------------------------------

def _bound_names(function: ast.AST) -> list[str]:
    """Names the function itself introduces, in first-appearance order.

    Only these may be renamed. A global, an imported module, or a builtin is FREE: renaming it would
    change which computation the program denotes, so it stays literal and no invariance is claimed
    over it.
    """
    ordered: list[str] = []
    seen: set[str] = set()

    def note(identifier: str) -> None:
        if identifier and identifier not in seen:
            seen.add(identifier)
            ordered.append(identifier)

    for node in ast.walk(function):
        if isinstance(node, ast.arg):
            note(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            note(node.id)
        elif isinstance(node, ast.FunctionDef) and node is not function:
            note(node.name)
        elif isinstance(node, ast.Lambda):
            for argument in node.args.args:
                note(argument.arg)
    return ordered


def alpha_canonical(source: str) -> tuple[str, dict[str, str]]:
    """Canonicalize a program's bound names. Returns (canonical source, canonical -> original)."""
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    bound = _bound_names(function)
    forward = {name: CANON.format(index) for index, name in enumerate(bound)}
    forward[function.name] = "f"
    reverse = {new: old for old, new in forward.items()}

    def rename(node: ast.AST) -> None:
        for inner in ast.walk(node):
            if isinstance(inner, ast.Name) and inner.id in forward:
                inner.id = forward[inner.id]
            elif isinstance(inner, ast.arg) and inner.arg in forward:
                inner.arg = forward[inner.arg]
            elif isinstance(inner, ast.FunctionDef) and inner.name in forward:
                inner.name = forward[inner.name]

    rename(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n", reverse


def alpha_restore(canonical: str, reverse: dict[str, str]) -> str | None:
    """Map a canonical program back to the target's real names. Exact, or nothing."""
    try:
        tree = ast.parse(canonical)
    except SyntaxError:
        return None
    for inner in ast.walk(tree):
        if isinstance(inner, ast.Name) and inner.id in reverse:
            inner.id = reverse[inner.id]
        elif isinstance(inner, ast.arg) and inner.arg in reverse:
            inner.arg = reverse[inner.arg]
        elif isinstance(inner, ast.FunctionDef) and inner.name in reverse:
            inner.name = reverse[inner.name]
    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree) + "\n"
    except (SyntaxError, ValueError):
        return None


# --------------------------------------------------------------------------------------------------
# the basis, folded over the demonstrations accumulated so far
# --------------------------------------------------------------------------------------------------

def fold(demonstrations: Sequence[tuple[str, str, str]]) -> dict[str, Any]:
    """Templates from verified (name, defective, repaired) demonstrations. Empty in, empty out."""
    if not demonstrations:
        return {"node": [], "leaf": []}
    out: dict[str, Any] = {"node": [], "leaf": []}
    try:
        out["node"] = basis.induce_node_templates(demonstrations, context_depth=1)
    except Exception:  # noqa: BLE001
        out["node"] = []
    try:
        out["leaf"] = basis.induce_templates(demonstrations, context_depth=1)
    except Exception:  # noqa: BLE001
        out["leaf"] = []
    return out


def propose(source: str, vocabulary: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            out += basis.candidates_from_node_templates(source, vocabulary["node"],
                                                        max_candidates=MAX_CANDIDATES)
        except Exception:  # noqa: BLE001
            pass
        try:
            out += basis.candidates_from_templates(source, vocabulary["leaf"],
                                                   max_candidates=MAX_CANDIDATES)
        except Exception:  # noqa: BLE001
            pass
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in out:
        if candidate["source_sha256"] in seen:
            continue
        seen.add(candidate["source_sha256"])
        unique.append(candidate)
    return unique


def try_vocabulary(root: pathlib.Path, name: str, *, function: str, examples: Sequence[Any],
                   proposals: Sequence[dict[str, Any]], per_example_timeout: float,
                   verify_timeout: int) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Score then judge. Returns (accounting, the accepted candidate or None)."""
    accounting = {"candidates": len(proposals), "survived_examples": 0, "judged": 0,
                  "fired_template_ids": sorted({p["template_id"] for p in proposals})}
    for proposal in proposals:
        try:
            # a candidate that trips a SyntaxWarning is still a candidate; the oracle decides, and
            # the warning is noise about a program that is about to be refused for the real reason
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                score = gen.score(proposal["source"], function, examples, per_example_timeout)
            if score != len(examples):
                continue
        except Exception:  # noqa: BLE001
            continue
        accounting["survived_examples"] += 1
        accounting["judged"] += 1
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                verdict = judged(root, name, proposal["source"], verify_timeout)
        except Exception:  # noqa: BLE001
            verdict = {"returncode": 1}
        if verdict["returncode"] == 0:
            return accounting, proposal
    return accounting, None


def measures_one(root: pathlib.Path, name: str, *, raw: dict[str, Any], canon: dict[str, Any],
                 reverse: dict[str, str], canonical_source: str, prior_stage: str | None,
                 budget_s: float, per_example_timeout: float, verify_timeout: int,
                 recorded: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    row: dict[str, Any] = {"task": name, "kind": "task", "arms_tried": [], "arms_rejected": 0}
    source = (root / "python_programs" / f"{name}.py").read_text()
    examples = gen.examples_of(root, name)
    row["examples"] = len(examples)
    row["prior_run_stage"] = prior_stage
    if not gen._install_alarm():
        row["stage"] = "UNMEASURABLE__NO_TIMER"
        return row
    try:
        function = _function_name(source)
    except StopIteration:
        # a module with no top-level function is not a bug this corpus can express, and calling it an
        # instrument error would hide a real "cannot measure" behind a crash
        row["stage"] = "NO_FUNCTION"
        row["seconds"] = round(time.time() - started, 1)
        return row

    # ---- arm 0: α-invariant templates learned earlier in THIS run
    row["arms_tried"].append("ALPHA_LEARNED_THIS_RUN")
    alpha_proposals: list[dict[str, Any]] = []
    if examples:
        for proposal in propose(canonical_source, canon):
            restored = alpha_restore(proposal["source"], reverse)
            if restored is None:
                continue
            alpha_proposals.append({**proposal, "source": restored,
                                    "source_sha256": hashlib.sha256(restored.encode()).hexdigest()})
    alpha_accounting, won = try_vocabulary(root, name, function=function, examples=examples,
                                           proposals=alpha_proposals,
                                           per_example_timeout=per_example_timeout,
                                           verify_timeout=verify_timeout)
    alpha_accounting["templates"] = len(canon.get("node") or []) + len(canon.get("leaf") or [])
    row["alpha_learned"] = alpha_accounting
    if won is not None:
        row.update(stage="REPAIRED", winner="ALPHA_LEARNED_THIS_RUN",
                   already_repaired_by_the_three_arms=(prior_stage == "REPAIRED"),
                   learned_template=won["template"], patched=won["source"],
                   seconds=round(time.time() - started, 1))
        return row
    row["arms_rejected"] += alpha_accounting["judged"]

    # ---- arm 1: the same kernel, literal preconditions (control)
    row["arms_tried"].append("LEARNED_THIS_RUN")
    raw_accounting, won = try_vocabulary(root, name, function=function, examples=examples,
                                         proposals=propose(source, raw) if examples else [],
                                         per_example_timeout=per_example_timeout,
                                         verify_timeout=verify_timeout)
    raw_accounting["templates"] = len(raw.get("node") or []) + len(raw.get("leaf") or [])
    row["learned_literal"] = raw_accounting
    if won is not None:
        row.update(stage="REPAIRED", winner="LEARNED_THIS_RUN",
                   already_repaired_by_the_three_arms=(prior_stage == "REPAIRED"),
                   learned_template=won["template"], patched=won["source"],
                   seconds=round(time.time() - started, 1))
        return row
    row["arms_rejected"] += raw_accounting["judged"]

    # ---- arm 2: synthesized from the failure (no vocabulary at all)
    if examples:
        try:
            found = synth.synthesize_return(source, function, examples, per_example_timeout, depth=3)
        except Exception:  # noqa: BLE001
            found = {"status": "ARM_ERROR"}
        row["arms_tried"].append("SYNTHESIZED_FROM_THE_FAILURE")
        if found.get("status") == "FOUND":
            for expression in found.get("expressions", []):
                patched = synth.install_return(source, function, expression)
                if patched is None:
                    continue
                if gen.score(patched, function, examples, per_example_timeout) != len(examples):
                    continue
                verdict = judged(root, name, patched, verify_timeout)
                if verdict["returncode"] == 0:
                    row.update(stage="REPAIRED", winner="SYNTHESIZED_FROM_THE_FAILURE",
                               expression=expression, patched=patched,
                               seconds=round(time.time() - started, 1))
                    return row
                row["arms_rejected"] += 1

    # ---- arm 3: the grammar-closed rewrite families
    row["arms_tried"].append("REWRITE_FAMILIES")
    families = gen.repair_task(root, name, budget_s=budget_s,
                               per_example_timeout=per_example_timeout,
                               verify_timeout=verify_timeout)
    if families.get("stage") == "REPAIRED__CORPUS_TEST_PASSES":
        row.update(stage="REPAIRED", winner="REWRITE_FAMILIES",
                   candidates_tested=families.get("candidates_tested"),
                   edit=families.get("edit"), patched=families.get("patched"),
                   seconds=round(time.time() - started, 1))
        return row

    # ---- arm 4: the recorded learned kind, replayed (kept so this pass is a superset of the merged one)
    if recorded.get("repaired") and recorded.get("lines"):
        row["arms_tried"].append("RECORDED_LEARNED_REPAIR")
        patched, why = replay.apply_lines(source, recorded["lines"])
        if patched is not None:
            verdict = judged(root, name, patched, verify_timeout)
            if verdict["returncode"] == 0:
                row.update(stage="REPAIRED", winner="RECORDED_LEARNED_REPAIR", replay=why,
                           patched=patched, seconds=round(time.time() - started, 1))
                return row
            row["arms_rejected"] += 1
        else:
            row["recorded_arm"] = why

    row["stage"] = families.get("stage", "NOT_REPAIRED")
    row["seconds"] = round(time.time() - started, 1)
    return row


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--record", required=True)
    parser.add_argument("--prior", required=True, help="COMPOSED_REPAIR_ONE_RUN receipt to compare against")
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--order", choices=("name", "reversed"), default="name")
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--budget-s", type=float, default=40.0)
    parser.add_argument("--per-example-timeout", type=float, default=0.05)
    parser.add_argument("--verify-timeout", type=int, default=120)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs)
    record = json.loads(pathlib.Path(args.record).read_text())["per_bug"]
    prior = {row["task"]: row.get("stage") for row in
             json.loads(pathlib.Path(args.prior).read_text())["rows"]}
    names = args.tasks or sorted(p.stem for p in (root / "python_programs").glob("*.py")
                                 if not p.stem.endswith("_test"))
    if args.order == "reversed":
        names = list(reversed(names))

    demonstrations: list[tuple[str, str, str]] = []
    raw = fold([])
    canon = fold([])
    rows: list[dict[str, Any]] = []
    fires: dict[str, dict[str, list[str]]] = {"alpha": {}, "literal": {}}
    started = time.time()
    with pathlib.Path(args.out).open("w") as handle:
        for name in names:
            rec = (record.get(name) or {}).get("another_benchmark") or {}
            source = (root / "python_programs" / f"{name}.py").read_text()
            try:
                canonical_source, reverse = alpha_canonical(source)
            except Exception:  # noqa: BLE001
                canonical_source, reverse = source, {}
            try:
                row = measures_one(root, name, raw=raw, canon=canon, reverse=reverse,
                                   canonical_source=canonical_source, prior_stage=prior.get(name),
                                   budget_s=args.budget_s,
                                   per_example_timeout=args.per_example_timeout,
                                   verify_timeout=args.verify_timeout, recorded=rec)
            except Exception as error:  # noqa: BLE001
                row = {"task": name, "kind": "task", "stage": f"INSTRUMENT_ERROR:{type(error).__name__}"}
            for arm, key in (("alpha", "alpha_learned"), ("literal", "learned_literal")):
                for template_id in (row.get(key) or {}).get("fired_template_ids", []):
                    fires[arm].setdefault(template_id, []).append(name)
            rows.append(row)
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(f"{name:<26}{(row.get('stage') or ''):<42}{(row.get('winner') or ''):<28}"
                  f"a={len(canon.get('node') or []) + len(canon.get('leaf') or []):<4}"
                  f"cand={(row.get('alpha_learned') or {}).get('candidates', 0):<4}"
                  f"{row.get('seconds', '?')}s", flush=True)
            # only a repair the corpus's own judge accepted becomes a lesson
            if row.get("stage") == "REPAIRED" and row.get("patched"):
                repaired = row["patched"]
                demonstrations.append((name, source, repaired))
                raw = fold(demonstrations)
                canon = fold([(n, alpha_canonical(d)[0], alpha_canonical(r)[0])
                              for n, d, r in demonstrations])

    repaired = [r for r in rows if r.get("stage") == "REPAIRED"]
    by_arm: dict[str, list[str]] = {}
    for row in repaired:
        by_arm.setdefault(row["winner"], []).append(row["task"])
    node_templates = (canon.get("node") or [])
    leaf_templates = (canon.get("leaf") or [])
    receipt = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "network_calls_at_run_time": 0,
        "arms_in_order": list(ARMS),
        "learning_is_causal_in_this_run": True,
        "learning_source": ("(defective, repaired) pairs whose patched program the corpus's own pytest "
                            "accepted, taken only from tasks earlier in this pass"),
        "alpha_invariance": ("bound names (parameters, assignment targets, nested defs and lambdas) are "
                             "canonicalized to n0, n1, ... before induction and matching; globals, "
                             "imports and builtins stay literal because they are free"),
        "order": args.order,
        "tasks": len(rows),
        "repaired": len(repaired),
        "by_arm": {k: sorted(v) for k, v in sorted(by_arm.items())},
        "stages": _tally(row.get("stage") for row in rows),
        "vocabulary": {
            "demonstrations_learned_from": len(demonstrations),
            "alpha_templates": len(list(node_templates) + list(leaf_templates)),
            "alpha_templates_relational": sum(1 for t in list(node_templates)
                                             if getattr(t, "kind", "") == "RELATIONAL"),
            "templates_with_support_ge_2": sum(1 for t in list(node_templates) + list(leaf_templates)
                                               if getattr(t, "support", 0) >= 2),
            "alpha_templates_that_fired": len(fires["alpha"]),
            "literal_templates_that_fired": len(fires["literal"]),
            "fires_alpha": {k: sorted(v) for k, v in sorted(fires["alpha"].items())},
            "fires_literal": {k: sorted(v) for k, v in sorted(fires["literal"].items())},
        },
        "learned_arms": {arm: _account(rows, key) for arm, key in
                         (("ALPHA_LEARNED_THIS_RUN", "alpha_learned"),
                          ("LEARNED_THIS_RUN", "learned_literal"))},
        "prior_run_stages": _tally(prior.get(row["task"]) for row in rows),
        "seconds": round(time.time() - started, 1),
        "rows": rows,
    }
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=1, default=str) + "\n")
    print(json.dumps({k: receipt[k] for k in ("tasks", "repaired", "by_arm", "stages", "vocabulary",
                                              "learned_arms", "seconds")}, indent=1, default=str))
    return 0


def _account(rows: Sequence[dict[str, Any]], key: str) -> dict[str, Any]:
    def total(field: str) -> int:
        return sum((row.get(key) or {}).get(field, 0) or 0 for row in rows)

    return {"tasks_where_it_proposed": sum(1 for row in rows if (row.get(key) or {}).get("candidates")),
            "candidates_proposed": total("candidates"),
            "survived_the_programs_own_examples": total("survived_examples"),
            "judged": total("judged"),
            "won": sorted(row["task"] for row in rows if row.get("winner") == _winning_arm(key)),
            "wins_over_bugs_the_three_arms_could_not_repair": sorted(
                row["task"] for row in rows if row.get("winner") == _winning_arm(key)
                and not row.get("already_repaired_by_the_three_arms"))}


def _winning_arm(key: str) -> str:
    return {"alpha_learned": "ALPHA_LEARNED_THIS_RUN", "learned_literal": "LEARNED_THIS_RUN"}[key]


def _tally(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items()))


if __name__ == "__main__":
    raise SystemExit(main())
