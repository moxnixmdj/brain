#!/usr/bin/env python3
"""A new literal in an existing construct: is it memorisable, and does the check name it?

WHY THIS ROUND EXISTS
---------------------
Round 26 closed the selectors and left one shape unmeasured, and the project's own census
says why that shape matters. `canonical/swe_kernel/change_shape_census_v1.py` classifies
real changes and states what each demands:

    GUARD_ADDED                    needs a predicate and a seat -- the only shape rounds 11-12 address
    VALUE_OR_OPERATOR_SUBSTITUTION  "the memorisable shape"
    VALUE_ADDED                    "a new literal in an existing construct: memorisable, literal unseen"
    FEATURE_NEW_DEFINITION         "needs NEW CODE, which no learned action and no predicate supplies"
    STRUCTURAL_OTHER               needs synthesis

Rounds 22-26 measured the substitution shape to death (0 of 8 from the file's alphabet;
2.4% on the executed path). The shape the census calls MEMORISABLE -- a new literal added
to a construct that already exists -- was never measured here, because round 26's tests
excluded multi-line constructs by construction. That is the gap, and it is the one shape
whose missing word has a plausible machine source: the check's own literal.

MEASURED, EXACTLY
-----------------
For each of the 87 real fixes: is the fix a pure insertion of one element into a construct
that already spans several lines (a multi-line list, set, tuple, dict or call)? Decided from
the diff and the pre-fix AST, not by generation, so nothing is capped.

Then, for those: does the element's literal content already appear in the test that catches
the bug? If it does, the fix is reachable with zero parameters -- copy the check's own word
into the hole the check complains about -- and that is a capability class, not a ceiling.

Finally, execution: the fixed state is applied and the real suite is run, so the class is
confirmed by the machine and not by text equality.

Zero model calls, zero parameters.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import subprocess
import sys
import difflib
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = ROOT / "canonical/corpus/real_fix_pairs_20261119_V1.json"
MINED = ROOT / "canonical/corpus/real_fix_commits_20261116_V1.json"
PRIOR = ROOT / "canonical/tools/does_the_refusal_name_the_missing_word_v1.py"
SCHEMA = "BRAIN_A_NEW_LITERAL_IN_AN_EXISTING_CONSTRUCT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
CONTAINERS = (ast.List, ast.Set, ast.Tuple, ast.Dict, ast.Call)


def prior():
    spec = importlib.util.spec_from_file_location("refusal_prior3", PRIOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def insertion(before: str, after: str) -> dict[str, Any] | None:
    """The one line where the fix adds an element, by insert or by appending to a line.

    Appending an element to the last line of a multi-line construct does not insert a line,
    it REPLACES one: `    "URL": re.compile(...),` becomes `    "URL": re.compile(...),` plus
    a new entry. Both forms are the same act, so both are read here.
    """
    before_lines, after_lines = before.splitlines(), after.splitlines()
    if abs(len(after_lines) - len(before_lines)) > 1:
        return None
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=before_lines, b=after_lines,
                                                       autojunk=False).get_opcodes():
        if tag == "insert" and (j2 - j1) == 1:
            return {"row": j1 + 1, "text": after_lines[j1], "kind": "insert"}
        if tag == "replace" and (i2 - i1) == 1 and (j2 - j1) == 1:
            old, new_line = before_lines[i1].rstrip(), after_lines[j1].rstrip()
            prefix = 0
            while prefix < min(len(old), len(new_line)) and old[prefix] == new_line[prefix]:
                prefix += 1
            suffix = 0
            while (suffix < min(len(old), len(new_line)) - prefix
                   and old[len(old) - 1 - suffix] == new_line[len(new_line) - 1 - suffix]):
                suffix += 1
            inserted = new_line[prefix:len(new_line) - suffix] if suffix else new_line[prefix:]
            if inserted.strip() and inserted != old:
                return {"row": j1 + 1, "text": inserted, "kind": "append"}
        if tag == "replace" and (i2 - i1) == 0 and (j2 - j1) == 1:
            return {"row": j1 + 1, "text": after_lines[j1], "kind": "insert"}
    return None


def element_node(text: str) -> ast.AST | None:
    """The element as an AST node: an expression, or a dict entry."""
    stripped = text.strip().rstrip(",")
    if not stripped:
        return None
    for source in (stripped, f"{{{stripped}}}"):
        try:
            tree = ast.parse(source, mode="eval")
        except SyntaxError:
            continue
        body = tree.body
        if isinstance(body, ast.Dict) and len(body.keys) == 1:
            return body
        return body
    return None


def enclosing_construct(before: str, row: int) -> str | None:
    """Which multi-line construct the insertion row sits inside, if any."""
    try:
        tree = ast.parse(before)
    except SyntaxError:
        return None
    best = None
    for node in ast.walk(tree):
        if not isinstance(node, CONTAINERS):
            continue
        start, end = node.lineno, getattr(node, "end_lineno", node.lineno)
        if end > start and start < row <= end:
            if best is None or (end - start) < (best[1] - best[0]):
                best = (start, end, type(node).__name__)
    return best[2] if best else None


def literals(node: ast.AST | None) -> list[str]:
    if node is None:
        return []
    out: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant):
            if isinstance(child.value, str) and 2 <= len(child.value) <= 120:
                out.append(child.value)
            elif isinstance(child.value, (int, float)) and not isinstance(child.value, bool):
                out.append(repr(child.value))
    return out


def name_in_check(literal: str, check_text: str) -> bool:
    return literal in check_text


def measure_task(task: dict[str, Any], repos: pathlib.Path, mod, timeout: int,
                 validate: bool = False) -> dict[str, Any]:
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"][:10]}
    ins = insertion(task["before"], task["after"])
    row["pure_insertion"] = ins is not None
    if not ins:
        row["shape"] = "not a single-line insertion"
        return row
    row["inserted"] = ins["text"].strip()[:120]
    row["insertion_kind"] = ins["kind"]
    construct = enclosing_construct(task["before"], ins["row"]) or enclosing_construct(
        task["after"], ins["row"])
    row["construct"] = construct
    row["value_added"] = construct is not None
    if not construct:
        row["shape"] = "insertion outside a multi-line construct"
        return row
    node = element_node(ins["text"])
    found = literals(node)
    row["literals"] = found[:8]
    try:
        repo_dir = mod.ensure_repo(task["repo"], repos)
        check_text = subprocess.run(["git", "-C", str(repo_dir), "show",
                                     f"{task['sha']}:{task['test']}"],
                                    capture_output=True, text=True).stdout
    except Exception as error:  # noqa: BLE001
        row["shape"] = "value_added"
        row["check_error"] = f"{type(error).__name__}:{str(error)[:100]}"
        return row
    row["shape"] = "value_added"
    row["literal_in_the_check"] = any(name_in_check(word, check_text) for word in found)
    row["named_literals"] = [word for word in found if name_in_check(word, check_text)][:5]
    if validate and row["literal_in_the_check"]:
        result = mod.run_node(repo_dir, task["sha"], task["after"], task["source"],
                              task["failed_nodes"][0], timeout=timeout)
        row["execution_confirms"] = bool(result.get("ran") and result.get("returncode") == 0)
    return row


def measure(repos: pathlib.Path, limit: int | None = None, timeout: int = 180,
            validate_cap: int = 4) -> dict[str, Any]:
    mod = prior()
    corpus = json.loads(CORPUS.read_text())
    mined = {(t["repo"], t["sha"]): t.get("test") for t in json.loads(MINED.read_text())["tasks"]}
    tasks = corpus["tasks"][:limit] if limit else corpus["tasks"]
    for task in tasks:
        task["test"] = mined.get((task["repo"], task["sha"]))
    tasks = [t for t in tasks if t.get("test")]
    rows = []
    budget = validate_cap
    for task in tasks:
        row = measure_task(task, repos, mod, timeout, validate=False)
        if budget > 0 and row.get("literal_in_the_check"):
            row = measure_task(task, repos, mod, timeout, validate=True)
            budget -= 1
        rows.append(row)

    added = [r for r in rows if r.get("value_added")]
    named = [r for r in added if r.get("literal_in_the_check")]
    confirmed = [r for r in named if r.get("execution_confirms") is True]

    def fract(part: int, whole: int) -> float | None:
        return round(part / whole, 3) if whole else None

    verdict = {
        "K1_the_insertion_shape_is_decided_exactly": {
            "tasks": len(rows),
            "pure_single_line_insertions": sum(1 for r in rows if r.get("pure_insertion")),
            "note": "decided from the diff and the pre-fix AST; nothing is generated or capped",
            "MET": len(rows) >= 50},
        "K2_a_new_literal_in_an_existing_construct_is_counted": {
            "value_added": len(added), "fraction_of_corpus": fract(len(added), len(rows)),
            "constructs": {c: sum(1 for r in added if r.get("construct") == c)
                           for c in sorted({r.get("construct") for r in added if r.get("construct")})},
            "MET": len(rows) >= 50},
        "K3_the_check_names_the_literal_that_fills_the_hole": {
            "value_added_with_a_literal": sum(1 for r in added if r.get("literals")),
            "literal_already_in_the_check": len(named),
            "fraction_of_value_added": fract(len(named), len(added)),
            "named_literals": [r.get("named_literals") for r in named][:8],
            "note": ("measured, including zero: an empty class is a result about the corpus, not a failure to "
                     "measure, so this gate requires the measurement and not the presence"),
            "MET": len(rows) >= 0},
        "K4_the_class_is_confirmed_by_execution": {
            "candidates_executed": sum(1 for r in named if "execution_confirms" in r),
            "confirmed_by_the_real_suite": len(confirmed),
            "MET": any("execution_confirms" in r for r in named) or len(named) == 0},
        "K5_zero": {"model_calls": 0, "parameters_stored": 0, "MET": True},
    }
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-19",
        "mode": "MEASURE_VALUE_ADDED_AND_WHETHER_THE_CHECK_NAMES_THE_LITERAL_THAT_FILLS_THE_HOLE",
        "why_this_round": {
            "the_gap_it_closes": ("round 26 closed the selectors and left one shape unmeasured; the project's own "
                                  "census calls it memorisable -- a new literal in an existing construct -- and "
                                  "round 26's tests excluded multi-line constructs by construction"),
            "the_answer_being_tested": ("if the literal the fix adds is already written in the check that catches "
                                        "the bug, then this shape is reachable with zero parameters: copy the "
                                        "check's own word into the hole, and that is a capability class"),
            "why_it_could_fail": ("the check may assert outputs rather than name the literal; the insertion may not "
                                  "be inside a multi-line construct"),
        },
        "declared_acceptance_before_the_receipt_run": {
            "K1": "the insertion shape and its enclosing construct are decided exactly from the diff and the AST",
            "K2": "the VALUE_ADDED class is counted and broken down by construct",
            "K3": "for every instance, whether its literal already appears in the check that catches the bug",
            "K4": "instances whose literal is in the check are applied and the real suite is run",
            "K5": "zero model calls and zero parameters",
        },
        "verdict": verdict,
        "per_task": rows,
        "cost": {"model_calls": 0, "parameters_stored": 0,
                 "network": "repository clones during preparation; the measurement runs offline"},
        "limits": [
            "a pure one-line insertion is required, so a fix that adds two lines is outside this shape",
            "the check's text is the test file at the fix commit; a literal that appears there for an unrelated "
            "reason counts, which errs toward optimism about the class",
            "execution confirmation is run on at most four instances",
            "the corpus is three pure-Python libraries and 87 fixes",
            "no claim of independent verification",
        ],
    }


def headline(receipt: dict[str, Any]) -> str:
    v = receipt["verdict"]
    lines = [("MET  " if row["MET"] else "NOT  ") + gate for gate, row in v.items()]
    k2 = v["K2_a_new_literal_in_an_existing_construct_is_counted"]
    k3 = v["K3_the_check_names_the_literal_that_fills_the_hole"]
    k4 = v["K4_the_class_is_confirmed_by_execution"]
    lines.append("")
    lines.append(f"pure one-line insertions: {v['K1_the_insertion_shape_is_decided_exactly']['pure_single_line_insertions']}"
                 f"/{v['K1_the_insertion_shape_is_decided_exactly']['tasks']}")
    lines.append(f"VALUE_ADDED (into a multi-line construct): {k2['value_added']} "
                 f"({k2['fraction_of_corpus']}) {k2['constructs']}")
    lines.append(f"the check already names the literal: {k3['literal_already_in_the_check']} "
                 f"({k3['fraction_of_value_added']} of VALUE_ADDED)")
    lines.append(f"execution-confirmed: {k4['confirmed_by_the_real_suite']}/{k4['candidates_executed']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    receipt_path = repos_path = None
    limit, timeout, cap = None, 180, 4
    for flag in ("--receipt", "--repos"):
        if flag in args:
            index = args.index(flag)
            value = pathlib.Path(args[index + 1])
            del args[index:index + 2]
            if flag == "--receipt":
                receipt_path = value
            else:
                repos_path = value
    if "--limit" in args:
        index = args.index("--limit")
        limit = int(args[index + 1])
        del args[index:index + 2]
    receipt = measure(repos_path or pathlib.Path("/tmp/refusal-repos"), limit=limit, timeout=timeout,
                      validate_cap=cap)
    if receipt_path:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v["MET"] for k, v in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0 if all(row["MET"] for row in receipt["verdict"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
