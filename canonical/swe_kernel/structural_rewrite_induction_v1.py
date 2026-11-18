"""Shape rules learned from real diffs, by anti-unification -- and whether they compose.

ROUND 9'S RESULT, AND WHY IT POINTS HERE
----------------------------------------
Round 9 measured edit synthesis on real fix commits and got 0 of 6, with an exact decomposition: two tasks
needed a COMPOSITE edit (the commit's own edit was in the grammar, fired, and was still not enough), two were
NOT_EXPRESSIBLE because the commit changed the SHAPE of an expression, and two had no firing site. Zero of the
six failures were search failures.

`induced_edit_basis_v1` already names what it throws away when it sees those diffs: `SUBTREE_REWRITE`,
`STATEMENT_INSERT`, `STATEMENT_DELETE` -- reported as NON_EXECUTABLE and discarded. So the raw material for a
shape grammar is already being collected and already being dropped.

That is the same lesson rounds 7 and 8 produced twice: do not invent the space, read it out of the
environment. Here the space is *rewrites*, and the environment's own commits are the only place they are
written down. So this file learns rewrites from real diffs by **anti-unification** (least general
generalisation): two subtrees are folded into one pattern with metavariables where they disagree, and a
replacement that refers to the same metavariables. One algorithm, no operator list, no model.

WHAT A LEARNED RULE LOOKS LIKE
------------------------------
    pattern      `result -= $v0`            (hole at the identifier)
    replacement  `result += $v0`
A pattern matches a site when its structure matches and every hole binds consistently; the replacement is then
instantiated with those bindings. Because the pattern came from a real diff, it fires at least at the site it
came from -- which is precisely the failure mode BIGBAG reports for agent-written AST rules (72 of its 86
non-fixes were "the matching pattern is incorrect / found no call sites", arXiv 2606.24446, Jun 2026).

COMPOSITION
-----------
Two of round 9's tasks needed more than one edit. A single-rewrite grammar cannot represent a multi-node commit
by construction, so the search here is over **sequences of up to two rewrites**, executed, never assumed.

WHAT IS REFUSED, BY NAME
------------------------
    REFUSED__NO_RULE_FIRES            no learned rule's pattern matches anywhere in the file
    REFUSED__STATEMENT_INSERT_DELETE  the diff adds or removes a statement: NOT modelled here, counted and named
    REFUSED__TEST_WOULD_NOT_RUN       the integrity gate failed, so the task is not a task
    REFUSED__SOURCE_FILE_ABSENT       the task names a file the parent tree does not have

MEASURED
--------
The same real commits as round 9, but without round 9's truncation bug (its corpus was capped at 40 commits per
repository; the gate passes 89). Every task's test must FAIL at the parent and PASS at the commit. The
round-9 template grammar is re-run on the identical sample as the A/B, so this is a comparison, not a claim.

Reuses: `history_induced_edit_grammar_v1` (execution, restore-on-finally, run_test), `induced_edit_basis_v1`
(diff alignment). Authority NONE -- sandbox measurement, not independent verification. No model. $0.
"""

from __future__ import annotations

import ast
import copy
import dataclasses
import difflib
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402

SCHEMA = "BRAIN_STRUCTURAL_REWRITE_INDUCTION_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
DEPTH1_BUDGET = 20
DEPTH2_SEEDS = 3
DEPTH2_PER_SEED = 8
SAMPLE = 24

SOLVED = "SOLVED"
SOLVED_COMPOSITE = "SOLVED_BY_TWO_REWRITES"
NOT_FOUND = "GRAMMAR_FIRES_NEVER_SOLVES"
REFUSED_NO_RULE = "REFUSED__NO_RULE_FIRES"
REFUSED_INSERT = "REFUSED__STATEMENT_INSERT_DELETE"
REFUSED_NO_RUN = "REFUSED__TEST_WOULD_NOT_RUN"
REFUSED_NO_SOURCE = "REFUSED__SOURCE_FILE_ABSENT"


# --------------------------------------------------------------------------------------------------
# terms: an AST <-> tuple encoding, so patterns and holes are data rather than syntax
# --------------------------------------------------------------------------------------------------

def encode(node: Any) -> Any:
    """AST -> tuple term. Leaves stay raw; a differing leaf becomes a hole at generalisation time."""
    if isinstance(node, ast.AST):
        return (type(node).__name__,) + tuple(encode(getattr(node, field, None)) for field in node._fields)
    if isinstance(node, list):
        return ("__list__",) + tuple(encode(item) for item in node)
    return node


def decode(term: Any) -> Any:
    """Tuple term -> AST. Holes must already be substituted."""
    if not isinstance(term, tuple) or not term:
        return term
    head = term[0]
    if head == "__list__":
        return [decode(item) for item in term[1:]]
    if not isinstance(head, str) or not hasattr(ast, head):
        return tuple(decode(item) for item in term)
    cls = getattr(ast, head)
    if not (isinstance(cls, type) and issubclass(cls, ast.AST)):
        return tuple(decode(item) for item in term)
    node = cls()
    for field, value in zip(cls._fields, term[1:]):
        setattr(node, field, decode(value))
    return ast.fix_missing_locations(node)


def _is_hole(term: Any) -> bool:
    return isinstance(term, tuple) and len(term) == 2 and term[0] == "?"


def _hole(index: int) -> tuple:
    return ("?", index)


def _hole_for(holes: list[dict[str, Any]], kind: str, left: Any, right: Any) -> tuple:
    index = next((position for position, hole in enumerate(holes)
                  if hole["kind"] == kind and hole["left"] == left and hole["right"] == right), None)
    if index is None:
        holes.append({"kind": kind, "left": left, "right": right})
        index = len(holes) - 1
    return _hole(index)


def generalise(left: Any, right: Any, holes: list[dict[str, Any]], depth: int = 0) -> Any:
    """Anti-unify `left` (defective) with `right` (repaired): one pattern, holes where they disagree.

    Three agreement rules make this a generalisation rather than a coincidence:
      * a node's own head stays literal; when two nodes differ in TYPE the whole node becomes one subtree
        hole, so a hole never stands where a class name belongs (that mistake made every reconstruction
        unparseable -- found by this round's own tests);
      * a one-element tuple is an atom (an operator, a context): it becomes one atom hole when it differs;
      * identical disagreements share ONE hole, so a pattern meaning "the same name twice" cannot match two
        different names.
    """
    if type(left) is not type(right):
        return _hole_for(holes, "subtree", left, right)
    if isinstance(left, tuple):
        if len(left) != len(right):
            return _hole_for(holes, "subtree", left, right)
        if len(left) == 0:
            return left
        if len(left) == 1:
            return left if left == right else _hole_for(holes, "atom", left, right)
        if left[0] != right[0]:
            return _hole_for(holes, "subtree", left, right)
        return (left[0],) + tuple(generalise(a_item, b_item, holes, depth + 1)
                                  for a_item, b_item in zip(left[1:], right[1:]))
    if left != right:
        return _hole_for(holes, "leaf", left, right)
    return left


def substitute(term: Any, bindings: Mapping[int, Any]) -> Any:
    if _is_hole(term):
        return bindings.get(term[1], term)
    if isinstance(term, tuple):
        return tuple(substitute(item, bindings) for item in term)
    return term


@dataclasses.dataclass(frozen=True)
class Rule:
    pattern: Any
    replacement: Any
    learners: tuple[str, ...] = ()
    support: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {"pattern": repr(self.pattern)[:300], "replacement": repr(self.replacement)[:300],
                "learners": list(self.learners), "support": self.support}


def _key(rule: Rule) -> str:
    return json.dumps([repr(rule.pattern), repr(rule.replacement)], default=str)


# --------------------------------------------------------------------------------------------------
# induction from real diffs
# --------------------------------------------------------------------------------------------------

def _statement_lists(node: ast.AST) -> list[list[ast.stmt]]:
    out: list[list[ast.stmt]] = []
    for child in ast.walk(node):
        for field in getattr(child, "_fields", ()):
            value = getattr(child, field, None)
            if isinstance(value, list) and value and all(isinstance(item, ast.stmt) for item in value):
                out.append(value)
    return out


def _text(statements: Iterable[ast.stmt]) -> list[string_t]:  # type: ignore[valid-type]
    return [ast.unparse(statement) for statement in statements]


def insert_delete_present(defective: str, repaired: str) -> bool:
    """True when the diff changes WHICH statements exist, not just how one is written."""
    try:
        old = ast.parse(defective)
        new = ast.parse(repaired)
    except SyntaxError:
        return False
    for old_list, new_list in zip(_statement_lists(old), _statement_lists(new)):
        # kinds, not text: a rewrite changes how a statement is written and must not be mistaken for an
        # insertion (which is what the first version of this function did)
        old_kinds = [type(statement).__name__ for statement in old_list]
        new_kinds = [type(statement).__name__ for statement in new_list]
        if old_kinds != new_kinds:
            return True
    return False


def _statement_pairs(old: ast.AST, new: ast.AST) -> list[tuple[ast.stmt, ast.stmt]]:
    """Align corresponding statements by their kind and order, so a shape change can be located."""
    pairs: list[tuple[ast.stmt, ast.stmt]] = []
    old_statements = [node for node in getattr(old, "body", []) if isinstance(node, ast.stmt)]
    new_statements = [node for node in getattr(new, "body", []) if isinstance(node, ast.stmt)]
    for old_statement, new_statement in zip(old_statements, new_statements):
        if type(old_statement) is type(new_statement):
            pairs.append((old_statement, new_statement))
            pairs.extend(_statement_pairs(old_statement, new_statement))
    return pairs


def _round_trips(rule: Rule, defective_statement: ast.stmt, repaired_statement: ast.stmt) -> bool:
    """A rule must reproduce the diff that taught it, exactly. Anything less is a lossy generalisation."""
    try:
        bindings = match(rule.pattern, encode(defective_statement))
        if bindings is None:
            return False
        rebuilt = decode(substitute(rule.replacement, bindings))
        return ast.unparse(ast.fix_missing_locations(rebuilt)) == ast.unparse(repaired_statement)
    except Exception:  # noqa: BLE001 - a rule that cannot be rebuilt simply never enters the grammar
        return False


def learn_rules(pairs: Iterable[tuple[str, str, str]], max_rules_per_pair: int = 24,
                require_round_trip: bool = True) -> list[Rule]:
    """Induce UPDATE rewrites from real (name, defective, repaired) source pairs.

    Statement insertions/deletions are deliberately NOT turned into rules: they are counted by
    `insert_delete_present` and refused by name at measurement time, because hiding an unmodelled shape behind
    a loose rule is how a system starts lying to itself.
    """
    learned: dict[str, Rule] = {}
    for name, defective, repaired in pairs:
        try:
            old, new = ast.parse(defective), ast.parse(repaired)
        except SyntaxError:
            continue
        made = 0
        for old_statement, new_statement in _statement_pairs(old, new):
            if made >= max_rules_per_pair:
                break
            old_term, new_term = encode(old_statement), encode(new_statement)
            if old_term == new_term:
                continue
            holes: list[dict[str, Any]] = []
            pattern = generalise(old_term, new_term, holes)
            if not holes:
                continue
            replacement = substitute(pattern, {index: hole["right"] for index, hole in enumerate(holes)})
            rule = Rule(pattern=pattern, replacement=replacement, learners=(name,), support=1)
            if require_round_trip and not _round_trips(rule, old_statement, new_statement):
                # admission gate: a rewrite that cannot reproduce its own example may never be searched
                continue
            existing = learned.get(_key(rule))
            if existing is None:
                learned[_key(rule)] = rule
            else:
                learned[_key(rule)] = dataclasses.replace(
                    existing, support=existing.support + 1,
                    learners=tuple(sorted(set(existing.learners) | {name})))
            made += 1
    return sorted(learned.values(), key=lambda rule: (-rule.support, _key(rule)))


# --------------------------------------------------------------------------------------------------
# matching
# --------------------------------------------------------------------------------------------------

def match(pattern: Any, term: Any, bindings: dict[int, Any] | None = None) -> dict[int, Any] | None:
    """Structural match with consistent hole binding. A hole binds any subtree, but only one."""
    bindings = {} if bindings is None else bindings
    if _is_hole(pattern):
        index = pattern[1]
        if index in bindings:
            return bindings if bindings[index] == term else None
        bindings[index] = term
        return bindings
    if isinstance(pattern, tuple):
        if not isinstance(term, tuple) or len(pattern) != len(term):
            return None
        for pattern_item, term_item in zip(pattern, term):
            bindings = match(pattern_item, term_item, bindings)
            if bindings is None:
                return None
        return bindings
    return bindings if pattern == term else None


def _sites_of(tree: ast.AST) -> list[tuple[list[tuple[str, int | None]], ast.AST]]:
    """Every node with a POSITIONAL path to it. Positional, not id()-based: a deepcopy gives new ids, and an
    id-based path silently matched nothing (found by this round's own run before any number was believed)."""
    out: list[tuple[list[tuple[str, int | None]], ast.AST]] = []

    def walk(node: ast.AST, steps: list[tuple[str, int | None]]) -> None:
        for field in getattr(node, "_fields", ()):
            value = getattr(node, field, None)
            if isinstance(value, ast.AST):
                out.append((steps + [(field, None)], value))
                walk(value, steps + [(field, None)])
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        out.append((steps + [(field, index)], item))
                        walk(item, steps + [(field, index)])

    walk(tree, [])
    return out


def _holder(root: ast.AST, steps: Sequence[tuple[str, int | None]]) -> tuple[Any, Any] | None:
    """Resolve a positional path to (holder, key) where the node lives."""
    holder: Any = root
    for field, index in steps:
        if not hasattr(holder, field):
            return None
        value = getattr(holder, field)
        if index is None:
            holder = value
        else:
            if not isinstance(value, list) or index >= len(value):
                return None
            holder = value[index]
    return holder, steps[-1] if steps else None


def _resolve(root: ast.AST, ids: Sequence[int]) -> ast.AST | None:
    current = root
    for target in ids:
        found = None
        for child in ast.walk(current):
            if id(child) == target:
                found = child
                break
        if found is None:
            return None
        current = found
    return current


def rewrite(source: str, rules: Sequence[Rule], cap: int = DEPTH1_BUDGET,
            rule_cap: int = 200) -> list[dict[str, Any]]:
    """Apply each (rule, site) pair that matches, returning syntactically valid candidate programs."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    sites = _sites_of(tree)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rule in list(rules)[:rule_cap]:
        for steps, node in sites:
            bindings = match(rule.pattern, encode(node))
            if bindings is None:
                continue
            replacement = decode(substitute(rule.replacement, bindings))
            if not isinstance(replacement, ast.AST):
                continue
            mutated = copy.deepcopy(tree)
            located = _holder(mutated, steps)
            if located is None:
                continue
            holder, key = located
            field, index = key if key is not None else (None, None)
            if field is None:
                continue
            value = getattr(holder, field, None)
            if index is None and isinstance(value, ast.AST):
                setattr(holder, field, replacement)
            elif isinstance(value, list) and index is not None and index < len(value):
                value[index] = replacement
            else:
                continue
            try:
                text = ast.unparse(ast.fix_missing_locations(mutated))
                compile(text, "<candidate>", "exec")  # parse() alone accepts field-shape misuse
            except (SyntaxError, ValueError, TypeError):
                continue
            if text in seen:
                continue
            seen.add(text)
            out.append({"text": text, "rule": rule.as_dict(), "support": rule.support,
                        "learners": list(rule.learners)})
            if len(out) >= cap:
                return out
    return out


# --------------------------------------------------------------------------------------------------
# measurement
# --------------------------------------------------------------------------------------------------

def prepare_corpus(manifest: pathlib.Path, hist: pathlib.Path, work: pathlib.Path,
                   limit: int | None = SAMPLE) -> list[dict[str, Any]]:
    """Rebuild the task trees from the committed manifest, so the corpus is reproducible by anyone."""
    payload = json.loads(pathlib.Path(manifest).read_text(encoding="utf-8"))
    tasks = payload["tasks"]
    if limit:
        by_repo: dict[str, list[dict[str, Any]]] = {}
        for task in tasks:
            by_repo.setdefault(task["name"], []).append(task)
        chosen: list[dict[str, Any]] = []
        per_repo = max(1, limit // max(1, len(by_repo)))
        for name, group in sorted(by_repo.items()):
            ordered = sorted(group, key=lambda task: task["sha"])
            step = max(1, len(ordered) // per_repo)
            chosen.extend(ordered[::step][:per_repo])
        tasks = chosen[:limit]
    prepared: list[dict[str, Any]] = []
    for task in tasks:
        name, sha = task["name"], task["sha"]
        repo_dir = pathlib.Path(hist) / name
        if not (repo_dir / ".git").exists():
            subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
                            f"https://github.com/{task['repo']}.git", str(repo_dir)], check=False)
        tree = pathlib.Path(work) / f"{name}-{sha[:8]}-p"
        if not tree.exists():
            tree.mkdir(parents=True, exist_ok=True)
            subprocess.run(f"git -C {repo_dir} archive {task['parent']} | tar -x -C {tree}", shell=True,
                           check=False)
            blob = subprocess.run(["git", "-C", str(repo_dir), "show", f"{sha}:{task['test']}"],
                                  capture_output=True, text=True)
            if blob.returncode == 0:
                target = tree / task["test"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(blob.stdout)
        prepared.append({**task, "parent_tree": str(tree)})
    return prepared


def solve_task(task: Mapping[str, Any], rules: Sequence[Rule],
               baseline_rules: Sequence[Any] = ()) -> dict[str, Any]:
    tree = pathlib.Path(task["parent_tree"])
    source_rel, test_rel = task["source"], task["test"]
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"], "source": source_rel, "test": test_rel}
    if not (tree / source_rel).is_file():
        return {**row, "state": REFUSED_NO_SOURCE}
    baseline = G.run_test(tree, test_rel)
    if baseline["passed"]:
        return {**row, "state": REFUSED_NO_RUN, "note": "the commit's test already passes at the parent"}
    source = (tree / source_rel).read_text(encoding="utf-8", errors="replace")
    row["insert_delete"] = insert_delete_present((tree / source_rel).read_text(encoding="utf-8"),
                                                 task.get("commit_source", source))
    first = rewrite(source, rules)
    row["depth1_candidates"] = len(first)
    row["trials"] = 0
    for entry in first:
        outcome = G.try_candidate(tree, source_rel, test_rel, entry["text"])
        row["trials"] += 1
        if outcome["passed"]:
            return {**row, "state": SOLVED, "rule": entry["rule"], "rule_support": entry["support"],
                    "taught_by": entry["learners"]}
    for seed in first[:DEPTH2_SEEDS]:
        second = rewrite(seed["text"], rules, cap=DEPTH2_PER_SEED)
        row["depth2_candidates"] = row.get("depth2_candidates", 0) + len(second)
        for entry in second:
            outcome = G.try_candidate(tree, source_rel, test_rel, entry["text"])
            row["trials"] += 1
            if outcome["passed"]:
                return {**row, "state": SOLVED_COMPOSITE, "rule": entry["rule"],
                        "first_rule": seed["rule"], "taught_by": entry["learners"]}
    row["state"] = NOT_FOUND if first else REFUSED_NO_RULE
    row["baseline_state"] = _baseline(task, tree, source, baseline_rules)
    return row


def _baseline(task: Mapping[str, Any], tree: pathlib.Path, source: str,
              baseline_rules: Sequence[Any]) -> str:
    """Round 9's template grammar on the SAME task, so the comparison is exact rather than remembered."""
    if not baseline_rules:
        return "NOT_RUN"
    candidates = G.localized_candidates(source, baseline_rules, None, cap=DEPTH1_BUDGET)
    for entry in candidates:
        if G.try_candidate(tree, task["source"], task["test"], entry["source"])["passed"]:
            return "BASELINE_SOLVES"
    return "BASELINE_FAILS" if candidates else "BASELINE_NO_FIRE"


def measure(tasks: Sequence[Mapping[str, Any]], all_pairs: Mapping[str, Sequence[tuple[str, str, str]]]) -> dict[str, Any]:
    """Leave-one-repository-out again: a task may only be solved by rules its own repository never taught."""
    rows: list[dict[str, Any]] = []
    for task in tasks:
        name = task["name"]
        teaching = [pair for other, group in all_pairs.items() if other != name for pair in group]
        rules = learn_rules(teaching)
        baseline_pairs = [pair for other, group in all_pairs.items() if other != name for pair in group]
        baseline_rules = G.induce_grammar(baseline_pairs)
        row = solve_task(task, rules, baseline_rules)
        row["rules_learned"] = len(rules)
        rows.append(row)
    return summarise(rows)


def summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    solved = states.get(SOLVED, 0) + states.get(SOLVED_COMPOSITE, 0)
    baseline = {"BASELINE_SOLVES": 0, "BASELINE_FAILS": 0, "BASELINE_NO_FIRE": 0, "NOT_RUN": 0}
    for row in rows:
        baseline[row.get("baseline_state", "NOT_RUN")] = baseline.get(row.get("baseline_state", "NOT_RUN"), 0) + 1
    return {
        "schema": SCHEMA, "rows": list(rows), "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "totals": {"tasks": len(rows), "states": states, "solved": solved,
                   "solved_fraction": round(solved / len(rows), 4) if rows else 0.0,
                   "solved_composite": states.get(SOLVED_COMPOSITE, 0),
                   "trials": sum(row.get("trials", 0) for row in rows),
                   "baseline": baseline,
                   "rules_learned": sorted({row.get("rules_learned") for row in rows})},
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    states = totals["states"]
    baseline = totals["baseline"]
    return (f"{totals['tasks']} real fix commits (test fails at the parent, passes at the commit). "
            f"Anti-unification rules learned from other repositories' diffs only: {totals['solved']} solved "
            f"({totals['solved_fraction']}), of which {totals['solved_composite']} needed two rewrites, in "
            f"{totals['trials']} executions. Round 9's template grammar on the same sample: "
            f"{baseline.get('BASELINE_SOLVES', 0)} solved. States: "
            + ", ".join(f"{state} {count}" for state, count in sorted(states.items())) + ".")


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path,
                        default=pathlib.Path("canonical/corpus/real_fix_commits_20261116_V1.json"))
    parser.add_argument("--hist", type=pathlib.Path, default=pathlib.Path("/tmp/hist"))
    parser.add_argument("--work", type=pathlib.Path, default=pathlib.Path("/tmp/histwork"))
    parser.add_argument("--json", type=pathlib.Path)
    parser.add_argument("--limit", type=int, default=SAMPLE)
    args = parser.parse_args(argv)
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    pairs: dict[str, list[tuple[str, str, str]]] = {}
    for entry in payload.get("grammar", []):
        pairs.setdefault(entry["name"], []).append(
            (entry["sha"][:8] + ":" + entry["source"], entry["defective"], entry["repaired"]))
    tasks = prepare_corpus(args.manifest, args.hist, args.work, limit=args.limit)
    for task in tasks:
        entry = next((item for item in payload.get("grammar", [])
                      if item["sha"] == task["sha"]), None)
        if entry:
            task["commit_source"] = entry["repaired"]
    report = measure(tasks, pairs)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
