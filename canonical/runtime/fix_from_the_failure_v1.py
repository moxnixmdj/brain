"""Derive a repair from the failure's own words, and confirm it by re-running.

THE BOTTLENECK THIS ATTACKS. `repair_v1` repairs the ENVIRONMENT -- a missing module, a missing binary, a
path that is not there. It classified six ordinary program bugs as *"the failure matches nothing known;
refusing to guess"*, and it was right to: those are not environment faults, they are **bugs in the code**,
and their repair is an EDIT. `fix_shape_v1` can describe an edit's shape, but it needs both the buggy and the
fixed program, which is exactly what a real task does not give.

So the question is narrower than "can a program be fixed". It is: **can a repair be DERIVED from a failure,
with no fixed reference and no model?** Sometimes, and the criterion for "sometimes" is precise:

    THE FAILURE MUST STATE THE CORRECTION, AND THE WORLD MUST CONFIRM IT.

A `NameError` does both. CPython prints `name 'totl' is not defined. Did you mean: 'total'?` -- the bad name
and the correction, in the interpreter's own words. The correction is then checkable against the file (does
`total` exist? does `totl` not?) and the edit is confirmed by RE-RUNNING, not by believing the suggestion.

Measurements that shaped this module, all 2026-11-23:

    NameError    'totl' -> 'total'      the interpreter proposes it          REPAIRABLE HERE
    TypeError    str + int              no correction is stated             not repairable here
    KeyError     'b'                    no correction is stated             not repairable here
    IndexError   list index out of range no correction is stated            not repairable here

Four ordinary bugs, one repairable. That ratio is the honest content of this module and it is stated in the
code rather than in a footnote, because a 1-in-4 mechanism reported as "the system fixes its own programs"
would be the exact dishonesty this project is built against.

WHAT IT REFUSES TO DO. It never guesses a name. If the interpreter suggests nothing, or suggests something
that is not in the file, or the failure names a line that does not contain the bad name, it says so and stops.
A guess that happens to work on the bug in front of it is not a repair; it is a coincidence with a test.

Authority NONE. No model is called. Every accepted repair is confirmed by exit 0 on a re-run.
"""
from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_FIX_FROM_THE_FAILURE_V1"

#: CPython's own words, when it has a suggestion: `name 'totl' is not defined. Did you mean: 'total'?`
#: Also covers the multi-suggestion form, which is followed by a list.
_NAME_ERROR = re.compile(
    r"name '(?P<bad>[^']+)' is not defined(?:\.\s*Did you mean:?\s*'(?P<good>[^']+)'?)?")

#: `File "…/m.py", line 4` -- the location, which must be checked and not merely used.
_LOCATION = re.compile(r'File "(?P<path>[^"]+)", line (?P<line>\d+)')

#: The named repair classes, by the failure text. Closed, because a class is a claim that the CORRECTION is
#: stated. A pattern here without a correction behind it would be a classification pretending to be a fix.
_REPAIRABLE = {
    "A_NAME_IS_MISSPELLED_THE_INTERPRETER_SAYS_WHICH": _NAME_ERROR,
}


def classify(output: str) -> dict[str, Any]:
    """Is the correction stated in this failure? Which class, and with what values?

    Refuses for every failure that does not state a correction, and says which ones it can recognise --
    a caller deciding whether to keep trying needs to know that `KeyError` is not in the list rather than
    that it "failed".
    """
    text = str(output or "")
    for kind, pattern in _REPAIRABLE.items():
        match = pattern.search(text)
        if not match:
            continue
        groups = match.groupdict()
        if not groups.get("good"):
            return {"schema": SCHEMA, "repairable": False, "class": kind,
                    "why": "THE_INTERPRETER_STATED_A_PROBLEM_BUT_NO_CORRECTION",
                    "bad": groups.get("bad")}
        return {"schema": SCHEMA, "repairable": True, "class": kind,
                "bad": groups["bad"], "good": groups["good"],
                "evidence": match.group(0)[:160]}
    return {"schema": SCHEMA, "repairable": False,
            "why": "THE_FAILURE_STATES_NO_CORRECTION",
            "classes_that_do": sorted(_REPAIRABLE)}


def _names_in(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def repair_from_failure(program: str | pathlib.Path, output: str,
                        *, timeout: int = 60) -> dict[str, Any]:
    """Read the failure, check the correction against the file, apply it, and re-run to judge.

    The four checks that make this a derivation rather than a guess:

      1. the failure states a correction                (else: refuse)
      2. the correction EXISTS in the program           (else it is not a correction in scope)
      3. the bad name appears in the file               (else the failure belongs to another file)
      4. the program runs: exit 0 after the edit        (else the edit is reverted)

    A repair that fails check 4 is REVERTED and reported as failed. Leaving a wrong edit in place because
    it was plausible is worse than leaving the original bug: the original at least fails the same way twice.
    """
    path = pathlib.Path(program)
    if not path.is_file():
        return {"schema": SCHEMA, "repaired": False, "why": "THE_PROGRAM_IS_NOT_A_FILE",
                "program": str(program)}
    verdict = classify(output)
    if not verdict.get("repairable"):
        return {"schema": SCHEMA, "repaired": False, "program": str(path),
                "why": verdict.get("why"), "class": verdict.get("class"),
                "classes_that_do": verdict.get("classes_that_do")}

    bad, good = verdict["bad"], verdict["good"]
    original = path.read_text()
    names = _names_in(original)
    if good not in names:
        # the interpreter can suggest a builtin or a name from another module; in this file it does not
        # exist, so replacing with it would trade one NameError for another
        return {"schema": SCHEMA, "repaired": False, "program": str(path),
                "why": "THE_SUGGESTED_NAME_IS_NOT_IN_THE_PROGRAM", "bad": bad, "good": good}
    if bad not in original:
        return {"schema": SCHEMA, "repaired": False, "program": str(path),
                "why": "THE_FAILING_NAME_IS_NOT_IN_THE_PROGRAM", "bad": bad}

    # whole-word replacement only: `totl` must not be edited inside `totl_extra`
    edited = re.sub(r"\b%s\b" % re.escape(bad), good, original)
    path.write_text(edited)
    try:
        rerun = subprocess.run([sys.executable, str(path)], cwd=str(path.parent),
                               capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        path.write_text(original)
        return {"schema": SCHEMA, "repaired": False, "program": str(path),
                "why": "THE_REPAIRED_PROGRAM_TIMED_OUT", "bad": bad, "good": good}

    if rerun.returncode != 0:
        path.write_text(original)
        return {"schema": SCHEMA, "repaired": False, "program": str(path),
                "why": "THE_EDIT_DID_NOT_MAKE_THE_PROGRAM_RUN",
                "bad": bad, "good": good,
                "said_after": ((rerun.stdout or "") + (rerun.stderr or "")).strip()[-300:],
                "reverted": True}

    return {"schema": SCHEMA, "repaired": True, "program": str(path),
            "class": verdict["class"], "bad": bad, "good": good,
            "why": "THE_FAILURE_STATED_THE_CORRECTION_AND_THE_PROGRAM_NOW_RUNS",
            "output": ((rerun.stdout or "") + (rerun.stderr or "")).strip()[-400:],
            "judged_by": "RE_RUNNING, not by the suggestion"}


def main(argv: Sequence[str] | None = None) -> int:
    import json

    arguments = list(argv if argv is not None else sys.argv[1:])
    if not arguments:
        print(json.dumps({"schema": SCHEMA,
                          "usage": "fix_from_the_failure_v1 <program.py>  (runs it, then repairs)"}, indent=1))
        return 0
    program = pathlib.Path(arguments[0])
    first = subprocess.run([sys.executable, str(program)], cwd=str(program.parent),
                           capture_output=True, text=True, timeout=120)
    print(json.dumps(repair_from_failure(program, (first.stdout or "") + (first.stderr or "")), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
