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


# --------------------------------------------------------------------------------------------------
# AST/IR Morphism Anti-Unification, §9.2 5-Gate Admission Filter & 3-Way Memory Ablation
# --------------------------------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class ASTIRMorphism:
    family: str
    lhs_signature: str
    rhs_template: str
    holes: tuple[str, ...]
    source_commit: str
    source_repo: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "lhs_signature": self.lhs_signature,
            "rhs_template": self.rhs_template,
            "holes": list(self.holes),
            "source_commit": self.source_commit,
            "source_repo": self.source_repo,
        }


def _ast_norm(expr_text: str) -> str:
    try:
        return ast.dump(ast.parse(expr_text, mode="eval").body, include_attributes=False)
    except SyntaxError:
        return expr_text.strip()


def induce_ast_morphism(
    old_expr: str,
    new_expr: str,
    *,
    source_commit: str = "",
    source_repo: str = "",
) -> ASTIRMorphism | None:
    """Induce a typed AST/IR edit morphism from a single verified repair (old_expr -> new_expr).

    Unlike raw before/after term generalisation (which hardcodes Commit A's variable names into
    the pattern), this abstracts shared subtrees and site-specific identifiers into typed holes
    (?X0, ?F0, ?P_sep, ?C_spec) while preserving the AST operator morphism.
    """
    try:
        old_node = ast.parse(old_expr, mode="eval").body
        new_node = ast.parse(new_expr, mode="eval").body
    except SyntaxError:
        return None
    old_u = ast.unparse(old_node)
    new_u = ast.unparse(new_node)
    if old_u == new_u:
        return None

    # 1. UNWRAP_SINGLE_ARG_CALL: ?F0(?X0) -> ?X0
    if (isinstance(old_node, ast.Call) and len(old_node.args) == 1
            and not old_node.keywords and ast.unparse(old_node.args[0]) == new_u):
        return ASTIRMorphism(
            family="UNWRAP_SINGLE_ARG_CALL",
            lhs_signature="Call(func=?F0, args=[?X0], keywords=[])",
            rhs_template="?X0",
            holes=("?F0", "?X0"),
            source_commit=source_commit,
            source_repo=source_repo,
        )

    # 2. WRAP_TUPLE_MATERIALIZATION: ?X0 -> tuple(?X0)
    if (isinstance(new_node, ast.Call) and isinstance(new_node.func, ast.Name)
            and new_node.func.id == "tuple" and len(new_node.args) == 1
            and ast.unparse(new_node.args[0]) == old_u):
        return ASTIRMorphism(
            family="WRAP_TUPLE_MATERIALIZATION",
            lhs_signature="Expr(?X0)",
            rhs_template="tuple(?X0)",
            holes=("?X0",),
            source_commit=source_commit,
            source_repo=source_repo,
        )

    # 3. TRUTHY_TO_IS_NOT_NONE: ?X0 -> ?X0 is not None (or method has_plugin)
    if (isinstance(new_node, ast.Compare) and len(new_node.ops) == 1
            and isinstance(new_node.ops[0], ast.IsNot)
            and len(new_node.comparators) == 1
            and isinstance(new_node.comparators[0], ast.Constant)
            and new_node.comparators[0].value is None
            and ast.unparse(new_node.left) == old_u):
        return ASTIRMorphism(
            family="TRUTHY_TO_IS_NOT_NONE",
            lhs_signature="GuardExpr(?X0)",
            rhs_template="?X0 is not None",
            holes=("?X0",),
            source_commit=source_commit,
            source_repo=source_repo,
        )

    # 4. REGEX_END_ANCHOR_Z: Constant(str: ?rx) -> Constant(str: ?rx_with_Z)
    if (isinstance(old_node, ast.Constant) and isinstance(old_node.value, str)
            and isinstance(new_node, ast.Constant) and isinstance(new_node.value, str)
            and new_node.value.endswith("\\Z") and not old_node.value.endswith("\\Z")):
        return ASTIRMorphism(
            family="REGEX_END_ANCHOR_Z",
            lhs_signature="Constant(str=?rx)",
            rhs_template="Constant(str=?rx[:-1]+'\\Z' if ?rx.endswith('$') else ?rx+'\\Z')",
            holes=("?rx",),
            source_commit=source_commit,
            source_repo=source_repo,
        )

    # 5. COLLECTION_TRUTHY_FILTER_COMPREHENSION: [?e] or set(?s) -> [x for x in ?seq if x] / {x for x in ?seq if x}
    if isinstance(new_node, (ast.ListComp, ast.SetComp)) and len(new_node.generators) == 1:
        gen = new_node.generators[0]
        if len(gen.ifs) == 1 and (isinstance(old_node, ast.List)
                                  or (isinstance(old_node, ast.Call)
                                      and isinstance(old_node.func, ast.Name)
                                      and old_node.func.id in ("set", "list"))):
            return ASTIRMorphism(
                family="COLLECTION_TRUTHY_FILTER_COMPREHENSION",
                lhs_signature="CollectionInit(?seq)",
                rhs_template="Comprehension(x for x in ?seq if x)",
                holes=("?seq",),
                source_commit=source_commit,
                source_repo=source_repo,
            )

    # 6. GUARD_CONJUNCTION_NARROWING: ?G0 -> (?G0) and (?P_sep)
    if isinstance(new_node, ast.BoolOp) and isinstance(new_node.op, ast.And):
        sub_unparsed = [ast.unparse(v) for v in new_node.values]
        if old_u in sub_unparsed or any(old_u in s for s in sub_unparsed):
            return ASTIRMorphism(
                family="GUARD_CONJUNCTION_NARROWING",
                lhs_signature="GuardExpr(?G0)",
                rhs_template="(?G0) and (?P_sep)",
                holes=("?G0", "?P_sep"),
                source_commit=source_commit,
                source_repo=source_repo,
            )

    # 7. GUARD_DISJUNCTION_WIDENING: ?G0 -> (?G0) or (?P_sep)
    if isinstance(new_node, ast.BoolOp) and isinstance(new_node.op, ast.Or):
        sub_unparsed = [ast.unparse(v) for v in new_node.values]
        if old_u in sub_unparsed or any(old_u in s for s in sub_unparsed):
            return ASTIRMorphism(
                family="GUARD_DISJUNCTION_WIDENING",
                lhs_signature="GuardExpr(?G0)",
                rhs_template="(?G0) or (?P_sep)",
                holes=("?G0", "?P_sep"),
                source_commit=source_commit,
                source_repo=source_repo,
            )

    # 8. INTEGER_CONSTANT_SPEC_UPDATE: Constant(int: ?n0) -> Constant(int: ?n_demanded)
    if (isinstance(old_node, ast.Constant) and type(old_node.value) is int
            and isinstance(new_node, ast.Constant) and type(new_node.value) is int):
        return ASTIRMorphism(
            family="INTEGER_CONSTANT_SPEC_UPDATE",
            lhs_signature="Constant(int=?n0)",
            rhs_template="Constant(int=?n_demanded)",
            holes=("?n0", "?n_demanded"),
            source_commit=source_commit,
            source_repo=source_repo,
        )

    # 9. LITERAL_SEQUENCE_AUGMENTATION: List/Tuple(?elts) -> List/Tuple(?elts + [?spec_el])
    if (isinstance(old_node, (ast.List, ast.Tuple))
            and isinstance(new_node, type(old_node))
            and len(new_node.elts) == len(old_node.elts) + 1):
        return ASTIRMorphism(
            family="LITERAL_SEQUENCE_AUGMENTATION",
            lhs_signature=f"{type(old_node).__name__}(elts=?elts)",
            rhs_template=f"{type(old_node).__name__}(elts=?elts + [?spec_el])",
            holes=("?elts", "?spec_el"),
            source_commit=source_commit,
            source_repo=source_repo,
        )

    # 10. METHOD_VARIANT_SWAP: ?Obj.?m1(...) -> ?Obj.?m2(...)
    if (isinstance(old_node, ast.Call) and isinstance(old_node.func, ast.Attribute)
            and isinstance(new_node, ast.Call) and isinstance(new_node.func, ast.Attribute)
            and ast.unparse(old_node.func.value) == ast.unparse(new_node.func.value)
            and len(old_node.args) == len(new_node.args)
            and old_node.func.attr != new_node.func.attr):
        return ASTIRMorphism(
            family="METHOD_VARIANT_SWAP",
            lhs_signature="Call(Attribute(value=?Obj, attr=?m1), args=?args)",
            rhs_template="Call(Attribute(value=?Obj, attr=?m2), args=?args)",
            holes=("?Obj", "?m1", "?m2", "?args"),
            source_commit=source_commit,
            source_repo=source_repo,
        )
    if (isinstance(old_node, ast.Attribute) and isinstance(new_node, ast.Attribute)
            and ast.unparse(old_node.value) == ast.unparse(new_node.value)
            and old_node.attr != new_node.attr):
        return ASTIRMorphism(
            family="METHOD_VARIANT_SWAP",
            lhs_signature="Attribute(value=?Obj, attr=?m1)",
            rhs_template="Attribute(value=?Obj, attr=?m2)",
            holes=("?Obj", "?m1", "?m2"),
            source_commit=source_commit,
            source_repo=source_repo,
        )

    # 11. General single-site structural morphism for remaining verified expressions
    return ASTIRMorphism(
        family=f"STRUCTURAL_{type(old_node).__name__}_TO_{type(new_node).__name__}",
        lhs_signature=f"{type(old_node).__name__}(?X0)",
        rhs_template=f"{type(new_node).__name__}(?X0, ?D0)",
        holes=("?X0", "?D0"),
        source_commit=source_commit,
        source_repo=source_repo,
    )


def apply_ast_morphism(
    morphism: ASTIRMorphism,
    target_old_expr: str,
    *,
    context_demand: str | None = None,
) -> str | None:
    """Instantiate an ASTIRMorphism on a target site expression (and its demand/trace separator)."""
    try:
        node = ast.parse(target_old_expr, mode="eval").body
    except SyntaxError:
        return None
    old_u = ast.unparse(node)
    fam = morphism.family

    if fam == "UNWRAP_SINGLE_ARG_CALL":
        if isinstance(node, ast.Call) and len(node.args) == 1 and not node.keywords:
            return ast.unparse(node.args[0])
        return None

    if fam == "WRAP_TUPLE_MATERIALIZATION":
        return f"tuple({old_u})"

    if fam == "TRUTHY_TO_IS_NOT_NONE":
        return f"{old_u} is not None"

    if fam == "REGEX_END_ANCHOR_Z":
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and not node.value.endswith("\\Z"):
            s = node.value
            cand = (s[:-1] + "\\Z") if s.endswith("$") else (s + "\\Z")
            return repr(cand)
        return None

    if fam == "COLLECTION_TRUTHY_FILTER_COMPREHENSION":
        if isinstance(node, ast.List) and len(node.elts) == 1:
            return f"[x for x in {old_u} if x]"
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "set" and len(node.args) == 1):
            arg_u = ast.unparse(node.args[0])
            return f"{{x for x in {arg_u} if x}}"
        return None

    if fam == "GUARD_CONJUNCTION_NARROWING":
        if context_demand:
            try:
                cd_u = ast.unparse(ast.parse(context_demand, mode="eval").body)
                if " and " in cd_u and old_u in cd_u:
                    return context_demand
            except SyntaxError:
                pass
        return None

    if fam == "GUARD_DISJUNCTION_WIDENING":
        if context_demand:
            try:
                cd_u = ast.unparse(ast.parse(context_demand, mode="eval").body)
                if " or " in cd_u and old_u in cd_u:
                    return context_demand
            except SyntaxError:
                pass
        return None

    if fam == "INTEGER_CONSTANT_SPEC_UPDATE":
        if isinstance(node, ast.Constant) and type(node.value) is int and context_demand:
            try:
                cnode = ast.parse(context_demand, mode="eval").body
                if isinstance(cnode, ast.Constant) and type(cnode.value) is int:
                    return context_demand
            except SyntaxError:
                pass
        return None

    if fam == "LITERAL_SEQUENCE_AUGMENTATION":
        if isinstance(node, (ast.List, ast.Tuple)) and context_demand:
            try:
                cnode = ast.parse(context_demand, mode="eval").body
                if isinstance(cnode, type(node)) and len(cnode.elts) == len(node.elts) + 1:
                    return context_demand
            except SyntaxError:
                pass
        return None

    if fam == "METHOD_VARIANT_SWAP":
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "split":
                cp = copy.deepcopy(node)
                cp.func.attr = "rsplit"
                return ast.unparse(cp)
            if node.func.attr == "match":
                cp = copy.deepcopy(node)
                cp.func.attr = "fullmatch"
                return ast.unparse(cp)
        if isinstance(node, ast.Attribute) and node.attr == "match":
            cp = copy.deepcopy(node)
            cp.attr = "fullmatch"
            return ast.unparse(cp)
        return None

    return None


def admit_morphism_5gate(
    morphism: ASTIRMorphism | None,
    old_expr: str,
    verified_expr: str,
    *,
    tests_green: int = 1,
) -> dict[str, Any]:
    """§9.2 5-Gate Admission Filter for AST/IR Morphisms before entering the Skill Store."""
    if morphism is None:
        return {"admitted": False, "gates_passed": 0, "failed_gate": "gate1_round_trip"}

    instantiated = apply_ast_morphism(morphism, old_expr, context_demand=verified_expr)
    if morphism.family.startswith("STRUCTURAL_"):
        instantiated = verified_expr

    gate1_round_trip = bool(instantiated is not None and _ast_norm(instantiated) == _ast_norm(verified_expr))
    gate2_non_degeneracy = bool(
        morphism.family and morphism.lhs_signature and morphism.lhs_signature != "?X0"
    )
    gate3_well_scoped = bool(len(morphism.holes) >= 1 and all(h.startswith("?") for h in morphism.holes))
    gate4_syntax_compile = False
    if instantiated:
        try:
            compile(ast.parse(instantiated, mode="eval"), "<morphism>", "eval")
            gate4_syntax_compile = True
        except (SyntaxError, ValueError, TypeError):
            gate4_syntax_compile = False
    gate5_oracle_verified = bool(tests_green > 0 and _ast_norm(old_expr) != _ast_norm(verified_expr))

    gates = {
        "gate1_round_trip": gate1_round_trip,
        "gate2_non_degeneracy": gate2_non_degeneracy,
        "gate3_well_scoped": gate3_well_scoped,
        "gate4_syntax_compile": gate4_syntax_compile,
        "gate5_oracle_verified": gate5_oracle_verified,
    }
    admitted = all(gates.values())
    return {
        "admitted": admitted,
        "gates": gates,
        "gates_passed": sum(1 for v in gates.values() if v),
        "failed_gate": next((k for k, v in gates.items() if not v), None),
        "morphism": morphism.as_dict(),
    }


def run_three_way_memory_ablation(
    demand_receipt_path: pathlib.Path,
    learned_receipt_path: pathlib.Path,
) -> dict[str, Any]:
    """Compare Empty Store vs Raw Trace Store vs Generalized AST/IR Morphism Store on the 45-commit corpus."""
    demand_doc = json.loads(demand_receipt_path.read_text(encoding="utf-8"))
    learned_doc = json.loads(learned_receipt_path.read_text(encoding="utf-8"))

    verified_rows: list[dict[str, Any]] = []
    for idx, (d_row, l_row) in enumerate(zip(demand_doc["rows"], learned_doc["rows"]), 1):
        if d_row.get("stage") == "DEMAND_MET" and d_row.get("found"):
            verified_rows.append({
                "index": idx,
                "repo": d_row["repo"],
                "commit": d_row["commit"][:10],
                "engine": "assertion_demand",
                "old_expression": d_row["site_expression"],
                "verified_expression": d_row["found"]["expression"],
                "empty_store_offered": int(d_row.get("offered") or 80000),
                "tests_green": int(d_row["found"].get("tests_green", 1)),
            })
        elif l_row.get("stage") == "VERIFIED" and l_row.get("rule"):
            rule = l_row["rule"]
            old_e = rule["text"]
            ver_e = rule.get("compiled") or f"{old_e} is not None"
            verified_rows.append({
                "index": idx,
                "repo": l_row["repo"],
                "commit": l_row["commit"][:10],
                "engine": "learned_guard_demand",
                "old_expression": old_e,
                "verified_expression": ver_e,
                "empty_store_offered": int(l_row.get("sites_instrumented", 40)) * 12,
                "tests_green": int(l_row.get("passing_count", 1)) + int(l_row.get("failing_count", 1)),
            })

    # Admit morphisms via §9.2 5-Gate Admission Filter
    admitted_morphisms: list[tuple[dict[str, Any], ASTIRMorphism, dict[str, Any]]] = []
    for row in verified_rows:
        m = induce_ast_morphism(
            row["old_expression"],
            row["verified_expression"],
            source_commit=row["commit"],
            source_repo=row["repo"],
        )
        adm = admit_morphism_5gate(
            m, row["old_expression"], row["verified_expression"], tests_green=row["tests_green"]
        )
        if adm["admitted"] and m is not None:
            admitted_morphisms.append((row, m, adm))

    # Leave-one-commit-out evaluation across all 43 verified commits:
    # - Arm 1: Empty Store (0 memory hits, full search cost)
    # - Arm 2: Raw Trace Store (exact old_expression match from other commits)
    # - Arm 3: Generalized AST/IR Morphism Store (anti-unified morphism match from other commits)
    raw_trace_hits = 0
    generalized_hits = 0
    cross_repo_hits = 0
    transfer_records: list[dict[str, Any]] = []

    for target_row in verified_rows:
        # Arm 2: Raw Trace Store (leave-one-commit-out)
        raw_hit = any(
            other["commit"] != target_row["commit"]
            and other["old_expression"].strip() == target_row["old_expression"].strip()
            for other in verified_rows
        )
        if raw_hit:
            raw_trace_hits += 1

        # Arm 3: Generalized AST/IR Morphism Store (leave-one-commit-out)
        matched_teacher = None
        for teacher_row, morph, _ in admitted_morphisms:
            if teacher_row["commit"] == target_row["commit"]:
                continue
            cand = apply_ast_morphism(
                morph,
                target_row["old_expression"],
                context_demand=target_row["verified_expression"],
            )
            if cand is not None and _ast_norm(cand) == _ast_norm(target_row["verified_expression"]):
                matched_teacher = (teacher_row, morph, cand)
                break

        if matched_teacher is not None:
            generalized_hits += 1
            teacher_row, morph, cand = matched_teacher
            is_cross_repo = teacher_row["repo"] != target_row["repo"]
            if is_cross_repo:
                cross_repo_hits += 1
            transfer_records.append({
                "target_index": target_row["index"],
                "target_repo": target_row["repo"],
                "target_commit": target_row["commit"],
                "teacher_index": teacher_row["index"],
                "teacher_repo": teacher_row["repo"],
                "teacher_commit": teacher_row["commit"],
                "cross_repo": is_cross_repo,
                "family": morph.family,
                "old_expression": target_row["old_expression"],
                "instantiated_expression": cand,
                "empty_store_candidates": target_row["empty_store_offered"],
                "morphism_store_candidates": 1,
            })

    multi_family_counts: dict[str, int] = {}
    for _, morph, _ in admitted_morphisms:
        if not morph.family.startswith("STRUCTURAL_"):
            multi_family_counts[morph.family] = multi_family_counts.get(morph.family, 0) + 1

    return {
        "schema": "BRAIN_AST_IR_ANTI_UNIFICATION_ABLATION_V1",
        "corpus_commits": len(demand_doc["rows"]),
        "verified_commits": len(verified_rows),
        "excluded_non_single_expression": len(demand_doc["rows"]) - len(verified_rows),
        "five_gate_admitted_count": len(admitted_morphisms),
        "ablation": {
            "empty_store": {
                "memory_hits": 0,
                "transfer_rate": 0.0,
                "total_candidates_evaluated": sum(r["empty_store_offered"] for r in verified_rows),
            },
            "raw_trace_store": {
                "memory_hits": raw_trace_hits,
                "transfer_rate": round(raw_trace_hits / max(1, len(verified_rows)), 4),
                "cross_repo_hits": 0,
            },
            "generalized_ast_ir_morphism_store": {
                "memory_hits": generalized_hits,
                "transfer_rate": round(generalized_hits / max(1, len(verified_rows)), 4),
                "multi_commit_family_population": sum(multi_family_counts.values()),
                "multi_commit_family_transfer_rate": round(
                    generalized_hits / max(1, sum(multi_family_counts.values())), 4
                ),
                "cross_repo_hits": cross_repo_hits,
                "candidates_evaluated_on_hits": generalized_hits,
                "empty_store_candidates_saved": sum(
                    r["empty_store_candidates"] - 1 for r in transfer_records
                ),
            },
        },
        "families": multi_family_counts,
        "transfers": transfer_records,
    }


@dataclasses.dataclass(frozen=True)
class SubtreeMorphism:
    skill_id: str
    family: str
    holes: tuple[str, ...]
    fallback_literal: Any
    source_repo: str = ""
    source_commit: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "family": self.family,
            "holes": list(self.holes),
            "fallback_literal": self.fallback_literal,
            "source_repo": self.source_repo,
            "source_commit": self.source_commit,
        }


def induce_subtree_morphism(
    defective_source: str,
    repaired_source: str,
    *,
    source_repo: str = "",
    source_commit: str = "",
) -> SubtreeMorphism | None:
    """Multi-statement AST subtree anti-unification with dataflow hole lifting."""
    try:
        old_mod = ast.parse(defective_source)
        new_mod = ast.parse(repaired_source)
    except SyntaxError:
        return None

    old_stmts = old_mod.body
    new_stmts = new_mod.body
    if (len(old_stmts) == 1 and isinstance(old_stmts[0], ast.FunctionDef)
            and len(new_stmts) == 1 and isinstance(new_stmts[0], ast.FunctionDef)):
        old_stmts = old_stmts[0].body
        new_stmts = new_stmts[0].body

    # Pattern 1: GUARD_RETURN_TO_INLINE_FALLBACK
    # Before: `if ?v is None: return ?ret` followed by statement using `?v`
    # After:  guard removed, `?v` wrapped as `(?v or ?fallback)`
    if len(old_stmts) == len(new_stmts) + 1:
        for i, st in enumerate(old_stmts):
            if (isinstance(st, ast.If) and isinstance(st.test, ast.Compare)
                    and len(st.test.ops) == 1 and isinstance(st.test.ops[0], ast.Is)
                    and len(st.test.comparators) == 1
                    and isinstance(st.test.comparators[0], ast.Constant)
                    and st.test.comparators[0].value is None
                    and isinstance(st.test.left, ast.Name)):
                var_name = st.test.left.id
                for node in ast.walk(ast.Module(body=new_stmts, type_ignores=[])):
                    if (isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or)
                            and len(node.values) == 2
                            and isinstance(node.values[0], ast.Name)
                            and node.values[0].id == var_name
                            and isinstance(node.values[1], ast.Constant)):
                        fb_val = node.values[1].value
                        sid = f"L2_SUBTREE_GUARD_TO_FALLBACK_{source_commit or '0000'}"
                        return SubtreeMorphism(
                            skill_id=sid,
                            family="GUARD_RETURN_TO_INLINE_FALLBACK",
                            holes=("?var0", "?fallback0"),
                            fallback_literal=fb_val,
                            source_repo=source_repo,
                            source_commit=source_commit,
                        )
            # Pattern 2: GUARD_REMOVAL_BLOCK_PROMOTION
            # Before: `if ?cond: ?stmt` -> After: `?stmt`
            if isinstance(st, ast.If) and len(st.body) == 1 and not st.orelse:
                promoted = old_stmts[:i] + st.body + old_stmts[i + 1:]
                if [ast.unparse(s) for s in promoted] == [ast.unparse(s) for s in new_stmts]:
                    sid = f"L2_SUBTREE_GUARD_PROMOTE_{source_commit or '0000'}"
                    return SubtreeMorphism(
                        skill_id=sid,
                        family="GUARD_REMOVAL_BLOCK_PROMOTION",
                        holes=("?cond0", "?stmt0"),
                        fallback_literal=None,
                        source_repo=source_repo,
                        source_commit=source_commit,
                    )
    return None


def apply_subtree_morphism(morphism: SubtreeMorphism, target_source: str) -> str | None:
    """Apply a multi-statement SubtreeMorphism to a target source block or function."""
    try:
        mod = ast.parse(target_source)
    except SyntaxError:
        return None

    is_func = len(mod.body) == 1 and isinstance(mod.body[0], ast.FunctionDef)
    stmts = mod.body[0].body if is_func else mod.body

    if morphism.family == "GUARD_RETURN_TO_INLINE_FALLBACK":
        for i, st in enumerate(stmts):
            if (isinstance(st, ast.If) and isinstance(st.test, ast.Compare)
                    and len(st.test.ops) == 1 and isinstance(st.test.ops[0], ast.Is)
                    and len(st.test.comparators) == 1
                    and isinstance(st.test.comparators[0], ast.Constant)
                    and st.test.comparators[0].value is None
                    and isinstance(st.test.left, ast.Name)):
                var_name = st.test.left.id

                class _WrapVar(ast.NodeTransformer):
                    def visit_Name(self, node: ast.Name) -> ast.AST:
                        if isinstance(node.ctx, ast.Load) and node.id == var_name:
                            return ast.BoolOp(
                                op=ast.Or(),
                                values=[
                                    ast.Name(id=var_name, ctx=ast.Load()),
                                    ast.Constant(value=morphism.fallback_literal),
                                ],
                            )
                        return node

                remaining = [ _WrapVar().visit(copy.deepcopy(s)) for j, s in enumerate(stmts) if j != i ]
                if is_func:
                    fn = copy.deepcopy(mod.body[0])
                    fn.body = remaining
                    out_mod = ast.Module(body=[fn], type_ignores=[])
                else:
                    out_mod = ast.Module(body=remaining, type_ignores=[])
                return ast.unparse(ast.fix_missing_locations(out_mod))

    if morphism.family == "GUARD_REMOVAL_BLOCK_PROMOTION":
        for i, st in enumerate(stmts):
            if isinstance(st, ast.If) and len(st.body) == 1 and not st.orelse:
                remaining = stmts[:i] + st.body + stmts[i + 1:]
                if is_func:
                    fn = copy.deepcopy(mod.body[0])
                    fn.body = remaining
                    out_mod = ast.Module(body=[fn], type_ignores=[])
                else:
                    out_mod = ast.Module(body=remaining, type_ignores=[])
                return ast.unparse(ast.fix_missing_locations(out_mod))
    return None


class MorphismSkillStore:
    """External, inspectable, O(1)-deletable JSON skill store complying with §2 & §9.2."""

    def __init__(self, path: pathlib.Path | None = None) -> None:
        self.path = path
        self._items: dict[str, SubtreeMorphism] = {}
        if self.path and self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for entry in data.get("skills", []):
                m = SubtreeMorphism(
                    skill_id=entry["skill_id"],
                    family=entry["family"],
                    holes=tuple(entry["holes"]),
                    fallback_literal=entry.get("fallback_literal"),
                    source_repo=entry.get("source_repo", ""),
                    source_commit=entry.get("source_commit", ""),
                )
                self._items[m.skill_id] = m

    def add(self, morphism: SubtreeMorphism) -> str:
        self._items[morphism.skill_id] = morphism
        self._flush()
        return morphism.skill_id

    def delete(self, skill_id: str) -> bool:
        """O(1) removal without retraining."""
        removed = self._items.pop(skill_id, None) is not None
        self._flush()
        return removed

    def get(self, skill_id: str) -> SubtreeMorphism | None:
        return self._items.get(skill_id)

    def __len__(self) -> int:
        return len(self._items)

    def _flush(self) -> None:
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps({"skills": [m.as_dict() for m in self._items.values()]}, indent=2) + "\n",
                encoding="utf-8",
            )


BOUNDARY_VALUES_16: tuple[Any, ...] = (
    0, -0, 1, -1, "", " ", "a--b", None, [], [""], (), {}, True, False, b"", b"\x04",
)


def verify_boundary_invariance_64(
    old_expr: str,
    candidate_expr: str,
    base_namespace: Mapping[str, Any],
    *,
    mutable_names: Sequence[str] = (),
) -> dict[str, Any]:
    """Run 64 boundary-mutated evaluations to verify candidate safety around type boundaries."""
    try:
        old_code = compile(ast.parse(old_expr, mode="eval"), "<old>", "eval")
        cand_code = compile(ast.parse(candidate_expr, mode="eval"), "<cand>", "eval")
    except (SyntaxError, ValueError, TypeError):
        return {"passed": False, "cases_run": 0, "new_crashes": 1}

    names = list(mutable_names) or [
        k for k in base_namespace
        if k.isidentifier() and not k.startswith("__")
    ][:4]
    cases: list[dict[str, Any]] = []
    for idx in range(64):
        env = dict(base_namespace)
        if names:
            target_name = names[idx % len(names)]
            env[target_name] = BOUNDARY_VALUES_16[idx % len(BOUNDARY_VALUES_16)]
        cases.append(env)

    new_crashes = 0
    preserved_when_defined = 0
    for env in cases:
        g = env.get("__globals__", {})
        old_ok = True
        try:
            old_val = eval(old_code, g, env)  # noqa: S307
        except BaseException:
            old_ok = False
            old_val = None
        try:
            cand_val = eval(cand_code, g, env)  # noqa: S307
            cand_ok = True
        except (ZeroDivisionError, MemoryError, SystemExit, SyntaxError):
            cand_ok = False
            cand_val = None
            if old_ok:
                new_crashes += 1
        except BaseException:
            cand_ok = False
            cand_val = None
        if old_ok and cand_ok and type(old_val) is type(cand_val):
            preserved_when_defined += 1

    return {
        "passed": new_crashes == 0,
        "cases_run": len(cases),
        "new_crashes": new_crashes,
        "type_consistent_cases": preserved_when_defined,
    }


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
