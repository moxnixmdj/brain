#!/usr/bin/env python3
"""What a run of a project's own tests says about a change, read from what the runner printed.

Why this exists
---------------
Three records of this line of work count a candidate as passing when its text is the text of a
patch that passed in somebody's recorded run. Nothing was run here. The organs that make the
candidates say "nothing here accepts a candidate: the caller's tests do". This is the reading of
those tests: the per-test lines Python's unittest runner prints when it is verbose (Django's runner
is that runner), and three questions asked of them.

  statuses       {test: PASSED | FAILED | ERROR | SKIPPED} from the lines "name ... ok" and their
                 like. Python 3.11 prints "test_x (pkg.mod.Class.test_x)" where older ones print
                 "test_x (pkg.mod.Class)", and `normal` brings both to the older form. A test with
                 a docstring is printed on two lines, its name and the first line of its
                 docstring, and is known here by BOTH: the lists SWE-bench publishes use the
                 docstring line, except where the docstring opens with an empty line, which
                 Python before 3.9 did not print and later ones do. Two tests can share a
                 docstring line; under that line the worse ending is kept, so a line passes only
                 when every test that carries it passed.
  identifiers    {test: the dotted name the runner takes as a label}, to run just those tests
  finished       whether the run got to its summary ("Ran N tests", then OK or FAILED)
  tells_apart    whether the tests tell the broken program from the fixed one HERE: with the fix
                 every test that should start passing passes, and without it at least one does
                 not. Where that does not hold the machine cannot judge the task, whatever a
                 candidate does.
  resolves       whether a candidate does what the fix does as far as these tests see: every
                 test that should start passing passes, and so does every test that should keep
                 passing AND passes with the fix here. A test that fails here even with the fix
                 says something about the machine, not about the candidate; it is left out and
                 `left_out` names it.

Nothing here runs anything, and nothing here knows a project: the caller runs the tests and hands
over what was printed.
"""
from __future__ import annotations

import re
from typing import Iterable, Mapping

SCHEMA = "BRAIN_TESTS_AS_THE_JUDGE_V1"
PASSED, FAILED, ERROR, SKIPPED = "PASSED", "FAILED", "ERROR", "SKIPPED"

_PASS_ENDS = (" ... ok", " ... OK", " ...  OK")
_WITH_METHOD = re.compile(r"^(\S+) \(((?:[^\s().]+\.)+)([^\s().]+)\)$")
_RAN = re.compile(r"^Ran (\d+) tests? in [0-9.]+s\s*$", re.MULTILINE)
_VERDICT = re.compile(r"^(OK|FAILED)\b[^\n]*$", re.MULTILINE)


def normal(name: str) -> str:
    """The name as unittest printed it before Python 3.11: `test_x (pkg.mod.Class.test_x)` becomes `test_x (pkg.mod.Class)`."""
    name = name.strip()
    found = _WITH_METHOD.match(name)
    if found and found.group(3) == found.group(1):
        return f"{found.group(1)} ({found.group(2)[:-1]})"
    return name


_WORSE = {ERROR: 3, FAILED: 3, SKIPPED: 2, PASSED: 1}


def _name_line(line: str) -> re.Match | None:
    """The line "test_x (pkg.mod.Class)" or "test_x (pkg.mod.Class.test_x)" a verbose runner prints for a test, or nothing."""
    return _WITH_METHOD.match(line.strip())


def _read(output: str) -> list[tuple[str, str | None, str]]:
    """(name or line the test is known by, the name line above it when it is a docstring line, how it ended), in the order printed."""
    out: list[tuple[str, str | None, str]] = []
    waiting: tuple[str, str | None] | None = None                  # a test whose line did not end with how it ended
    above: str | None = None                                       # a bare name line: the next line is its docstring's
    for raw in output.split("\n"):
        line = raw.strip()
        if " ... " in line:
            name, _, ending = line.partition(" ... ")
            if line.endswith(_PASS_ENDS):
                name, how = line.rsplit(" ... ", 1)[0], PASSED
            elif ending.startswith("skipped"):
                how = SKIPPED
            elif line.endswith(" ... FAIL"):
                name, how = line.rsplit(" ... ", 1)[0], FAILED
            elif line.endswith(" ... ERROR"):
                name, how = line.rsplit(" ... ", 1)[0], ERROR
            elif ending.startswith("expected failure"):
                how = SKIPPED
            elif ending.startswith("unexpected success"):
                how = FAILED
            else:
                how = ""                                           # the test printed something of its own after the dots
            owner = above if above is not None and _name_line(name) is None else None
            above = None
            if how:
                out.append((name, owner, how))
                waiting = None
            else:
                waiting = (name, owner)
        elif waiting is not None and line in ("ok", "FAIL", "ERROR"):
            out.append((waiting[0], waiting[1], {"ok": PASSED, "FAIL": FAILED, "ERROR": ERROR}[line]))
            waiting = None
        else:
            above = line if _name_line(line) is not None else None
    return out


def statuses(output: str) -> dict[str, str]:
    """{test: how it ended}, from the lines of a verbose run; a test with a docstring is there under its name and under the docstring's line."""
    found: dict[str, str] = {}
    shared: dict[str, str] = {}
    for name, owner, how in _read(output):
        if owner is None:
            found[normal(name)] = how
        else:
            found[normal(owner)] = how
            if name not in shared or _WORSE[how] > _WORSE[shared[name]]:
                shared[name] = how
    for line, how in shared.items():
        found.setdefault(line, how)
    return found


def identifiers(output: str) -> dict[str, list[str]]:
    """{test, by name and by docstring line: the dotted names to hand the runner as labels}."""
    out: dict[str, list[str]] = {}
    for name, owner, _ in _read(output):
        found = _name_line(owner if owner is not None else name)
        if found is None:
            continue
        method, dotted = found.group(1), found.group(2) + found.group(3)
        label = dotted if found.group(3) == method else f"{dotted}.{method}"
        for key in ([normal(owner), name] if owner is not None else [normal(name)]):
            if label not in out.setdefault(key, []):
                out[key].append(label)
    return out


def ran(output: str) -> int | None:
    """The number in the last "Ran N tests in ...", or None when the run never got there."""
    found = _RAN.findall(output)
    return int(found[-1]) if found else None


def finished(output: str) -> bool:
    """Whether the run got to its summary: "Ran N tests" and, after it, OK or FAILED."""
    at = None
    for at in _RAN.finditer(output):
        pass
    return at is not None and _VERDICT.search(output, at.end()) is not None


def passing(found: Mapping[str, str], names: Iterable[str]) -> list[str]:
    """Those of the names, as given, whose test passed."""
    return [name for name in names if found.get(normal(name)) == PASSED]


def tells_apart(base: Mapping[str, str], fixed: Mapping[str, str], fail_to_pass: Iterable[str]) -> bool:
    """Whether these tests tell the broken program from the fixed one here."""
    wanted = list(fail_to_pass)
    return bool(wanted) and len(passing(fixed, wanted)) == len(wanted) and len(passing(base, wanted)) < len(wanted)


def left_out(fixed: Mapping[str, str], pass_to_pass: Iterable[str]) -> list[str]:
    """The tests that should keep passing and do not pass here even with the fix."""
    names = list(pass_to_pass)
    kept = set(passing(fixed, names))
    return [name for name in names if name not in kept]


def resolves(candidate: Mapping[str, str], fixed: Mapping[str, str], fail_to_pass: Iterable[str], pass_to_pass: Iterable[str]) -> bool:
    """Whether the candidate does what the fix does, as far as these tests see."""
    first, keep = list(fail_to_pass), list(pass_to_pass)
    if not first or len(passing(fixed, first)) != len(first):
        return False
    judged = first + passing(fixed, keep)
    return len(passing(candidate, judged)) == len(judged)
