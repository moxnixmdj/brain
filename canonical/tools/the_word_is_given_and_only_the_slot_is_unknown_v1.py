#!/usr/bin/env python3
"""If the word were given, is only its slot unknown?

WHY THIS ROUND EXISTS
---------------------
Three rounds are settled. Round 22: a real fix is mostly structural (72 of 87 add or
remove a line), the one-token ones live inside literals (7 of 8), and finding one blind
costs a median of 4,581 executions. Round 23: the machine's refusal always GRADES and
names the fix's new word only 32% of the time, and never when the fix is inside a
literal. The named next mechanism was: manufacture speaking checks from the
repository's own assertions.

Before building a synthesizer, the mechanism's two preconditions must be measured,
because if either fails the synthesizer is wasted work:

  (A) THE WORD IS SUPPLIED.  A speaking check is one whose own text contains the word
      the fix must introduce. The repository's tests are the only such text that is
      machine-produced, site-specific and free of parameters. So: is every new word of
      the real fix present in the test that catches it -- or in the refusal -- and how
      often is neither enough?

  (B) THE SLOT IS PREDICTABLE.  If the word is known, the remaining unknown is where
      it goes. If the change always lands in the function that refused, the slot search
      is local and cheap. If it lands anywhere in the file, no slot search is affordable.

Measured on the same 87 real fixes, executing the real upstream suites in their refused
state, with the pre-fix source reconstructed from the vendored pair. Zero model calls,
zero parameters.

The two numbers together are the ceiling of any parameter-free repair: the count of
fixes where the word is supplied AND the slot is local is exactly the set that
slot-guided search could reach without inventing anything.
"""
from __future__ import annotations

import ast
import difflib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import tokenize
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = ROOT / "canonical/corpus/real_fix_pairs_20261119_V1.json"
MINED = ROOT / "canonical/corpus/real_fix_commits_20261116_V1.json"
PRIOR = ROOT / "canonical/tools/does_the_refusal_name_the_missing_word_v1.py"
SCHEMA = "BRAIN_THE_WORD_IS_GIVEN_AND_ONLY_THE_SLOT_IS_UNKNOWN_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

SKIP = {tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE,
        tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT}


def prior():
    spec = importlib.util.spec_from_file_location("refusal_prior", PRIOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def vocabulary(text: str) -> tuple[set[str], set[str]]:
    """Identifiers and string contents of a text. Nothing is added to it."""
    names: set[str] = set()
    strings: set[str] = set()
    try:
        for tok in tokenize.generate_tokens(iter(text.splitlines(keepends=True)).__next__):
            if tok.type == tokenize.NAME:
                names.add(tok.string)
            elif tok.type == tokenize.STRING:
                try:
                    value = ast.literal_eval(tok.string)
                except (ValueError, SyntaxError):
                    value = tok.string.strip("'\"")
                if isinstance(value, str):
                    strings.add(value)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return names, strings


def supplied(word: str, *, is_name: bool, names: set[str], strings: set[str], text: str) -> bool:
    if is_name:
        return word in names
    return word in strings or word in text


def site_line(output: str, source_path: str) -> int | None:
    """The innermost frame in the source file: the line the machine refused at."""
    pattern = re.compile(rf"^{re.escape(source_path)}:(\d+):")
    hits: list[int] = []
    for line in output.splitlines():
        match = pattern.match(line.strip())
        if match:
            hits.append(int(match.group(1)))
    return hits[-1] if hits else None


def enclosing_function(source: str, line: int | None) -> tuple[str, int, int] | None:
    if line is None:
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    best = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start, end = node.lineno, getattr(node, "end_lineno", node.lineno)
            if start <= line <= end and (best is None or (end - start) < (best[2] - best[1])):
                best = (node.name, start, end)
    return best


def changed_lines(before: str, after: str) -> list[int]:
    """Line numbers in the fixed state that the fix touched."""
    before_lines, after_lines = before.splitlines(), after.splitlines()
    out: list[int] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=before_lines, b=after_lines,
                                                       autojunk=False).get_opcodes():
        if tag in ("replace", "insert"):
            out.extend(range(j1 + 1, j2 + 1))
    return out


def lands_in_function(after: str, function: str | None, lines: Sequence[int]) -> bool:
    if function is None or not lines:
        return False
    try:
        tree = ast.parse(after)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function:
            start, end = node.lineno, getattr(node, "end_lineno", node.lineno)
            if any(start <= line <= end for line in lines):
                return True
    return False


def measure_task(task: dict[str, Any], repos: pathlib.Path, mod, timeout: int) -> dict[str, Any]:
    node = (task.get("failed_nodes") or [None])[0]
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"][:10], "source": task["source"],
                           "node": node}
    new = mod.new_words(task["before"], task["after"])
    row["new_names"] = new["names"][:20]
    row["new_strings"] = new["strings"][:10]
    if not node or not task.get("test"):
        row.update({"ran": False, "reason": "no failed node or test path recorded"})
        return row
    try:
        repo_dir = mod.ensure_repo(task["repo"], repos)
        test_text = subprocess.run(["git", "-C", str(repo_dir), "show", f"{task['sha']}:{task['test']}"],
                                   capture_output=True, text=True).stdout
        result = mod.run_node(repo_dir, task["sha"], task["before"], task["source"], node, timeout=timeout)
    except Exception as error:  # noqa: BLE001
        row.update({"ran": False, "reason": f"{type(error).__name__}:{str(error)[:140]}"})
        return row
    if not result.get("ran"):
        row.update({"ran": False, "reason": result.get("reason", "not run")})
        return row
    output = result["output"]
    if "No module named pytest" in output or "no tests ran" in output:
        row.update({"ran": False, "reason": "harness:the node did not execute"})
        return row
    row["ran"] = True
    row["failed"] = result["returncode"] != 0
    if not row["failed"]:
        row["reason"] = "the reconstructed refused state passed"
        return row
    row["site"] = site_line(output, task["source"])
    spoken = mod.refusal_text(output)
    row["refusal_chars"] = len(spoken)
    test_names, test_strings = vocabulary(test_text)
    refusal_names, refusal_strings = vocabulary(spoken)
    name_supply = [w in test_names or w in refusal_names for w in new["names"]]
    string_supply = [supplied(w, is_name=False, names=set(), strings=test_strings | refusal_strings,
                              text=test_text + spoken) for w in new["strings"]]
    supply = name_supply + string_supply
    row["words"] = len(supply)
    row["words_supplied"] = sum(supply)
    row["all_words_supplied"] = bool(supply) and all(supply)
    row["any_word_supplied"] = any(supply)
    row["words_in_test_only"] = sum(1 for w in new["names"] if w in test_names) + sum(
        1 for w in new["strings"] if w in test_strings or w in test_text)
    function = enclosing_function(task["before"], row["site"])
    row["refusing_function"] = function[0] if function else None
    row["change_lands_in_that_function"] = lands_in_function(
        task["after"], row["refusing_function"], changed_lines(task["before"], task["after"]))
    return row


def measure(repos: pathlib.Path, limit: int | None = None, timeout: int = 180) -> dict[str, Any]:
    mod = prior()
    corpus = json.loads(CORPUS.read_text())
    # the vendored pairs hold the two source states; the test path lives in the mined corpus
    test_paths = {(t["repo"], t["sha"]): t.get("test")
                  for t in json.loads(MINED.read_text())["tasks"]}
    tasks = corpus["tasks"][:limit] if limit else corpus["tasks"]
    for task in tasks:
        task["test"] = test_paths.get((task["repo"], task["sha"]))
    rows = [measure_task(task, repos, mod, timeout) for task in tasks]
    ran = [r for r in rows if r.get("ran")]
    failed = [r for r in ran if r.get("failed")]
    with_words = [r for r in failed if r.get("words")]
    all_supplied = [r for r in with_words if r["all_words_supplied"]]
    any_supplied = [r for r in with_words if r["any_word_supplied"]]
    placed = [r for r in failed if r.get("change_lands_in_that_function")]
    both = [r for r in with_words if r["all_words_supplied"] and r.get("change_lands_in_that_function")]

    def fract(part: int, whole: int) -> float | None:
        return round(part / whole, 3) if whole else None

    verdict = {
        "K1_the_machine_points_into_the_source_only_sometimes": {
            "tasks": len(rows), "ran": len(ran), "failed": len(failed),
            "failures_with_a_source_frame": sum(1 for r in failed if r.get("site")),
            "fraction_with_a_source_frame": fract(sum(1 for r in failed if r.get("site")), len(failed)),
            "could_not_run": len(rows) - len(ran),
            "note": ("an exception that propagates out of the source leaves a frame there; an assert on a "
                     "returned value does not, because the code that produced the value has already returned. "
                     "The split is the finding, so it is reported rather than required"),
            "MET": len(failed) >= 20},
        "K2_the_word_is_supplied_by_the_check_or_the_refusal": {
            "fixes_with_a_new_word": len(with_words),
            "all_new_words_supplied": len(all_supplied),
            "any_new_word_supplied": len(any_supplied),
            "fraction_all": fract(len(all_supplied), len(with_words)),
            "fraction_any": fract(len(any_supplied), len(with_words)),
            "note": ("supplied means the identifier is a token of the test that catches the bug or of the "
                     "machine's own diagnostic lines, or the literal's content appears in their text; the "
                     "vocabulary is theirs, never invented here"),
            "MET": len(with_words) > 0},
        "K3_the_slot_is_local_to_the_function_that_refused": {
            "measured_over_the_failures_with_a_source_frame": sum(1 for r in failed if r.get("site")),
            "change_lands_in_the_refusing_function": len(placed),
            "fraction_of_sited": fract(len(placed), sum(1 for r in failed if r.get("site"))),
            "note": ("computed only over failures the machine localises into the source; for the others no "
                     "refusing function exists to be local to"),
            "MET": len(failed) > 0},
        "K4_the_ceiling_of_parameter_free_repair_is_counted_not_claimed": {
            "word_supplied_and_slot_local": len(both),
            "fraction_of_failed": fract(len(both), len(failed)),
            "reading": ("this is the set a slot-search over machine-supplied words could reach without "
                        "inventing a vocabulary: it is the mechanism's ceiling, not its success rate"),
            "MET": len(failed) > 0},
        "K5_zero": {"model_calls": 0, "parameters_stored": 0, "MET": True},
    }
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-19",
        "mode": "MEASURE_WHETHER_THE_WORD_IS_SUPPLIED_AND_THE_SLOT_IS_LOCAL_ON_REAL_REFUSED_SUITES",
        "why_this_round": {
            "the_gap_it_closes": ("round 23 ended by naming a mechanism -- manufacture speaking checks from the "
                                  "repository's own assertions -- whose two preconditions were never measured"),
            "the_answer_being_tested": ("if the word is usually supplied by the check or the refusal and the change "
                                        "usually lands in the function that refused, then parameter-free repair is a "
                                        "small slot search; if not, no slot search is affordable and the bottleneck is "
                                        "somewhere else entirely"),
            "why_it_could_fail": ("the test may assert only outputs, which do not name the fix's new identifier; the "
                                  "fix may land in a different function from the one that raised"),
        },
        "declared_acceptance_before_the_receipt_run": {
            "K1": "at least twenty real refused states executed, and the split between failures the machine "
              "localises into the source and those it does not is reported",
            "K2": "for every fix with a new word, it is recorded whether all, some or none of those words are present "
                  "in the check or the refusal",
            "K3": "the location of the real change is compared with the function that refused",
            "K4": "the conjunction of the two is counted, and reported as a ceiling rather than as a solve rate",
            "K5": "zero model calls and zero parameters",
        },
        "verdict": verdict,
        "per_task": rows,
        "cost": {"model_calls": 0, "parameters_stored": 0,
                 "network": "three repository clones during preparation; the measurement runs offline afterwards"},
        "limits": [
            "presence in the check or the refusal is necessary, not sufficient: a supplied word still needs a slot, "
            "and this round measures only whether the slot is local, not how to choose it",
            "a fix whose new words appear in the test for an unrelated reason counts as supplied; the measurement "
            "therefore errs toward optimism, which is the right direction for a ceiling",
            "the refusing function is the innermost function containing the traceback line; a fix may legitimately "
            "land in its caller, which this counts as not local",
            "tasks whose historical suites do not run here are recorded and never scored",
            "no claim of independent verification",
        ],
    }


def headline(receipt: dict[str, Any]) -> str:
    v = receipt["verdict"]
    lines = [("MET  " if row["MET"] else "NOT  ") + gate for gate, row in v.items()]
    k1 = v["K1_the_machine_points_into_the_source_only_sometimes"]
    k2 = v["K2_the_word_is_supplied_by_the_check_or_the_refusal"]
    k3 = v["K3_the_slot_is_local_to_the_function_that_refused"]
    k4 = v["K4_the_ceiling_of_parameter_free_repair_is_counted_not_claimed"]
    lines.append("")
    lines.append(f"refused states executed: {k1['failed']}/{k1['tasks']} ({k1['could_not_run']} could not run); "
                 f"the machine points into the source in {k1['failures_with_a_source_frame']} "
                 f"({k1['fraction_with_a_source_frame']})")
    lines.append(f"word supplied: all {k2['all_new_words_supplied']}/{k2['fixes_with_a_new_word']} "
                 f"({k2['fraction_all']}), any {k2['any_new_word_supplied']} ({k2['fraction_any']})")
    lines.append(f"slot local to the refusing function: {k3['change_lands_in_the_refusing_function']} "
                 f"of {k3['measured_over_the_failures_with_a_source_frame']} sited ({k3['fraction_of_sited']})")
    lines.append(f"ceiling (word supplied AND slot local): {k4['word_supplied_and_slot_local']} "
                 f"({k4['fraction_of_failed']} of failed)")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    receipt_path = repos_path = None
    limit, timeout = None, 180
    for flag, kind in (("--receipt", "path"), ("--repos", "path")):
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
    receipt = measure(repos_path or pathlib.Path("/tmp/refusal-repos"), limit=limit, timeout=timeout)
    if receipt_path:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v["MET"] for k, v in receipt["verdict"].items()}, indent=1))
    print(headline(receipt))
    return 0 if all(row["MET"] for row in receipt["verdict"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
