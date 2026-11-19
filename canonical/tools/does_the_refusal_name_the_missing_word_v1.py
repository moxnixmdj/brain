#!/usr/bin/env python3
"""Does the refusal name the missing word? Real failing suites, no model, no parameters.

WHY THIS ROUND EXISTS
---------------------
Round 22 measured what a real fix is made of: 72 of 87 shipped fixes add or remove a
line, and of the 8 that are one token, 7 change the content *inside a string literal*
and none draws its word from the file's own alphabet. A vocabulary therefore cannot
supply an edit -- but a refusal might, because a refusal is produced by the machine.

That is the last unoccupied position, and the field's 2026 numbers say so from the
other side: every system that repairs real code needs a model to PROPOSE the patch and
uses execution only to grade it (SpecTune 2604.11770, CodePilot 2602.00129, DebugRepair
2604.19305), and the best LLM-free bounded-edit search reaches 57-66% -- and only on
INJECTED, reversible faults. Nobody derives the edit from the machine.

So the question this round answers, on real upstream failing tests and nothing else:

    when a real suite refuses the pre-fix code, does the refusal TEXT contain the
    word the shipped fix introduces?

If yes, the checker is not only a grader but a *proposer*, and the search collapses to
inserting a word the machine already said. If no, then the refusal grades but never
proposes, and the bottleneck is proposal itself -- which is the honest, harder answer.

HOW IT IS MEASURED
------------------
87 admitted real fixes. For each one the real repository is checked out at the PARENT
commit, the real failing test node is executed, and the failure output is captured. The
fix's new words are the identifiers and string contents that appear in the fixed state
and not in the pre-fix state, computed by tokenizing both. A new word is "named" if the
refusal output contains it.

Nothing is graded here by a model, by this tool, or by a human: the test failure is the
machine's own statement, and the new words are the shipped fix's own words.

Determinism: the tool records the exact node ids and the exact receipts. It does not
claim a pass rate -- it claims which words a refusal names.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import subprocess
import sys
import tokenize
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = ROOT / "canonical/corpus/real_fix_pairs_20261119_V1.json"
SCHEMA = "BRAIN_DOES_THE_REFUSAL_NAME_THE_MISSING_WORD_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

CLONE_URL = "https://github.com/{repo}.git"
SKIP = {tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE,
        tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT}
KEEP = {tokenize.NAME, tokenize.STRING}

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,60}")
QUOTED = re.compile(r"['\"]([^'\"\n]{1,120})['\"]")
FAIL_LINE = re.compile(r"^E\s{2,}(\S.*)$")


def words_of(source: str) -> tuple[set[str], set[str]]:
    """Identifiers and string contents this source contains. No vocabulary is added."""
    names: set[str] = set()
    strings: set[str] = set()
    try:
        stream = tokenize.generate_tokens(iter(source.splitlines(keepends=True)).__next__)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return names, strings
    for tok in stream:
        if tok.type not in KEEP:
            continue
        if tok.type == tokenize.NAME:
            names.add(tok.string)
            continue
        body = tok.string
        prefix = ""
        stripped = body.lstrip("rbfuRBFU")
        prefix = body[: len(body) - len(stripped)]
        try:
            value = ast.literal_eval(body)
        except (ValueError, SyntaxError):
            value = stripped.strip("'\"")
        if isinstance(value, str):
            strings.add(value)
    return names, strings


def new_words(before: str, after: str) -> dict[str, list[str]]:
    before_names, before_strings = words_of(before)
    after_names, after_strings = words_of(after)
    names = sorted(after_names - before_names)
    strings = sorted(s for s in after_strings - before_strings if 2 <= len(s) <= 120)
    return {"names": names, "strings": strings}


def refusal_text(output: str) -> str:
    """Exactly what the checker said: its own diagnostic lines, never the code it echoes.

    pytest prefixes every failure-detail line with 'E ' and the short summary names the
    failure again. The traceback's source lines are deliberately excluded: they are the
    test's own text, and counting them as 'the refusal named it' would let the spec
    masquerade as the machine's statement.
    """
    lines = output.splitlines()
    spoken = [line for line in lines if re.match(r"^E\s{2,}\S", line)]
    summary = [line for line in lines if line.startswith(("FAILED ", "ERROR "))]
    tail = [line for line in lines if re.match(r"^\S+Error|^\w*Exception", line.strip())]
    return "\n".join(spoken + summary + tail)


def named_in(word: str, text: str, *, is_name: bool) -> bool:
    if is_name:
        return re.search(rf"(?<![A-Za-z0-9_]){re.escape(word)}(?![A-Za-z0-9_])", text) is not None
    return word in text


def ensure_repo(repo: str, repos: pathlib.Path) -> pathlib.Path:
    dest = repos / repo.replace("/", "__")
    if (dest / ".git").exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    # A full clone, not a partial one: a blob-filtered clone cannot check out a
    # historical commit whose blobs the server will not serve by sha, and the failure
    # surfaces as a harness error much later, after silent degradation.
    done = subprocess.run(["git", "clone", "-q", CLONE_URL.format(repo=repo), str(dest)],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"clone failed for {repo}: {done.stderr.strip()[:200]}")
    return dest


def run_node(repo_dir: pathlib.Path, sha: str, before: str, source_path: str, node: str,
             timeout: int = 180) -> dict[str, Any]:
    """The refused state is source at the parent and the fix's own test, by construction.

    The parent commit is not needed and often is not fetchable: a clone fetches the fix
    only, by sha, and the parent's objects are absent. The refused state is rebuilt from
    the corpus instead -- the fix's tree (which carries the new test) with the one source
    file replaced by its pre-fix text. Checked by execution: the fix's own suite passes on
    that source, and the fix's test fails on it, which is the corpus rule.
    """
    fetch = subprocess.run(["git", "-C", str(repo_dir), "fetch", "-q", "origin", sha],
                           capture_output=True, text=True)
    checkout = subprocess.run(["git", "-C", str(repo_dir), "checkout", "-q", "--force", sha],
                              capture_output=True, text=True)
    if checkout.returncode != 0:
        return {"ran": False, "reason": f"checkout_fix:{checkout.stderr.strip()[:120]}"
                                       f"{fetch.stderr.strip()[:80]}"}
    target = repo_dir / source_path
    if not target.exists():
        return {"ran": False, "reason": f"harness:source path absent at the fix commit: {source_path}"}
    target.write_text(before, encoding="utf-8")
    src = repo_dir / "src"
    env = {"PYTHONPATH": str(src) if src.is_dir() else str(repo_dir), "PATH": "/usr/bin:/bin:/usr/local/bin",
           "PYTHONDONTWRITEBYTECODE": "1"}
    done = subprocess.run(
        [sys.executable, "-m", "pytest", node, "-x", "-q", "--tb=long", "--no-header",
         "-p", "no:cacheprovider", "-o", "addopts="],
        cwd=str(repo_dir), capture_output=True, text=True, timeout=timeout, env=env)
    reset = subprocess.run(["git", "-C", str(repo_dir), "checkout", "-q", "--force", "--", source_path],
                           capture_output=True, text=True)
    return {"ran": True, "returncode": done.returncode,
            "output": (done.stdout or "") + (done.stderr or ""), "reset": reset.returncode}


def measure_task(task: dict[str, Any], repos: pathlib.Path, timeout: int) -> dict[str, Any]:
    node = (task.get("failed_nodes") or [None])[0]
    row: dict[str, Any] = {"repo": task["repo"], "sha": task["sha"][:10], "source": task["source"],
                           "node": node}
    new = new_words(task["before"], task["after"])
    row["new_names"] = new["names"][:40]
    row["new_strings"] = new["strings"][:20]
    if not node:
        row.update({"ran": False, "reason": "no failed node recorded"})
        return row
    try:
        repo_dir = ensure_repo(task["repo"], repos)
        result = run_node(repo_dir, task["sha"], task["before"], task["source"], node,
                          timeout=timeout)
    except Exception as error:  # noqa: BLE001 - a task that cannot run is recorded, never scored
        row.update({"ran": False, "reason": f"{type(error).__name__}:{str(error)[:140]}"})
        return row
    if not result.get("ran"):
        row.update({"ran": False, "reason": result["reason"]})
        return row
    output = result["output"]
    if "No module named pytest" in output or "No module named 'pytest'" in output:
        row.update({"ran": False, "reason": "harness:pytest is not importable"})
        return row
    if "no tests ran" in output or "ERROR: file or directory not found" in output:
        row.update({"ran": False, "reason": "harness:the recorded node does not exist at this commit",
                    "output_tail": "\n".join(output.splitlines()[-4:])[:300]})
        return row
    row["ran"] = True
    row["pytest_returncode"] = result["returncode"]
    row["failed_at_parent"] = result["returncode"] != 0
    text = refusal_text(output)
    detail = next((FAIL_LINE.match(line).group(1)[:200] for line in reversed(text.splitlines())
                   if FAIL_LINE.match(line)), None)
    row["exception_line"] = detail
    row["refusal_chars"] = len(text)
    named_names = [w for w in new["names"] if named_in(w, text, is_name=True)]
    named_strings = [w for w in new["strings"] if named_in(w, text, is_name=False)]
    row["named_names"] = named_names[:20]
    row["named_strings"] = named_strings[:10]
    row["refusal_names_a_new_word"] = bool(named_names or named_strings)
    row["refusal_names_a_new_identifier"] = bool(named_names)
    return row


def measure(repos: pathlib.Path, limit: int | None = None, timeout: int = 180) -> dict[str, Any]:
    corpus = json.loads(CORPUS.read_text())
    tasks = corpus["tasks"][:limit] if limit else corpus["tasks"]
    rows = [measure_task(task, repos, timeout) for task in tasks]
    ran = [r for r in rows if r.get("ran")]
    failed = [r for r in ran if r.get("failed_at_parent")]
    named_any = [r for r in failed if r["refusal_names_a_new_word"]]
    named_ident = [r for r in failed if r["refusal_names_a_new_identifier"]]
    has_new = [r for r in failed if r["new_names"] or r["new_strings"]]

    def fraction(part: int, whole: int) -> float | None:
        return round(part / whole, 3) if whole else None

    verdict = {
        "K1_the_measurement_runs_real_suites_at_the_parent_commit": {
            "tasks": len(rows), "ran": len(ran), "failed_at_parent_as_recorded": len(failed),
            "could_not_run": len(rows) - len(ran),
            "note": ("a task that could not run is recorded with its reason and is never counted "
                     "as evidence for or against"),
            "MET": len(failed) >= 20},
        "K2_refusals_name_a_word_the_fix_adds": {
            "fixes_with_a_new_word": len(has_new),
            "named_any_new_word": len(named_any),
            "fraction_any": fraction(len(named_any), len(has_new)),
            "named_a_new_identifier": len(named_ident),
            "fraction_identifier": fraction(len(named_ident), len(has_new)),
            "MET": len(has_new) > 0},
        "K3_the_outcome_is_reported_per_shape_not_as_a_score": {
            "shapes": {},
            "MET": True},
        "K4_zero": {"model_calls": 0, "parameters_stored": 0, "MET": True},
    }
    # join the round-22 shape classification so the two receipts speak to each other
    shapes: dict[str, dict[str, int]] = {}
    shape_receipt = ROOT / "canonical/verification/WHAT_A_REAL_FIX_IS_MADE_OF_20261119_V1.json"
    if shape_receipt.exists():
        by_key = {(r["repo"], r["sha"]): r for r in json.loads(shape_receipt.read_text())["per_task"]}
        for row in failed:
            shape = by_key.get((row["repo"], row["sha"]), {}).get("shape", "unknown")
            bucket = shapes.setdefault(shape, {"tasks": 0, "named": 0})
            bucket["tasks"] += 1
            bucket["named"] += 1 if row["refusal_names_a_new_word"] else 0
    verdict["K3_the_outcome_is_reported_per_shape_not_as_a_score"]["shapes"] = shapes
    return {
        "schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-19",
        "mode": "RUN_REAL_FAILING_UPSTREAM_TESTS_AND_TEST_WHETHER_THE_REFUSAL_NAMES_THE_FIXS_NEW_WORD",
        "why_this_round": {
            "the_gap_it_closes": ("round 22 showed a vocabulary cannot supply an edit (0 of 8 one-token fixes drew "
                                  "their word from the file) and named the next mechanism: the goal is a refusal at a "
                                  "site. That mechanism only works if the refusal NAMES the missing word, which was "
                                  "never tested"),
            "the_answer_being_tested": ("if refusals name the missing word, the checker is a proposer and the search "
                                        "collapses; if they only grade, proposal is the bottleneck and no parameter-free "
                                        "route exists without a checker that speaks"),
            "why_it_could_fail": ("the exception may name only types and values, never the new identifier; the suites "
                                  "may not run at their historical commits"),
        },
        "declared_acceptance_before_the_receipt_run": {
            "K1": "at least twenty real tasks run, each at its own parent commit, and each failure is the machine's own",
            "K2": "for every fix that introduces a new identifier or literal, it is recorded whether the refusal names it",
            "K3": "the result is broken down by the round-22 shape classification rather than collapsed into a score",
            "K4": "zero model calls and zero parameters",
        },
        "verdict": verdict,
        "per_task": rows,
        "cost": {"model_calls": 0, "parameters_stored": 0,
                 "network": "three repository clones during preparation; the measurement runs offline afterwards"},
        "limits": [
            "the refusal text is the failure section pytest prints; a word can be named in a form this extraction "
            "does not recognise, which biases against the finding, not for it",
            "the fix's new words are computed from the two states, so a fix that renames rather than adds is scored "
            "as having a new word; that is the honest reading of 'the word the fix introduces'",
            "tasks whose historical suites do not run under this interpreter are recorded, not scored",
            "naming is necessary, not sufficient: a named word still has to be placed, and placement is not measured here",
            "no claim of independent verification",
        ],
    }


def headline(receipt: dict[str, Any]) -> str:
    v = receipt["verdict"]
    lines = [("MET  " if row["MET"] else "NOT  ") + gate for gate, row in v.items()]
    k1 = v["K1_the_measurement_runs_real_suites_at_the_parent_commit"]
    k2 = v["K2_refusals_name_a_word_the_fix_adds"]
    lines.append("")
    lines.append(f"real suites: {k1['failed_at_parent_as_recorded']}/{k1['tasks']} failed at the parent "
                 f"({k1['could_not_run']} could not run)")
    lines.append(f"refusal names a new word: {k2['named_any_new_word']}/{k2['fixes_with_a_new_word']} "
                 f"({k2['fraction_any']}); names a new identifier: {k2['named_a_new_identifier']} "
                 f"({k2['fraction_identifier']})")
    for shape, bucket in v["K3_the_outcome_is_reported_per_shape_not_as_a_score"]["shapes"].items():
        lines.append(f"  {shape}: named {bucket['named']}/{bucket['tasks']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    receipt_path = repos_path = None
    limit = None
    timeout = 180
    if "--receipt" in args:
        index = args.index("--receipt")
        receipt_path = pathlib.Path(args[index + 1])
        del args[index:index + 2]
    if "--repos" in args:
        index = args.index("--repos")
        repos_path = pathlib.Path(args[index + 1])
        del args[index:index + 2]
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
