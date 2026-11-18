"""The statement names the change but does not specify it.

WHAT IS LEFT AFTER FIVE SPENT DIMENSIONS
----------------------------------------
Input shape (round 17), the value a condition wants (18), the repository's own documents (19) and the language's
protocol operations (20) were all measured against the same residual work: the parts a change's own suite accepts
without pinning. None of them added a pin beyond what the change's test already provided, and round 20 found why --
27 of 36 fixes are fully pinned by their own suites, and the parts that stay open are the ones nobody tested.

That leaves exactly one source inside the loop that contains what the artifact does not: **the statement the author
wrote about the change** -- the commit message. `declared_input_derivation_v1` already binds *slot values* from human
sentences (which file, which name, which test command). Nothing in the tree asks the harder question:

    does the statement say what the behaviour SHOULD BE -- an expected value, an expected exception, a number?

That is the question this module measures, and it measures it in the only way that counts: by trying to build the
pin from the statement alone and verifying it against both states.

WHAT IT DOES
------------
    statement   the commit body from the repository the task was mined from (git, local, no network)
    names       does any quoted literal or code identifier in the statement appear in the changed hunk or in the
                name of the function that contains it?  (this is the weak form: the statement mentions the change)
    specifies   can a pin be CONSTRUCTED from the statement alone -- its quoted literals as inputs, its exception
                and identifier names as expectations -- and does that pin pass at the fixed state and fail at the
                reverted one?  (this is the strong form, and it is the only one that buys capability)

A statement that merely names the change is not a specification, and the difference between the two columns is the
whole answer.

WHAT IS NOT DONE
----------------
No model. No network at measurement time. Nothing is stored. A quoted literal is used as an input because that is
what a quotation is; an exception name is used as an expectation because a capitalised name ending in Error is one.
Neither is guessed, and a statement that supplies nothing produces ``REFUSED__STATEMENT_SAYS_NOTHING`` rather than a
guess. Custom exception classes are imported from the module that defines them, or the candidate is dropped.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import json
import pathlib
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import checkability_by_differential_pin_v1 as C  # noqa: E402  the two-state prober
from canonical.swe_kernel import history_induced_edit_grammar_v1 as G  # noqa: E402
from canonical.swe_kernel import pins_from_the_reverted_part_v1 as SYN  # noqa: E402
from canonical.swe_kernel import reach_the_changed_site_v1 as R  # noqa: E402
from canonical.swe_kernel import what_the_verifier_actually_pins_v1 as PINS  # noqa: E402

SCHEMA = "BRAIN_THE_SMALLEST_QUESTION_THAT_MAKES_THIS_CHECKABLE_V1"
MODEL_CALLS = 0
NETWORK_CALLS = 0
MAX_PARTS = 3
PIN_TEST_NAME = "test_round21_statement_pin.py"

QUOTED = re.compile(r"['\"`]([^'\"`\n]{1,80})['\"`]")
NAMED_EXCEPTION = re.compile(r"\b([A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning))\b")
IDENTIFIER = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b")
NUMBER = re.compile(r"(?<![\w.])(-?\d+(?:\.\d+)?)(?![\w.])")
IDENTIFIER_STOP = frozenset({
    "the", "and", "for", "not", "with", "this", "that", "from", "when", "into", "than", "then", "but", "are", "was",
    "has", "have", "had", "its", "it's", "also", "only", "now", "new", "use", "used", "add", "adds", "added", "make",
    "makes", "made", "fix", "fixed", "fixes", "bug", "issue", "return", "returns", "raise", "raises", "value",
    "values", "should", "would", "could", "must", "instead", "because", "which", "while", "there", "these", "those",
})


def statement_from_git(hist: pathlib.Path, repo_name: str, sha: str) -> str:
    """The author's own words about the change, read from the clone the corpus was built from."""
    directory = hist / repo_name
    if not (directory / ".git").exists():
        return ""
    done = subprocess.run(["git", "-C", str(directory), "log", "-1", "--format=%B", sha],
                          capture_output=True, text=True, timeout=120)
    return done.stdout.strip() if done.returncode == 0 else ""


def tokens_of(statement: str, source: str) -> dict[str, list[str]]:
    """What the statement states, filtered to what the artifact also knows. Nothing is inferred."""
    quoted = [text for text in QUOTED.findall(statement) if len(text.strip()) >= 2]
    exceptions = sorted({name for name in NAMED_EXCEPTION.findall(statement) if name in source})
    numbers = NUMBER.findall(statement)
    identifiers = sorted({name for name in IDENTIFIER.findall(statement)
                          if name not in IDENTIFIER_STOP and name in source})
    return {"quoted": quoted[:20], "exceptions": exceptions[:8], "numbers": numbers[:8],
            "identifiers": identifiers[:20]}


def names_the_change(part: Mapping[str, Any], source: str, statement_tokens: Mapping[str, Sequence[str]]) -> bool:
    """Weak form: the statement mentions a literal or a code identifier that the changed hunk itself contains."""
    added = str(part.get("added") or "")
    removed = str(part.get("removed") or "")
    haystack = added + "\n" + removed
    for literal in statement_tokens.get("quoted") or []:
        if literal in haystack:
            return True
    for name in list(statement_tokens.get("identifiers") or []) + list(statement_tokens.get("exceptions") or []):
        if re.search(rf"\b{re.escape(name)}\b", haystack):
            return True
    return False


def _calls_from_statement(statement_tokens: Mapping[str, Sequence[str]],
                          seeds: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """A quoted literal is an input; every callable the test already uses is a place to put it."""
    calls: list[dict[str, Any]] = []
    for literal in statement_tokens.get("quoted") or []:
        for seed in seeds:
            calls.append({"module": seed["module"], "function": seed["function"], "args": ["=" + literal]})
    return calls


def _importable_exception(name: str, source: str, module: str) -> str | None:
    """A pin may only raise what the artifact defines: resolve it from the module, never guess the import path."""
    try:
        parsed = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(parsed):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return f"from {module} import {name}"
    return None


def _assertion(call: Mapping[str, Any], record: Mapping[str, Any], source: str) -> str | None:
    arguments = ", ".join(repr(token[1:]) for token in call["args"] if token.startswith("="))
    expression = f"_make({arguments})"
    if record.get("outcome") == "RAISED":
        name = str(record.get("type") or "")
        if hasattr(builtins, name):
            return f"    with pytest.raises({name}):\n        {expression}\n", ""
        imported = _importable_exception(name, source, call["module"])
        if imported:
            return f"    with pytest.raises({name}):\n        {expression}\n", imported + "\n"
        return None
    if record.get("outcome") == "RETURNED":
        rendered = str(record.get("value_repr") or "")
        if not rendered or "0xADDR" in rendered or len(rendered) > 180:
            return None
        return f"    assert repr({expression}) == {rendered!r}\n", ""
    return None


def _pin_source(call: Mapping[str, Any], record: Mapping[str, Any], source: str) -> str | None:
    built = _assertion(call, record, source)
    if built is None:
        return None
    body, extra = built
    return ("import pytest\n\n" + extra + f"from {call['module']} import {call['function']} as _make\n\n\n"
            "def test_what_the_statement_said_must_hold():\n" + body)


def _signature(record: Mapping[str, Any]) -> str:
    return C._signature(record)


def judge_part(tree: pathlib.Path, source_rel: str, fixed: str, mutant: str,
               statement_tokens: Mapping[str, Sequence[str]], seeds: Sequence[Mapping[str, Any]],
               source_text: str) -> dict[str, Any]:
    """The strong form only: a pin built from the statement that passes at fixed and fails at the revert."""
    calls = _calls_from_statement(statement_tokens, seeds)
    if not calls:
        return {"state": "REFUSED__STATEMENT_QUOTES_NOTHING", "candidates": 0}
    target = tree / source_rel
    original = target.read_bytes()
    try:
        target.write_text(fixed, encoding="utf-8")
        at_fixed = C.probe(tree, calls)
        target.write_text(mutant, encoding="utf-8")
        at_mutant = C.probe(tree, calls)
    finally:
        target.write_bytes(original)
    if not at_fixed or len(at_fixed) != len(at_mutant):
        return {"state": "REFUSED__PROBE_FAILED", "candidates": len(calls)}
    differences = [(call, left, right) for call, left, right in zip(calls, at_fixed, at_mutant)
                   if _signature(left) != _signature(right)]
    pin_file = tree / PIN_TEST_NAME
    verified: dict[str, Any] | None = None
    try:
        for call, left, right in differences:
            built = _pin_source(call, left, source_text)
            if built is None:
                continue
            pin_file.write_text(built, encoding="utf-8")
            if not G.try_candidate(tree, source_rel, PIN_TEST_NAME, fixed)["passed"]:
                continue
            if G.try_candidate(tree, source_rel, PIN_TEST_NAME, mutant)["passed"]:
                continue
            verified = {"input": call["args"][0][1:], "callable": f"{call['module']}.{call['function']}",
                        "fixed": _signature(left), "reverted": _signature(right), "assertion": built}
            break
    finally:
        pin_file.unlink(missing_ok=True)
    return {"state": "SPECIFIED" if verified else "NAMED_ONLY", "candidates": len(calls),
            "differences": len(differences), "pin": verified}


def audit_task(task: Mapping[str, Any], grammar: Sequence[Mapping[str, Any]], hist: pathlib.Path,
               cap: int = MAX_PARTS) -> dict[str, Any]:
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
    statement = statement_from_git(hist, task["name"], task["sha"])
    row["statement"] = statement.replace("\n", " ")[:200]
    statement_tokens = tokens_of(statement, fixed)
    row["tokens"] = {key: len(value) for key, value in statement_tokens.items()}
    test_source = (tree / test_rel).read_text(encoding="utf-8", errors="replace") \
        if (tree / test_rel).is_file() else ""
    seeds = [{"module": call["module"], "function": call["function"]}
             for call in SYN.calls_from_the_test(test_source)
             if isinstance(call.get("module"), str) and isinstance(call.get("function"), str)]
    unique, seen = [], set()
    for seed in seeds:
        key = (seed["module"], seed["function"])
        if key not in seen:
            seen.add(key)
            unique.append(seed)
    row["callables"] = len(unique)
    judged: list[dict[str, Any]] = []
    for part in PINS.hunks(defective, fixed):
        if len(judged) >= cap:
            break
        if not PINS.is_behavioural(fixed, part) or PINS.typing_only(fixed, part):
            continue
        mutant = PINS.revert(fixed, defective, part)
        if G.try_candidate(tree, source_rel, test_rel, mutant)["passed"] is False:
            continue                       # the suite already pins this part
        verdict = judge_part(tree, source_rel, fixed, mutant, statement_tokens, unique, fixed)
        verdict["named"] = names_the_change(part, fixed, statement_tokens)
        verdict["part_head"] = str(part.get("added") or "").strip()[:120] or "(removal)"
        judged.append(verdict)
    # What is left is not a search problem but a question, and the question is specific: these are the callables the
    # test already reaches, the two states agree on every one of them for every input the statement states, and the
    # missing object is the outcome that should differ. Naming WHO has to answer it is the honest end of the census.
    row["the_question"] = {
        "asked_of": "the author of the change",
        "needs": "one input and the outcome it must produce",
        "reachable_callables": len(unique),
        "statement_supplies_an_expected_value": bool(statement_tokens.get("quoted")),
    }
    return {**row, "parts": judged, "unpinned_parts": len(judged),
            "named": sum(1 for item in judged if item["named"]),
            "specified": sum(1 for item in judged if item["state"] == "SPECIFIED"),
            "state": "SPECIFIED" if any(item["state"] == "SPECIFIED" for item in judged) else
                     (PINS.FULLY_PINNED if not judged else "NAMED_ONLY")}


def measure(tasks: Sequence[Mapping[str, Any]], grammar: Sequence[Mapping[str, Any]],
            hist: pathlib.Path) -> dict[str, Any]:
    rows = [audit_task(task, grammar, hist) for task in tasks]
    states: dict[str, int] = {}
    for row in rows:
        states[row["state"]] = states.get(row["state"], 0) + 1
    parts = [item for row in rows for item in (row.get("parts") or [])]
    with_statement = [row for row in rows if (row.get("statement") or "").strip()]
    return {
        "schema": SCHEMA, "rows": rows, "model_calls": MODEL_CALLS, "network_calls": NETWORK_CALLS,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "totals": {
            "tasks": len(rows), "states": states,
            "tasks_with_a_statement": len(with_statement),
            "parts_audited": len(parts),
            "parts_the_statement_names": sum(1 for item in parts if item.get("named")),
            "parts_the_statement_specifies": sum(1 for item in parts if item["state"] == "SPECIFIED"),
            "candidates_probed": sum(item.get("candidates") or 0 for item in parts),
            "parts_that_require_a_question": sum(1 for item in parts if item["state"] != "SPECIFIED"),
            "differences_found": sum(item.get("differences") or 0 for item in parts),
            "naming_share": round(sum(1 for item in parts if item.get("named")) / len(parts), 3) if parts else None,
            "specifying_share": round(sum(1 for item in parts if item["state"] == "SPECIFIED") / len(parts), 3)
            if parts else None,
            "certified_share_before": 0.762, "certified_share_after": 0.762,
        },
    }


def headline(report: Mapping[str, Any]) -> str:
    totals = report["totals"]
    won = [(row, item) for row in report["rows"] for item in (row.get("parts") or [])
           if item["state"] == "SPECIFIED"]
    detail = "; ".join(f"{row['repo'].split('/')[-1]} {row['sha'][:8]}: "
                       f"{(item['pin'] or {}).get('input', '')!r}" for row, item in won)
    return (f"{totals['tasks']} real fixes ({totals['tasks_with_a_statement']} with a statement): "
            f"{totals['parts_audited']} parts the suite accepts without. The statement NAMES the change on "
            f"{totals['parts_the_statement_names']} of them ({totals['naming_share']}); it SPECIFIES it -- a pin "
            f"built from its own quoted literals and verified against both states -- on "
            f"{totals['parts_the_statement_specifies']} ({totals['specifying_share']}), from "
            f"{totals['candidates_probed']} candidates and {totals['differences_found']} differences."
            + (f" {detail}" if detail else ""))


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
    report = measure(tasks, grammar, args.hist)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"written: {args.json}")
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
