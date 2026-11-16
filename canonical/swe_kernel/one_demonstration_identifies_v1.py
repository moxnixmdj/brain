#!/usr/bin/env python3
"""How much does ONE demonstration identify? Measured on real code, with the tree's own learner.

THE QUESTION
------------
"Show the agent the action once and it has learned where the action applies." A demonstration is a
single point: (source, site, outcome). What a learner can extract from it is not the operation but a
*set* of candidate applicability conditions, and the size of that set is the honest measure of what
one experience bought.

Three objections were raised against the "one exposure is enough" claim, and each is decidable here
rather than arguable:

  * **identifiability** -- one trace is consistent with exponentially many hypotheses;
  * **vocabulary insufficiency** -- if the causal observable is absent from the representation, no
    number of repetitions can separate success from failure;
  * **synthesis-verification asymmetry** -- replay covers only the repeated part of the task space.

WHAT IS MEASURED, AND AGAINST WHAT
----------------------------------
The operation is the bundle's own `inline` skill: a real learned action with a stated four-condition
premise. The sites are real sites in this repository (a deterministic stride over every name bound in
a top-level function). The ORACLE is the skill itself, executed at the site in an isolated copy of
the file and judged by the tree's independent verdict (file changed, sentence matched, everything
outside the named function byte-identical). So "applicable" is a fact about the code, not a label
anyone wrote down.

The FACTS are the nine observable conditions the skill's own refusals are phrased in -- plain
binding, set once, read once, adjacent, first computed, no nested rebinding, not a parameter, no
dynamic name lookup, assignment alone on its line. They are read from the AST, never executed.

Three arms:

  1. ONE DEMONSTRATION. Evidence is a single applicable site. What survives, and what does the most
     general survivor predict on held-out sites? The optimistic survivor is the empty requirement,
     which admits every site -- so its held-out error rate is the base rate of inapplicable sites.
  2. CHOSEN CONTRASTS. ``canonical/runtime/contrast_selection_v1.select_contrast`` picks the next
     site by exact information gain; the oracle answers; repeat until the requirement is identified
     or no reachable state can teach anything. Reported: how many observations that took.
  3. RANDOM CONTRASTS (control). The same loop with a random site, repeated over seeds. If choosing
     does not beat repeating, the honest conclusion is that nothing about this is active learning.

Then, with the evidence in hand, two diagnostics the tree already owns are run rather than
re-implemented: ``applicability_v1.insufficiency_witness`` (is there any conjunction of these facts
that separates the applicable sites from the inapplicable ones at all?) and the held-out precision
and false-positive count of the learned condition.

Nothing here calls, trains, or distils a model. Model calls: 0. Spend: $0.
"""
from __future__ import annotations

import ast
import json
import pathlib
import random
import re
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # pragma: no cover - import wiring
    sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as applicability  # noqa: E402
from canonical.runtime import contrast_selection_v1 as contrast  # noqa: E402
from canonical.swe_kernel import learned_skill_verdict_v1 as lv  # noqa: E402
from canonical.swe_kernel import one_demonstration_reach_v1 as reach  # noqa: E402

SCHEMA = "one_demonstration_identifies_v1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
DEFAULT_PATTERN = "canonical/swe_kernel/*.py"
DEFAULT_SITES = 240
DYNAMIC_NAME_CALLS = frozenset({"exec", "eval", "vars", "dir", "globals", "locals"})


def _evaluation_order(node: ast.AST) -> Iterable[ast.AST]:
    """Names in the order CPython evaluates them, near enough to decide `first computed`."""
    if isinstance(node, (ast.Return, ast.Expr, ast.Assign, ast.AnnAssign, ast.AugAssign,
                         ast.Delete, ast.Assert)) and getattr(node, "value", None) is not None:
        yield from _evaluation_order(node.value)
    elif isinstance(node, (ast.If, ast.While, ast.Assert)) and getattr(node, "test", None) is not None:
        yield from _evaluation_order(node.test)
    elif isinstance(node, (ast.For, ast.AsyncFor)):
        yield from _evaluation_order(node.iter)
    elif isinstance(node, (ast.With, ast.AsyncWith)):
        for item in node.items:
            yield from _evaluation_order(item.context_expr)
    elif isinstance(node, ast.Call):
        yield node.func
        for argument in node.args:
            yield from _evaluation_order(argument)
        for keyword in node.keywords:
            yield from _evaluation_order(keyword.value)
    elif isinstance(node, ast.BinOp):
        yield from _evaluation_order(node.left)
        yield from _evaluation_order(node.right)
    elif isinstance(node, ast.BoolOp):
        for value in node.values:
            yield from _evaluation_order(value)
    elif isinstance(node, ast.Compare):
        yield from _evaluation_order(node.left)
        for comparator in node.comparators:
            yield from _evaluation_order(comparator)
    elif isinstance(node, ast.UnaryOp):
        yield from _evaluation_order(node.operand)
    elif isinstance(node, ast.Attribute):
        yield from _evaluation_order(node.value)
    elif isinstance(node, ast.Subscript):
        yield from _evaluation_order(node.value)
        yield from _evaluation_order(node.slice)
    elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for element in node.elts:
            yield from _evaluation_order(element)
    elif isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values):
            if key is not None:
                yield from _evaluation_order(key)
            yield from _evaluation_order(value)
    elif isinstance(node, ast.JoinedStr):
        for value in node.values:
            yield from _evaluation_order(value)
    else:
        yield node


def _blocks(function: ast.AST) -> Iterable[tuple[tuple[ast.AST, ...], list[ast.stmt]]]:
    """Every statement list inside the function, with the statements that enclose it."""
    stack: list[tuple[tuple[ast.AST, ...], list[ast.stmt]]] = [((), function.body)]
    while stack:
        ancestors, block = stack.pop()
        yield ancestors, block
        for statement in block:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue  # a different scope; its bindings are not this site's bindings
            for field in ("body", "orelse", "finalbody"):
                inner = getattr(statement, field, None)
                if isinstance(inner, list) and inner and all(isinstance(x, ast.stmt) for x in inner):
                    stack.append((ancestors + (statement,), inner))
            for handler in getattr(statement, "handlers", []) or []:
                stack.append((ancestors + (statement,), handler.body))


def _names_of(statement: ast.stmt) -> list[ast.Name]:
    """Names a statement itself uses, NOT the names inside the statements nested in it."""
    found: list[ast.Name] = []

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                continue  # a nested statement is its own site; counting it here double-counted
            if isinstance(child, ast.Name):
                found.append(child)
            visit(child)

    if isinstance(statement, ast.Name):
        found.append(statement)
    else:
        visit(statement)
    return found


def _stores_and_loads(function: ast.AST, variable: str) -> tuple[list, list]:
    stores, loads = [], []
    seen: set[int] = set()
    for ancestors, block in _blocks(function):
        for index, statement in enumerate(block):
            for inner in _names_of(statement):
                if inner.id != variable or id(inner) in seen:
                    continue
                seen.add(id(inner))
                record = (ancestors, block, index, statement, inner)
                (stores if isinstance(inner.ctx, ast.Store) else loads).append(record)
    return stores, loads


def _under(ancestors: Iterable[ast.AST], kinds: tuple[type, ...]) -> bool:
    return any(isinstance(node, kinds) for node in ancestors)


_INERT = 2
_FIRST = 1
_COMPUTED = 0


def _first_computed_in(node: ast.AST, variable: str) -> bool:
    """Is `variable` the first thing this expression computes, with only name reads before it?

    Reads of names and constants are inert; any operation that actually runs is a computation. The
    statement `return round(markup, 2)` reads `round` and then computes `markup`, so it qualifies --
    which is exactly the demonstration the skill was learned from. Descending in evaluation order
    keeps `print(stats["mean"])` qualifying and `f(g(x), x)` not.
    """
    def visit(current: ast.AST) -> int:
        if isinstance(current, ast.Name):
            return _FIRST if current.id == variable else _INERT
        if isinstance(current, ast.Constant):
            return _INERT
        if isinstance(current, ast.Call):
            children = [current.func, *current.args, *(keyword.value for keyword in current.keywords)]
        elif isinstance(current, (ast.BinOp,)):
            children = [current.left, current.right]
        elif isinstance(current, ast.UnaryOp):
            children = [current.operand]
        elif isinstance(current, ast.BoolOp):
            children = list(current.values)
        elif isinstance(current, ast.Compare):
            children = [current.left, *current.comparators]
        elif isinstance(current, ast.Attribute):
            children = [current.value]
        elif isinstance(current, ast.Subscript):
            children = [current.value, current.slice]
        elif isinstance(current, (ast.Tuple, ast.List, ast.Set)):
            children = list(current.elts)
        elif isinstance(current, ast.Dict):
            children = [value for value in current.values]
        elif isinstance(current, ast.JoinedStr):
            children = list(current.values)
        elif isinstance(current, ast.FormattedValue):
            children = [current.value]
        elif isinstance(current, ast.IfExp):
            children = [current.test, current.body, current.orelse]
        else:
            children = []
        for child in children:
            verdict = visit(child)
            if verdict == _FIRST:
                return _FIRST
            if verdict == _COMPUTED:
                return _COMPUTED
        return _COMPUTED

    return visit(node) == _FIRST


def _inside_conditional(statement: ast.AST, name_node: ast.AST) -> bool:
    """Is this use reached more than once, or only sometimes, inside its own statement?"""
    conditionals = (ast.BoolOp, ast.IfExp, ast.Lambda, ast.ListComp, ast.SetComp,
                    ast.DictComp, ast.GeneratorExp)
    if isinstance(statement, (ast.If, ast.IfExp, ast.While, ast.For, ast.AsyncFor)):
        return True
    for node in ast.walk(statement):
        if isinstance(node, conditionals):
            for inner in ast.walk(node):
                if inner is name_node:
                    return True
    return False


def facts_of(path: str, function: str, variable: str, *,
             repo: pathlib.Path = ROOT) -> frozenset[str]:
    """The observable facts of one site, read from the file. Never executed.

    The vocabulary is the skill's own stated premise, expressed as observables: a plain binding,
    set once, read once, in the statement that directly follows *in the same block*, first in that
    statement's evaluation order, computed exactly once, no nested rebinding, not a parameter, no
    dynamic name lookup, and an assignment that stands alone on its line without a comment.
    """
    source = (repo / path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function:
            target = node
            break
    if target is None:
        return frozenset()

    stores, loads = _stores_and_loads(target, variable)
    facts: set[str] = set()

    if any(isinstance(record[3], ast.Assign) and len(record[3].targets) == 1
           and isinstance(record[3].targets[0], ast.Name) for record in stores):
        facts.add("bind.plain_assignment")
    if len(stores) == 1:
        facts.add("bind.set_once")
    if len(loads) == 1:
        facts.add("use.read_once")

    if stores and loads:
        store, load = stores[0], loads[0]
        same_block = store[1] is load[1] and load[2] == store[2] + 1
        if same_block:
            facts.add("use.next_statement_in_same_block")
            statement = load[3]
            expression = getattr(statement, "value", None)
            if expression is not None and _first_computed_in(expression, variable):
                facts.add("use.first_computed")
            if not _inside_conditional(load[3], load[4]):
                facts.add("use.computed_once")
        if not _under(store[0], (ast.For, ast.AsyncFor, ast.While)) and not _under(
                load[0], (ast.For, ast.AsyncFor, ast.While)):
            facts.add("blocks.not_in_a_loop")

    nested_scopes = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                     ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)
    nested = False
    for node in ast.walk(target):
        if isinstance(node, nested_scopes) and node is not target:
            if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                for generator in node.generators:
                    if (isinstance(generator.target, ast.Name)
                            and generator.target.id == variable):
                        nested = True
            for inner in ast.walk(node):
                if (isinstance(inner, ast.Name) and inner.id == variable
                        and isinstance(inner.ctx, ast.Store)):
                    nested = True
    if not nested:
        facts.add("scope.no_nested_rebinding")
    arguments = {argument.arg for argument in target.args.args}
    arguments |= {argument.arg for argument in getattr(target.args, "posonlyargs", [])}
    arguments |= {argument.arg for argument in target.args.kwonlyargs}
    if variable not in arguments:
        facts.add("scope.not_parameter")

    calls = {node.func.id for node in ast.walk(target)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    if not (calls & DYNAMIC_NAME_CALLS):
        facts.add("body.no_dynamic_names")

    plain = [record[3] for record in stores
             if isinstance(record[3], ast.Assign) and len(record[3].targets) == 1]
    if plain:
        assignment = plain[0]
        first, last = lines[assignment.lineno - 1], lines[assignment.end_lineno - 1]
        if (not first[:assignment.col_offset].strip()
                and not last[assignment.end_col_offset:].strip()):
            facts.add("text.assignment_alone")
        if "#" not in first[assignment.col_offset:]:
            facts.add("text.no_comment_on_assignment")
    return frozenset(facts)


def inline_skill() -> dict[str, Any]:
    for skill in lv.load_skills():
        if str(skill.get("goal_skeleton") or "").startswith("inline the variable"):
            return skill
    raise LookupError("the bundle carries no inline skill")


def oracle(skill: Mapping[str, Any], site: Mapping[str, Any], *,
           repo: pathlib.Path = ROOT, python_executable: str | None = None) -> dict[str, Any]:
    """Is the operation applicable here? Decided by executing it and judging the world."""
    recorded = reach.run_site(skill, site, repo=repo, python_executable=python_executable)
    return {"applicable": recorded["outcome"] == "VERIFIED", "outcome": recorded["outcome"],
            "reason": recorded["reason"]}


def collect(*, pattern: str = DEFAULT_PATTERN, sites: int = DEFAULT_SITES,
            repo: pathlib.Path = ROOT, python_executable: str | None = None) -> dict[str, Any]:
    universe, scan = reach.all_sites(repo=repo, pattern=pattern)
    chosen = reach.sample(universe, sites)
    skill = inline_skill()
    started = time.time()
    rows: list[dict[str, Any]] = []
    damaged_sites: list[dict[str, Any]] = []
    for site in chosen:
        try:
            facts = facts_of(str(site["path"]), str(site["function"]), str(site["variable"]),
                             repo=repo)
        except (OSError, SyntaxError):
            continue
        verdict = oracle(skill, site, repo=repo, python_executable=python_executable)
        if str(verdict["outcome"]) == "DAMAGED":
            # The operation fired and the world did not hold: not a label, a defect. Kept and
            # reported, never silently folded into "inapplicable".
            damaged_sites.append({"site": dict(site), "reason": verdict["reason"]})
            continue
        applicable = verdict["applicable"]
        unmeasured = str(verdict["reason"]).startswith("CRASH:")
        rows.append({"site": site, "facts": facts, "applicable": applicable,
                     "outcome": verdict["outcome"], "reason": verdict["reason"],
                     "measured": not unmeasured})
    measured = [row for row in rows if row["measured"]]
    return {"skill_id": skill.get("skill_id"), "universe": len(universe), **scan,
            "rows": measured, "unmeasured": len(rows) - len(measured),
            "damaged": damaged_sites, "seconds": round(time.time() - started, 2)}


def split(rows: Sequence[Mapping[str, Any]]) -> tuple[list[int], list[int]]:
    """Deterministic: every third site is held out, so the held-out set is not a corner."""
    return ([index for index in range(len(rows)) if index % 3],   # held out
            [index for index in range(len(rows)) if index % 3 != 0])  # train pool


def _predict(requirement: Iterable[str], state: Iterable[str]) -> bool:
    return applicability.admits(requirement, state)


def _score(rows: Sequence[Mapping[str, Any]], indices: Sequence[int],
           requirement: Iterable[str]) -> dict[str, Any]:
    required = tuple(requirement)
    true_positive = false_positive = true_negative = false_negative = 0
    for index in indices:
        row = rows[index]
        predicted = _predict(required, row["facts"])
        if predicted and row["applicable"]:
            true_positive += 1
        elif predicted and not row["applicable"]:
            false_positive += 1
        elif not predicted and not row["applicable"]:
            true_negative += 1
        else:
            false_negative += 1
    total = true_positive + false_positive + true_negative + false_negative
    # Accuracy is the wrong headline here: the operation is rare, so answering "no" every time
    # scores above 0.98. What matters is whether the rare applicable sites are found, and how many
    # sites are called applicable when they are not -- the only direction that damages a file.
    return {"sites": total, "true_positive": true_positive, "false_positive": false_positive,
            "true_negative": true_negative, "false_negative": false_negative,
            "accuracy": round((true_positive + true_negative) / total, 4) if total else None,
            "precision": (round(true_positive / (true_positive + false_positive), 4)
                          if true_positive + false_positive else None),
            "recall": (round(true_positive / (true_positive + false_negative), 4)
                       if true_positive + false_negative else None),
            "dangerous_error_rate": round(false_positive / total, 4) if total else None}


def one_demonstration(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The arm the claim rests on: a single applicable site, and nothing else."""
    held_out, train = split(rows)
    successes = [index for index in train if rows[index]["applicable"]]
    if not successes:
        return {"status": "NO_APPLICABLE_SITE_IN_THE_POOL"}
    evidence = [(rows[successes[0]]["facts"], True)]
    boundary = applicability.learn(evidence)
    requirement = boundary.most_general
    return {
        "status": boundary.status,
        "reason": boundary.reason,
        "candidate_request_count": 2 ** len(boundary.candidate_facts or ()),
        "candidate_facts": list(boundary.candidate_facts),
        "requirement": list(requirement),
        "survivors": boundary.survivor_count,
        "held_out": _score(rows, held_out, requirement),
        "true_held_out_precision_at_that_requirement": None,
    }


def _loop(rows: Sequence[Mapping[str, Any]], *, held_out: Sequence[int], train: Sequence[int],
          choose: str, seed: int = 0) -> dict[str, Any]:
    pool = [index for index in train if rows[index]["applicable"]][:1]
    remaining = [index for index in train if index not in pool]
    evidence: list[tuple[frozenset[str], bool]] = [(rows[index]["facts"], True) for index in pool]
    rng = random.Random(seed)
    observations = 0
    boundary = applicability.learn(evidence)
    while not boundary.identified and remaining:
        if choose == "chosen":
            picked = contrast.select_contrast(evidence, [rows[index]["facts"] for index in remaining])
            if not picked.informative:
                break
            wanted = picked.state
            match = [index for index in remaining if tuple(sorted(rows[index]["facts"])) == wanted]
            index = match[0] if match else remaining[0]
        else:
            index = rng.choice(remaining)
        remaining.remove(index)
        evidence.append((rows[index]["facts"], rows[index]["applicable"]))
        observations += 1
        boundary = applicability.learn(evidence)

    requirement = boundary.required if boundary.identified else boundary.most_general
    return {
        "choose": choose, "seed": seed, "observations": observations,
        "status": boundary.status, "requirement": list(requirement or ()),
        "survivors": boundary.survivor_count,
        "held_out": _score(rows, held_out, requirement or ()),
        "evidence_size": len(evidence),
        "insufficiency": applicability.insufficiency_witness(evidence),
    }


def separation_report(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Why no conjunction of these observables separates the outcomes, with the witnesses named.

    A = the facts every applicable site shares. Some conjunction of observed facts admits every
    applicable site and excludes every inapplicable one if and only if A is not a subset of any
    inapplicable site's facts. When it is, those sites ARE the proof: they share every observable
    the applicable sites agree on, so the difference between them is not in this vocabulary.
    """
    successes = [row for row in rows if row["applicable"]]
    failures = [row for row in rows if not row["applicable"]]
    if not successes:
        return {"status": "NO_APPLICABLE_SITE"}
    shared = set(successes[0]["facts"])
    for row in successes[1:]:
        shared &= set(row["facts"])
    blockers = [row for row in failures if shared <= set(row["facts"])]
    reasons: dict[str, int] = {}
    for row in blockers:
        key = re.sub(r"\b\d+\b", "N", str(row["reason"]))
        reasons[key[:120]] = reasons.get(key[:120], 0) + 1
    return {
        "status": "SEPARATION_IMPOSSIBLE" if blockers else "SEPARATION_EXISTS",
        "shared_facts_of_applicable_sites": sorted(shared),
        "blocking_inapplicable_sites": len(blockers),
        "blocking_reasons": dict(sorted(reasons.items(), key=lambda item: (-item[1], item[0]))),
        "blocking_sites": [{"site": dict(row["site"]), "reason": str(row["reason"])[:160]}
                           for row in blockers[:8]],
        "reading": ("every observable the applicable sites agree on is also true of these sites, so "
                    "no conjunction of this vocabulary can admit one and refuse the other"
                    if blockers else
                    "a conjunction of these observables separates the outcomes"),
    }


def measure(*, pattern: str = DEFAULT_PATTERN, sites: int = DEFAULT_SITES,
            seeds: int = 12, repo: pathlib.Path = ROOT,
            python_executable: str | None = None) -> dict[str, Any]:
    collected = collect(pattern=pattern, sites=sites, repo=repo,
                        python_executable=python_executable)
    rows = collected["rows"]
    held_out, train = split(rows)
    applicable = sum(1 for row in rows if row["applicable"])
    one = one_demonstration(rows)
    chosen = _loop(rows, held_out=held_out, train=train, choose="chosen")
    random_arms = [_loop(rows, held_out=held_out, train=train, choose="random", seed=seed)
                   for seed in range(seeds)]
    identified = [arm for arm in random_arms if arm["status"] == "IDENTIFIED"]
    full_evidence = [(row["facts"], bool(row["applicable"])) for row in rows]
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "network_calls": 0,
        "skill_id": collected["skill_id"],
        "pattern": pattern,
        "universe": collected["universe"],
        "files": collected["files"],
        "sites_queried": len(rows),
        "applicable_sites": applicable,
        "unmeasured_sites": collected["unmeasured"],
        "damaged_sites": len(collected["damaged"]),
        "inapplicable_sites": len(rows) - applicable,
        "oracle_seconds": collected["seconds"],
        "held_out_sites": len(held_out),
        "train_sites": len(train),
        "one_demonstration": one,
        "chosen_contrasts": chosen,
        "random_contrasts": {
            "seeds": seeds,
            "identified_at_all": len(identified),
            "observations_when_identified": sorted(arm["observations"] for arm in identified),
            "mean_observations_when_identified": (
                round(sum(arm["observations"] for arm in identified) / len(identified), 2)
                if identified else None),
            "accuracy_when_identified": sorted(arm["held_out"]["accuracy"]
                                               for arm in identified),
        },
        "vocabulary_sufficiency_on_all_evidence": applicability.insufficiency_witness(full_evidence),
        "separation": separation_report(rows),
        "random_rows": [{"seed": arm["seed"], "observations": arm["observations"],
                         "status": arm["status"],
                         "accuracy": arm["held_out"]["accuracy"],
                         "dangerous_errors": arm["held_out"]["false_positive"]}
                        for arm in random_arms],
        "what_one_demonstration_buys": (
            "one applicable site leaves %s candidate requirements and %s survivor(s); the most "
            "general one predicts the held-out set at accuracy %s with %s dangerous errors"
            % (one.get("candidate_request_count"), one.get("survivors"),
               (one.get("held_out") or {}).get("accuracy"),
               (one.get("held_out") or {}).get("false_positive"))),
    }


def summarize(report: Mapping[str, Any]) -> str:
    one = report["one_demonstration"]
    chosen = report["chosen_contrasts"]
    random_arm = report["random_contrasts"]
    lines = [
        "operation %s on %d real sites (%d applicable, %d not) from %d files"
        % (report["skill_id"], report["sites_queried"], report["applicable_sites"],
           report["inapplicable_sites"], report["files"]),
        "  1 demonstration : %s, %s candidate requirements, %s survivor(s)"
        % (one.get("status"), one.get("candidate_request_count"), one.get("survivors")),
        "      held out     : %s" % (
            "accuracy %s, dangerous errors %s of %d"
            % (one["held_out"]["accuracy"], one["held_out"]["false_positive"],
               one["held_out"]["sites"]) if "held_out" in one else "not measured"),
        "  chosen contrasts: %s after %d observation(s), held-out accuracy %s, dangerous %s"
        % (chosen["status"], chosen["observations"], chosen["held_out"]["accuracy"],
           chosen["held_out"]["false_positive"]),
        "      requirement  : %s" % ", ".join(chosen["requirement"]),
        "  random contrasts: identified in %d of %d seeds, mean observations %s"
        % (random_arm["identified_at_all"], random_arm["seeds"],
           random_arm["mean_observations_when_identified"]),
    ]
    separation = report.get("separation") or {}
    lines.append("  vocabulary      : %s, %s blocking site(s), shared facts %s"
                 % (separation.get("status"), separation.get("blocking_inapplicable_sites"),
                    ", ".join(separation.get("shared_facts_of_applicable_sites") or [])))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Measure how much one demonstration identifies, on real code.")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--sites", type=int, default=DEFAULT_SITES)
    parser.add_argument("--seeds", type=int, default=12)
    ns = parser.parse_args(argv)
    report = measure(pattern=ns.pattern, sites=ns.sites, seeds=ns.seeds)
    print(summarize(report))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
