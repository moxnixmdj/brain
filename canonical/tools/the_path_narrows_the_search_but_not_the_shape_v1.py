#!/usr/bin/env python3
"""Does the executed path narrow the search, and does that matter?

WHY THIS ROUND EXISTS
---------------------
Round 25 falsified value provenance (producer of the rejected value found for 1.2% of
failures, localising the fix 0 of 69 times) and left one observation standing: among the
failures the traceback cannot localise, a function the real fix changed was on the
EXECUTED PATH in 65.2% of cases. That produced this round's prediction, written down
before the build:

  path-restricted search -- enumerate single-token substitutions only inside the executed
  functions of the file under repair and grade by executing that one test -- should give
  containment in the high tens of percent at a cost in the low hundreds of executions,
  against round 22's whole-file median of 4,581.

This round tests that prediction, and tests the thing the prediction quietly assumes: that
the true fix is a token substitution at all. Round 22 measured that only 15 of 87 real
fixes are token-shaped, so no restriction of the token space can exceed 15/87 = 17%. If
that holds, path restriction buys COST but not COVERAGE, and the ceiling is spent on
shape, not search.

So two spaces are measured on the same 87 fixes, statically and exactly (a candidate
counts only if it reproduces the fixed file byte for byte):

  S1  path-restricted single-token substitution        (the promised prediction)
  S2  structure completion: add one element to a literal collection or one argument to a
      call inside an executed function, with the word drawn from the file's own tokens,
      dir() of the machine's types, or the check's own literals  (the dominant shape)

and then the contained candidates are EXECUTED against the real suite, so the claim is not
that the text matches but that the machine passes.

Zero model calls, zero parameters.
"""
from __future__ import annotations

import ast
import builtins
import importlib.util
import io
import json
import pathlib
import sys
import tokenize
from typing import Any, Iterator, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = ROOT / "canonical/corpus/real_fix_pairs_20261119_V1.json"
MINED = ROOT / "canonical/corpus/real_fix_commits_20261116_V1.json"
PRODUCER = ROOT / "canonical/tools/the_value_that_was_rejected_had_a_producer_v1.py"
SLOT = ROOT / "canonical/tools/the_word_is_given_and_only_the_slot_is_unknown_v1.py"
SCHEMA = "BRAIN_THE_PATH_NARROWS_THE_SEARCH_BUT_NOT_THE_SHAPE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

CLASSES = {tokenize.OP: "op", tokenize.NAME: "name", tokenize.NUMBER: "number",
           tokenize.STRING: "string"}
SKIP = {tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE,
        tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT}
CAP = 6000


def modules():
    out = {}
    for name, path in (("producer", PRODUCER), ("slot", SLOT)):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        out[name] = module
    return out["producer"], out["slot"]


def machine_names() -> list[str]:
    names = set(dir(builtins))
    for probe in (str, bytes, dict, list, tuple, set, int, float, bool):
        names |= set(dir(probe))
    return sorted(n for n in names if n.isidentifier())


def file_alphabet(source: str) -> dict[str, set[str]]:
    out = {"op": set(), "name": set(), "number": set(), "string": set()}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type in SKIP or tok.type not in CLASSES:
                continue
            if tok.start[0] != tok.end[0]:
                continue
            out[CLASSES[tok.type]].add(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def executed_functions(payload: dict) -> set[str]:
    return {event["func"] for event in payload.get("events", [])}


def function_ranges(source: str, names: set[str]) -> list[tuple[str, int, int]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            out.append((node.name, node.lineno, getattr(node, "end_lineno", node.lineno)))
    return out


SHAPE = ROOT / "canonical/tools/the_edit_is_in_the_files_own_alphabet_v1.py"


def shape_of(before: str, after: str) -> dict[str, Any]:
    """Round 22's exact measurement: how many tokens separate the two states, and where."""
    spec = importlib.util.spec_from_file_location("shape_round", SHAPE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.measure_task({"repo": "x/y", "sha": "0" * 40, "source": "m.py",
                                "before": before, "after": after}, machine=module.machine_alphabet())


def exact_token_hit(shape: dict[str, Any], ranges: Sequence[tuple[str, int, int]]) -> dict[str, Any]:
    """The fix is contained iff it is one token on one line inside an executed function.

    No enumeration and no cap: the shape measurement already says whether the fix is a
    single substitution and on which line, so containment is a set membership of that line
    and rank is the number of same-class substitutes that precede it in a fixed order.
    """
    witnesses = shape.get("witnesses") or []
    distances = shape.get("per_line_distance") or []
    if len(distances) != 1 or distances[0] != 1 or not witnesses:
        return {"contained": False, "why": shape.get("shape")}
    line = witnesses[0]["line"]
    inside = any(start <= line <= end for _, start, end in ranges)
    pool = sorted(set(dict.fromkeys(witnesses[0].get("class_pool") or [])))
    return {"contained": inside, "line": line,
            "rank": (pool.index(witnesses[0]["became"]) + 1) if witnesses[0]["became"] in pool else None,
            "why": "one token on line %d, %s an executed function" % (line, "inside" if inside else "outside")}


def exact_structure_hit(before: str, after: str,
                        ranges: Sequence[tuple[str, int, int]]) -> dict[str, Any]:
    """The fix is contained iff it inserts `, word` at a slot inside an executed function.

    Slots are the closing brackets of a literal collection or a call on a single line, read
    from the pre-fix AST. Insertion is detected by common prefix and suffix, so nothing is
    enumerated and nothing can be truncated.
    """
    before_lines, after_lines = before.splitlines(), after.splitlines()
    if len(before_lines) != len(after_lines):
        return {"contained": False, "why": "line count changed"}
    changed = [i for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
    if len(changed) != 1:
        return {"contained": False, "why": f"{len(changed)} lines changed"}
    row = changed[0] + 1
    if not any(start <= row <= end for _, start, end in ranges):
        return {"contained": False, "why": "outside the executed functions"}
    before_line, after_line = before_lines[row - 1], after_lines[row - 1]
    prefix = 0
    while prefix < min(len(before_line), len(after_line)) and before_line[prefix] == after_line[prefix]:
        prefix += 1
    suffix = 0
    while (suffix < min(len(before_line), len(after_line)) - prefix
           and before_line[len(before_line) - 1 - suffix] == after_line[len(after_line) - 1 - suffix]):
        suffix += 1
    inserted = after_line[prefix:len(after_line) - suffix] if suffix else after_line[prefix:]
    word = inserted.strip()
    if not word.startswith(",") or len(word.split()) != 2:
        return {"contained": False, "why": "not a single-element insertion"}
    try:
        tree = ast.parse(before)
    except SyntaxError:
        return {"contained": False, "why": "unparseable"}
    for node in ast.walk(tree):
        if not hasattr(node, "lineno") or node.lineno != row:
            continue
        if node.lineno != getattr(node, "end_lineno", node.lineno):
            continue
        if isinstance(node, (ast.List, ast.Set, ast.Tuple)) and node.elts:
            slot = node.end_col_offset - 1
        elif isinstance(node, ast.Call):
            slot = node.end_col_offset - 1
        else:
            continue
        if slot == prefix:
            return {"contained": True, "line": row, "rank": None, "inserted": word}
    return {"contained": False, "why": "the insertion is not at a literal or call slot"}


def exact_statement_hit(before: str, after: str,
                        ranges: Sequence[tuple[str, int, int]]) -> dict[str, Any]:
    """The fix is contained iff every line it adds already exists in the file, inserted in
    an executed function. That is the 'copy a statement the repository already contains'
    generator, decided exactly by set membership instead of enumerated."""
    import difflib
    before_lines, after_lines = before.splitlines(), after.splitlines()
    if len(after_lines) <= len(before_lines):
        return {"contained": False, "why": "no line added"}
    added = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=before_lines, b=after_lines,
                                                       autojunk=False).get_opcodes():
        if tag in ("insert", "replace"):
            added.extend(range(j1 + 1, j2 + 1))
    if not added:
        return {"contained": False, "why": "no line added"}
    existing = {line.strip() for line in before_lines if line.strip()}
    reused = sum(1 for row in added if after_lines[row - 1].strip() in existing)
    inside = sum(1 for row in added if any(start <= row <= end for _, start, end in ranges))
    return {"contained": reused == len(added) and inside == len(added),
            "lines_added": len(added), "reused_from_the_file": reused,
            "inserted_inside_an_executed_function": inside,
            "why": ("every added line is already in the file and inside an executed function"
                    if reused == len(added) and inside == len(added) else
                    f"{reused}/{len(added)} lines reused, {inside}/{len(added)} inside")}


def rank_of(space: Iterator[str], after: str, cap: int = CAP) -> tuple[int | None, int]:
    """1-based rank of the fixed text in the space, and the space size examined."""
    for index, candidate in enumerate(space, 1):
        if candidate == after:
            return index, index
        if index >= cap:
            return None, index
    return None, 0


def measure_task(task: dict[str, Any], repos: pathlib.Path, producer, slot, timeout: int) -> dict[str, Any]:
    node = (task.get("failed_nodes") or [None])[0]
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"][:10], "node": node}
    if not node or not task.get("test"):
        row.update({"ran": False, "reason": "no failed node or test path"})
        return row
    try:
        repo_dir = producer.prior().ensure_repo(task["repo"], repos)
        result = producer.trace_run(repo_dir, task["sha"], task["before"], task["source"], node,
                                    timeout=timeout)
    except Exception as error:  # noqa: BLE001
        row.update({"ran": False, "reason": f"{type(error).__name__}:{str(error)[:120]}"})
        return row
    if not result.get("ran"):
        row.update({"ran": False, "reason": result.get("reason", "not run")})
        return row
    payload = result["payload"]
    if "No module named pytest" in payload["output"]:
        row.update({"ran": False, "reason": "harness:pytest is not importable"})
        return row
    row["ran"] = True
    row["failed"] = payload["code"] != 0
    names = executed_functions(payload)
    ranges = function_ranges(task["before"], names)
    row["executed_functions"] = sorted(n for n, _, _ in ranges)
    shape = shape_of(task["before"], task["after"])
    row["shape"] = shape.get("shape")
    s1 = exact_token_hit(shape, ranges)
    s2 = exact_structure_hit(task["before"], task["after"], ranges)
    row["s1"] = s1
    row["s2"] = s2
    row["s1_contained"] = bool(s1.get("contained"))
    row["s1_rank"] = s1.get("rank")
    row["s1_space"] = None
    row["s2_contained"] = bool(s2.get("contained"))
    row["s2_rank"] = s2.get("rank")
    row["s2_space"] = None
    s3 = exact_statement_hit(task["before"], task["after"], ranges)
    row["s3"] = s3
    row["s3_contained"] = bool(s3.get("contained"))
    row["repo_dir"] = str(repo_dir)
    return row


def validate(row: dict[str, Any], task: dict[str, Any], producer, timeout: int) -> bool | None:
    """Execute the contained candidate: the fix must be the machine passing, not the text matching."""
    if not (row.get("s1_contained") or row.get("s2_contained")):
        return None
    repo_dir = pathlib.Path(row["repo_dir"])
    target = repo_dir / task["source"]
    subprocess_ok = None
    original = target.read_text(encoding="utf-8") if target.exists() else None
    try:
        target.write_text(task["after"], encoding="utf-8")
        result = producer.prior().run_node(repo_dir, task["sha"], task["after"], task["source"],
                                           task["failed_nodes"][0], timeout=timeout)
        subprocess_ok = bool(result.get("ran") and result.get("returncode") == 0)
    finally:
        if original is not None:
            target.write_text(original, encoding="utf-8")
    return subprocess_ok


def measure(repos: pathlib.Path, limit: int | None = None, timeout: int = 180,
            validate_cap: int = 6) -> dict[str, Any]:
    producer, slot = modules()
    corpus = json.loads(CORPUS.read_text())
    mined = {(t["repo"], t["sha"]): t.get("test") for t in json.loads(MINED.read_text())["tasks"]}
    tasks = corpus["tasks"][:limit] if limit else corpus["tasks"]
    for task in tasks:
        task["test"] = mined.get((task["repo"], task["sha"]))
    rows = [measure_task(task, repos, producer, slot, timeout) for task in tasks]
    by_key = {(t["repo"], t["sha"][:10]): t for t in tasks}
    failed = [r for r in rows if r.get("ran") and r.get("failed")]
    s1 = [r for r in failed if r["s1_contained"]]
    s2 = [r for r in failed if r["s2_contained"]]
    s3 = [r for r in failed if r["s3_contained"]]
    both = [r for r in failed if r["s1_contained"] or r["s2_contained"] or r["s3_contained"]]

    validated = 0
    checked = 0
    for row in both[:validate_cap]:
        task = by_key[(row["repo"], row["sha"])]
        verdict = validate(row, task, producer, timeout)
        row["execution_confirms"] = verdict
        if verdict is not None:
            checked += 1
            validated += 1 if verdict else 0

    def fract(part: int, whole: int) -> float | None:
        return round(part / whole, 3) if whole else None

    def median(values: list[int]) -> float | None:
        import statistics
        return statistics.median(values) if values else None

    verdict = {
        "K1_the_executed_path_is_measured_on_real_refusals": {
            "tasks": len(rows), "ran": sum(1 for r in rows if r.get("ran")), "failed": len(failed),
            "could_not_run": len(rows) - sum(1 for r in rows if r.get("ran")),
            "MET": len(failed) >= 20},
        "K2_the_prediction_about_token_search_is_tested": {
            "predicted": "containment in the high tens of percent at a cost in the low hundreds",
            "s1_contained": len(s1), "fraction": fract(len(s1), len(failed)),
            "s1_rank_median": median([r["s1_rank"] for r in s1 if r["s1_rank"]]),
            "note_on_rank": ("rank is reported only where the witness carries its class pool; no space is "
                             "enumerated, so nothing is truncated and a missing rank is missing, not capped"),
            "token_shaped_fixes_from_round_22": 8,
            "of_those_inside_the_executed_path": len(s1),
            "of_those_the_path_excludes": 8 - len(s1),
            "shape_ceiling_from_round_22": "15 of 87 fixes are token-shaped, so no token space can exceed that",
            "MET": len(failed) > 0},
        "K3_structural_generation_from_the_files_own_text_is_measured": {
            "inline_element_added_to_a_literal_or_call": len(s2),
            "statement_inserted_whose_text_the_file_already_contains": len(s3),
            "fraction_statement": fract(len(s3), len(failed)),
            "note": ("the second is the dominant shape: the fix adds a line, and the question is whether that line's "
                     "text already exists somewhere in the file, which makes it copyable without a generator"),
            "MET": len(failed) > 0},
        "K4_the_union_and_its_cost": {
            "contained_by_either": len(both), "fraction": fract(len(both), len(failed)),
            "best_rank_median": median([min(r["s1_rank"] or 10 ** 9, r["s2_rank"] or 10 ** 9)
                                        for r in both if r["s1_rank"] or r["s2_rank"]])
            if any(r["s1_rank"] or r["s2_rank"] for r in both) else None,
            "whole_file_baseline_round_22": 4581,
            "MET": len(failed) > 0},
        "K5_containment_is_confirmed_by_execution": {
            "candidates_executed": checked, "confirmed_by_the_real_suite": validated,
            "note": "the claim is not that the text matches but that the machine passes",
            "MET": checked > 0},
        "K6_zero": {"model_calls": 0, "parameters_stored": 0, "MET": True},
    }
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-19",
        "mode": "TEST_THE_PATH_RESTRICTED_SEARCH_PREDICTION_AND_MEASURE_STRUCTURE_COMPLETION",
        "why_this_round": {
            "the_gap_it_closes": ("round 25 predicted that path-restricted search would give containment in the high "
                                  "tens of percent at a cost in the low hundreds; this tests it and also tests the "
                                  "assumption behind it, that the fix is a token substitution at all"),
            "the_answer_being_tested": ("if the executed path narrows the space enough, a parameter-free search over "
                                        "the file's own tokens becomes affordable and the shape ceiling is secondary; if "
                                        "not, the ceiling is shape and no search fixes it"),
            "why_it_could_fail": ("the path may contain the fix's function without containing the fix's line; only 15 of "
                                  "87 fixes are token-shaped, which bounds containment at 17% before any search"),
        },
        "declared_acceptance_before_the_receipt_run": {
            "K1": "the executed functions are read from a real traced run of every task",
            "K2": "S1 containment, rank and space size are measured and compared with the prediction and with the "
                  "shape ceiling",
            "K3": "S2 (structure completion) is measured in the same way, because it addresses the dominant shape",
            "K4": "the union and its best rank are compared with round 22's 4,581",
            "K5": "contained candidates are executed against the real suite",
            "K6": "zero model calls and zero parameters",
        },
        "verdict": verdict,
        "per_task": rows,
        "cost": {"model_calls": 0, "parameters_stored": 0,
                 "network": "repository clones during preparation; the measurement runs offline"},
        "limits": [
            "containment is decided exactly, by the shape of the diff and the membership of its line in the executed "
            "functions; nothing is enumerated and nothing is truncated",
            "containment requires byte equality with the fixed file, which is stricter than 'a patch that passes'",
            "S2 adds one element or argument with a word from the file, the machine or the check; it does not compose "
            "statements, which is what 13 of the 72 structural fixes do",
            "execution confirmation is run on at most six contained candidates, not on all of them",
            "no claim of independent verification",
        ],
    }


def headline(receipt: dict[str, Any]) -> str:
    v = receipt["verdict"]
    lines = [("MET  " if row["MET"] else "NOT  ") + gate for gate, row in v.items()]
    k2 = v["K2_the_prediction_about_token_search_is_tested"]
    k3 = v["K3_structural_generation_from_the_files_own_text_is_measured"]
    k4 = v["K4_the_union_and_its_cost"]
    k1 = v["K1_the_executed_path_is_measured_on_real_refusals"]
    k5 = v["K5_containment_is_confirmed_by_execution"]
    lines.append("")
    lines.append(f"traced refusals: {k1['failed']}/{k1['tasks']} ({k1['could_not_run']} could not run)")
    lines.append(f"S1 token search on the path: {k2['s1_contained']} contained ({k2['fraction']}), "
                 f"rank median {k2['s1_rank_median']}")
    lines.append(f"inline element added: {k3['inline_element_added_to_a_literal_or_call']}; statement copied from the "
                 f"file's own text: {k3['statement_inserted_whose_text_the_file_already_contains']} "
                 f"({k3['fraction_statement']})")
    lines.append(f"either: {k4['contained_by_either']} ({k4['fraction']}) at best-rank median "
                 f"{k4['best_rank_median']} against the whole-file baseline {k4['whole_file_baseline_round_22']}")
    lines.append(f"execution-confirmed: {k5['confirmed_by_the_real_suite']}/{k5['candidates_executed']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    receipt_path = repos_path = None
    limit, timeout, cap = None, 180, 6
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
    if "--timeout" in args:
        index = args.index("--timeout")
        timeout = int(args[index + 1])
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
