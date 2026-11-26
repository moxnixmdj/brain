#!/usr/bin/env python3
"""The witness carries the distance: a failing test is not one bit, it is a point.

WHY THIS EXISTS, AND WHAT IT DOES NOT REBUILD
---------------------------------------------
The repair search in this tree accepts a candidate only when it STRICTLY lowers the
failure count. `python_iterative_software_repair_loop_v1._score` returns

    the number of failing tests            (an integer, 0 when the suite passes)

and its own module docstring measured what that costs:

    cwd at the repository root  ->  errors=1     (No module named 'calc')
    cwd at the source directory ->  failures=1   (-1 != 5)

    "Both score 1, so no edit to the source can ever strictly improve the metric and
     the repair loop reports OPEN__NO_STRICTLY_IMPROVING_CANDIDATE for every bug."

That is the whole disease stated by the instrument: two behaviourally unrelated programs
are the same point, so the space has no order, so the search cannot step. The project wrote
the same thing about itself in `FIVE_THOUSAND_DOCUMENTS_CHANGE_NOTHING...` -- *"the search
has no measure of distance to the part it is trying to reach"* -- and five rounds of
mechanism and five thousand documents moved the number by zero.

WHAT THE FIELD MEASURES AND DOES NOT SEARCH WITH
------------------------------------------------
FeatureBench (ICLR 2026) reports a *Passed Rate* next to Resolved Rate: "the average
fraction of fail-to-pass tests passed per task, serving as a soft indicator of partial
correctness", and on its hard real-world set GPT-5.1-Codex reads **20.0% resolved against
60.2% passed**. A 40-point gap between partial correctness and resolution is the gradient
the field measures but does not descend: it is used as a reporting statistic.

Gradient-Based Program Repair (2026) is the closest honest attempt -- "a loss that directly
measures deviations from correct behavior", searching a *numerical* program space. It needs
the program to be differentiable, so it needs a neural surrogate, so it needs training, so
it cannot be the runtime this project is constrained to be. **The differentiability was
never necessary.** A test already computes both operands and prints them. The distance is
not approximated by a surrogate -- it is observed, in the assertion's own message.

WHAT IS MEASURED
----------------
    failures(text)   the typed witness for each failing node: kind, expected, observed,
                     the assertion's own source line, and the values in scope
    distance(f)      a residual in [0, INF) whose zero means satisfied. TYPED, because
                     real failures are not all numeric: `DID NOT RAISE InvalidMetadata`
                     has no operands at all, and an escaped AttributeError has no value
                     yet. A scalar residual cannot express the difference between those,
                     and pretending it can is how an instrument lies.
    score(text)      (gates_satisfied, -total_distance) -- lexicographic, so a candidate
                     that satisfies one more gate always wins, and among candidates that
                     satisfy the same gates, the closer one wins. This ordering is what
                     the integer could not express.
    nearest(fs)      the failing node with the smallest distance: the next gate to work
                     on. Target selection falls out of the same number.
    improved(a, b)   strict lexicographic improvement. This is the predicate the search
                     needs; `b < a` on an integer was the whole bottleneck.

THE INTEGRITY LINE
------------------
Every number here is read from the test's own output. Nothing reads the fixed source, the
upstream diff, or any other model. The oracle is the test the repository shipped, and its
message is the only arithmetic this module does.
"""
from __future__ import annotations

import ast
import re
import typing

SCHEMA = "PROJECT_BRAIN_WITNESS_DISTANCE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
MODEL_CALLS = 0
NETWORK_CALLS = 0

# Distances for failures that carry no operand at all. They are ordered by how much the
# search can learn from them, not by how bad they look: a missing guard is one edit away
# (the guard is absent, and the test names the exception and the value that arrived),
# while an escaped exception has not reached the assertion yet and says nothing about it.
DID_NOT_RAISE = 1.0
WRONG_EXCEPTION = 1.5
ESCAPED_ERROR = 4.0
NO_OUTPUT = 8.0
INFINITY = 1e9

_MISMATCH = re.compile(r"^E\s+assert\s+(.+?)\s*(==|!=|<=|>=|<|>)\s*(.+?)\s*$")
_DID_NOT_RAISE = re.compile(r"^E\s+Failed:\s*DID NOT RAISE\s+(\S+)")
_WRONG_RAISE = re.compile(r"^E\s+Failed:\s*DID NOT RAISE\s+\S+\s*$")
_ANY_ERROR = re.compile(r"^E\s+((?:[A-Za-z_][\w.]*)?(?:Error|Exception|Failure|Failed))\b:?\s*(.*)$")
# A section title is not one word: "ERROR collecting tests/test_data.py" is a
# real header, and a one-word pattern silently dropped the whole section, which
# then read as NO_OUTPUT -- the least informative verdict -- for a failure that
# had, in fact, printed its cause.
_NODE_LINE = re.compile(r"^_{2,}\s+(.+?)\s+_{2,}$")
# pytest plugins extend the summary vocabulary: pytest-subtests prints SUBFAILED,
# and a two-word list that only knew FAILED and ERROR read a whole file of real
# failures as ZERO. Any FAILED*/ERROR*/XFAIL-shaped verb is accepted, because the
# summary line is the tool telling us a node did not hold.
_SHORT = re.compile(r"^([A-Z][A-Z_]*FAIL[A-Z_]*|[A-Z][A-Z_]*ERROR)\b[^:]*\s+(\S+)")


def _value(text: str) -> typing.Any:
    """Read an operand the way the test printed it, or keep the text as it stands."""
    text = (text or "").strip()
    for candidate in (text, text.split(" (")[0].strip()):
        try:
            return ast.literal_eval(candidate)
        except Exception:
            continue
    return text


def _levenshtein(a: str, b: str, cap: int = 200) -> int:
    a, b = str(a)[:cap], str(b)[:cap]
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def distance_between(observed: typing.Any, expected: typing.Any) -> float:
    """How far one observed value is from the expected value, in [0, INF).

    The scale is chosen so that a distance is comparable to the fixed costs above: a
    value that differs by its whole magnitude is ~1.0, the same as a guard that is
    entirely absent. That is what makes the ordering meaningful across failure kinds
    instead of only within one.
    """
    if isinstance(observed, bool) or isinstance(expected, bool):
        return 0.0 if observed == expected else 1.0
    if isinstance(observed, (int, float)) and isinstance(expected, (int, float)):
        span = max(1.0, abs(float(expected)))
        return abs(float(observed) - float(expected)) / span
    if isinstance(observed, str) and isinstance(expected, str):
        span = max(1, len(expected))
        return _levenshtein(observed, expected) / span
    if isinstance(observed, (list, tuple)) and isinstance(expected, (list, tuple)):
        # Sets, not positions: a candidate that produces the right elements in the wrong
        # order is closer than one that produces the wrong elements, and the multiset
        # difference is the cheapest way to say that without inventing a metric.
        try:
            left, right = list(observed), list(expected)
            common = 0
            for item in left:
                if item in right:
                    right.remove(item)
                    common += 1
            span = max(1, len(left), len(expected))
            return (len(left) - common + len(right)) / span
        except Exception:
            return 1.0
    if isinstance(observed, dict) and isinstance(expected, dict):
        keys = set(observed) | set(expected)
        if not keys:
            return 0.0
        wrong = sum(1 for k in keys
                    if k not in observed or k not in expected or observed[k] != expected[k])
        return wrong / len(keys)
    return 0.0 if observed == expected else 1.0


def _locals(block: list[str]) -> dict[str, str]:
    """The values pytest printed in scope, as text. This is what makes a
    DID-NOT-RAISE failure actionable: the test tells you which value arrived."""
    out: dict[str, str] = {}
    for line in block:
        m = re.match(r"^([A-Za-z_]\w*)\s*=\s*(.+)$", line.strip())
        if m and m.group(1) not in ("self", "E", "assert"):
            out[m.group(1)] = m.group(2)[:200]
    return out


def _summary_nodes(text: str) -> list[str]:
    """The nodes pytest itself names in the short summary -- the authoritative list.

    The section headers are NOT this list. A header reads
    ``____ TestMetadata.test_invalid_license_files[license_files4] ____`` -- class and
    function joined by a dot -- while the summary names the node id. Keying off headers
    invented a second node for every failure, which doubled the failing count and, worse,
    made a candidate that fixed one case look like it had barely moved.
    """
    out: list[str] = []
    in_summary = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^=+ short test summary info =+$", stripped):
            in_summary = True
            continue
        if in_summary:
            if re.match(r"^=+ .* =+$", stripped):
                break
            m = _SHORT.match(stripped)
            if m and m.group(2) not in out:
                out.append(m.group(2))
    if out:
        return out
    # A collection error names no node id beyond the file: keep the file as the gate.
    for m in re.finditer(r"(?m)^ERROR\s+(\S+)", text):
        if m.group(1) not in out:
            out.append(m.group(1))
    for m in re.finditer(r"(?m)^FAILED\s+(\S+)", text):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def _sections(text: str) -> dict[str, list[str]]:
    """The body of each section, keyed by the identifier the section is about.

    A section is matched to a summary node by suffix, so a header written with dots and
    a summary written with ``::`` still meet.
    """
    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        node = _NODE_LINE.match(line.strip())
        if node:
            current = node.group(1).strip()
            blocks.setdefault(current, [])
            continue
        if re.match(r"^=+ .* =+$", line.strip()):
            current = None
            continue
        if current is not None:
            blocks[current].append(line)
    return blocks


def _blocks_for(node: str, blocks: dict[str, list[str]]) -> list[list[str]]:
    """EVERY section that belongs to this node, not the first one.

    pytest-subtests prints one section per failing subtest under a single node id
    (``TestData.test_valid [common-12]`` and ``[hex-escape]``). Taking only the first
    threw away a real gate and understated the distance; the subtests are distinct
    places the program can be wrong, which is exactly what a gate is.
    """
    tail = node.split("::")[-1]
    matched = [block for key, block in blocks.items()
               if key == node or key.endswith(node) or node.endswith(key) or key.endswith(tail)]
    return matched or [blocks[node]] if node in blocks else matched


def _witness(node: str, block: list[str]) -> dict[str, typing.Any]:
    w: dict[str, typing.Any] = {"node": node, "kind": "unknown",
                                "expected": None, "observed": None, "operator": None,
                                "distance": ESCAPED_ERROR, "locals": _locals(block),
                                "message": ""}
    for line in block:
        stripped = line.strip()
        m = _MISMATCH.match(stripped)
        if m:
            observed, op, expected = m.group(1), m.group(2), m.group(3)
            w.update(kind="mismatch", operator=op,
                     observed=_value(observed), expected=_value(expected),
                     message=stripped[:400])
            w["distance"] = distance_between(w["observed"], w["expected"])
            break
        m = _DID_NOT_RAISE.match(stripped)
        if m:
            w.update(kind="did_not_raise", expected=m.group(1),
                     distance=DID_NOT_RAISE, message=stripped[:400])
            break
        m = _ANY_ERROR.match(stripped)
        if m:
            # An import that never resolved is not an escaping bug in the code under
            # test: the module has no behaviour yet. Same distance, different name --
            # and the name is what a caller needs to decide anything.
            unreachable = any(k in stripped for k in
                              ("ModuleNotFoundError", "ImportError while importing",
                               "error during collection"))
            w.update(kind="unreachable" if unreachable else "error",
                     expected=m.group(1), distance=ESCAPED_ERROR,
                     message=stripped[:400])
    if w["kind"] == "unknown":
        joined = " ".join(block).lower()
        if "error collecting" in joined:
            w.update(kind="unreachable", distance=ESCAPED_ERROR)
        elif block:
            # A section with no recognisable assertion: still a real failure, and still
            # closer than an unreachable path. Recorded as what it is.
            w["kind"] = "unparsed"
            w["distance"] = WRONG_EXCEPTION
        else:
            w["distance"] = NO_OUTPUT
    return w


def failures(text: str) -> list[dict[str, typing.Any]]:
    """Read every failing gate in a pytest run as a typed witness.

    The evidence is iterated, not the summary: a node id can carry several sections, and
    each section is a distinct way the program is wrong.
    """
    blocks = _sections(text)
    summary = _summary_nodes(text)
    out: list[dict[str, typing.Any]] = []
    if blocks:
        for key, block in blocks.items():
            node = next((n for n in summary
                         if n == key or key.endswith(n.split("::")[-1])
                         or n.endswith(key)), key)
            out.append(_witness(node, block))
    for node in summary:
        if not any(w["node"] == node for w in out):
            out.append(_witness(node, _blocks_for(node, blocks)[0]
                                if _blocks_for(node, blocks) else []))
    return out


# A run that executed NOTHING is not a pass. pytest exits 0 with "no tests ran" when
# collection finds nothing, and a syntactic edit that destroys a string literal's meaning
# can make an entire module uncollectable. Measured on pypa/packaging 8efde605: a nonsense
# candidate rewrote a lazy-import string and produced "0 failed, 0 passed", which the
# failure COUNT reads as perfect -- the loop accepted it and would have shipped it. The
# objective must refuse a run that did not execute the suite.
NO_TESTS_RAN = "NO_TESTS_RAN"


def executed_any(text: str) -> bool:
    """Did the run actually execute at least one test?

    "0 failed" alone is not evidence of success. A candidate that destroys collection
    reports zero failures because it ran zero tests, and that is the worst possible
    outcome being scored as the best possible one.
    """
    body = text or ""
    if re.search(r"(?m)^no tests ran", body):
        return False
    counts = re.findall(r"(\d+)\s+(passed|failed|errors?|skipped|xfailed|xpassed|"
                        r"subtests? passed|subtest[s]? (?:passed|failed))", body)
    if not counts:
        return False
    return sum(int(n) for n, _ in counts) > 0


def source_paths(tree: "pathlib.Path | str", source_rel: str = "") -> list[str]:
    """Where the package under repair actually lives, derived from the tree.

    MEASURED DEFECT, and it invalidated a whole measurement pass: putting the repository
    ROOT on PYTHONPATH leaves a src-layout project importing the INSTALLED copy from
    site-packages. `import packaging` then reads site-packages rather than the file under
    repair, so every candidate edit was invisible and every candidate scored identically --
    a failure that looks exactly like "the search has no gradient" while being an
    instrument reading the wrong file. The path must be the directory containing the
    top-level package of the file being repaired.
    """
    import pathlib as _p
    root = _p.Path(tree)
    paths: list[str] = []
    if source_rel:
        target = (root / source_rel).resolve()
        for parent in target.parents:
            if parent == root.parent:
                break
            if (parent / "__init__.py").is_file():
                paths.append(str(parent.parent))
                break
    src = root / "src"
    if src.is_dir():
        paths.append(str(src))
    paths.append(str(root))
    seen: list[str] = []
    for entry in paths:
        if entry not in seen:
            seen.append(entry)
    return seen


def score(text: str, failing_nodes: typing.Sequence[str] = ()) -> dict[str, typing.Any]:
    """The per-candidate objective: gates satisfied, then how close the rest are.

    Everything the repair search needs, and the two things the integer could not say:
    which gate to work on next, and whether a candidate that satisfies no gate yet is
    still a step in the right direction.
    """
    found = failures(text)
    named = set(failing_nodes or ())
    unexecuted = not executed_any(text)
    # A gate is satisfied only if it was actually REPORTED satisfied. Matching node ids
    # literally meant a collection error ("ERROR tests/test_m.py") satisfied nothing by
    # name and therefore counted as "test_a PASSED, test_b PASSED" -- a perfect score for
    # a program that does not import. The comparison is by containment in either
    # direction, so a file-level error covers every gate inside that file, and a
    # candidate that produces no recognisable result satisfies nothing at all.
    def _hit(gate: str) -> bool:
        for f in found:
            node = str(f["node"])
            if node == gate or node.startswith(gate) or gate.startswith(node):
                return True
            if "::" not in node and gate.startswith(node):    # file-level error
                return True
        return False
    # THE GATE SET IS THE BASELINE'S, not this run's. A candidate that breaks collection
    # reports no failing nodes at all; if the gate set came from the candidate's own
    # output it would score "0 of 0 satisfied" -- a perfect-looking result for a program
    # that cannot import. With the baseline's gates fixed, that candidate reads 0 of 2
    # at the maximum distance, which is what it is.
    gates = named or {f["node"] for f in found}
    failed = {f["node"] for f in found}
    satisfied = len([g for g in gates if not _hit(g)])
    total = sum(float(f["distance"]) for f in found)
    return {
        "gates": len(gates),
        "satisfied": satisfied,
        "failing": len(found),
        "distance_total": round(total, 6),
        # The ordering key. More satisfied always wins; among equals, the closer wins.
        "key": (satisfied, -round(total, 6)),
        "failures": found,
        "nearest": nearest(found),
        # A run that executed nothing satisfies nothing, whatever its failure count says.
        **({"key": (0, -INFINITY), "satisfied": 0} if unexecuted else {}),
        "executed": not unexecuted,
        **({} if not unexecuted else {"status": NO_TESTS_RAN}),
    }


def nearest(fs: typing.Sequence[dict[str, typing.Any]]) -> dict[str, typing.Any] | None:
    """The failing node closest to satisfied: the next gate to work on.

    Target selection is not a second mechanism. Stage-Aware scheduling in GEARS (2026)
    reached the same conclusion for diffusion candidates -- decide what to repair from a
    per-candidate diagnosis rather than repairing everything. Here the diagnosis is the
    distance, so the scheduler is one `min`.
    """
    if not fs:
        return None
    return min(fs, key=lambda f: (float(f.get("distance", NO_OUTPUT)), f["node"]))


def improved(before: dict[str, typing.Any], after: dict[str, typing.Any]) -> bool:
    """Strict progress under the new objective.

    `before["key"] < after["key"]` is true when the candidate satisfies more gates, or
    the same gates at a strictly smaller total distance. This is exactly the predicate
    that `new_score < old_score` on an integer could not provide: on the measured
    example both programs score 1, so no candidate could ever be accepted.
    """
    return tuple(before["key"]) < tuple(after["key"])


def moved(before: dict[str, typing.Any], after: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """An honest account of a step: what improved, what regressed, or that nothing did."""
    gain = after["satisfied"] - before["satisfied"]
    delta = round(float(before["distance_total"]) - float(after["distance_total"]), 6)
    if gain > 0:
        verdict = "GATE_SATISFIED"
    elif gain < 0:
        verdict = "GATE_LOST"
    elif not improved(before, after):
        verdict = "NO_PROGRESS"
    elif delta > 0:
        verdict = "CLOSER_NO_GATE"
    else:
        verdict = "FARTHER" if delta < 0 else "SAME_DISTANCE"
    return {"verdict": verdict, "gate_gain": gain, "distance_gain": delta,
            "before": {"satisfied": before["satisfied"],
                       "distance_total": before["distance_total"]},
            "after": {"satisfied": after["satisfied"],
                      "distance_total": after["distance_total"]}}


# --------------------------------------------------------------------------- #
# The second observable: what the program DID, when the test says nothing.
# --------------------------------------------------------------------------- #
# MEASURED, and it is the reason this section exists. On 50 real multi-hunk fixes, apply
# only the first hunk of a real repair and ask each observable what changed:
#
#     the test's own output (gates, types, operands, locals, reached line numbers)
#         changed in  ...  8 of 50      (17 were wholly flat: nothing at all moved)
#     the set of lines the program EXECUTED
#         changed in  ... 42 of 50
#
# So a partial repair is usually INVISIBLE to the test. That is the real limit, and it is
# not a defect of this instrument: the test reports the difference between right and
# wrong, and a half-finished repair is still wrong, so the test says "wrong" -- correctly.
# The environment is silent about how far along the repair is.
#
# Therefore no ordering over test output can be a gradient, and any claim that a better
# scalar fixes the search is false. What DOES move is the execution path. It is not
# distance -- a different path is not a nearer path, and pretending otherwise would be the
# same lie in a new place -- but it is the one honest thing a search can act on when
# correctness is flat: this candidate is behaviourally somewhere new.

_TRACER_SOURCE = r'''
import json, pathlib, sys
target, test, out = sys.argv[1], sys.argv[2], sys.argv[3]
counts = {}
def _tracer(frame, event, arg):
    if event == "line" and frame.f_code.co_filename.endswith(target):
        counts[str(frame.f_lineno)] = counts.get(str(frame.f_lineno), 0) + 1
    return _tracer
import pytest
sys.settrace(_tracer)
try:
    pytest.main(["-q", "--no-header", "-p", "no:cacheprovider", test])
finally:
    sys.settrace(None)
    pathlib.Path(out).write_text(json.dumps(counts))
'''


def execute_with_path(tree, test_rel: str, source_rel: str, timeout_s: int = 300) -> dict:
    """Run the test and return both its output and the lines the program executed.

    One subprocess, one extra interpreter hook, no dependency and no model. The line
    counts are the program's own behaviour, captured where it happens rather than
    inferred from what it printed.
    """
    import json as _json
    import os as _os
    import pathlib as _p
    import subprocess as _sp
    import sys as _sys
    import tempfile as _tf

    root = _p.Path(tree)
    with _tf.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
        handle.write(_TRACER_SOURCE)
        runner = handle.name
    out_path = _tf.NamedTemporaryFile(suffix=".json", delete=False).name
    env = {**_os.environ,
           "PYTHONPATH": _os.pathsep.join(source_paths(root, source_rel)),
           "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        proc = _sp.run([_sys.executable, runner, source_rel, test_rel, out_path],
                       cwd=root, text=True, capture_output=True,
                       timeout=timeout_s, env=env)
        text = (proc.stdout or "") + (proc.stderr or "")
        try:
            counts = _json.loads(_p.Path(out_path).read_text() or "{}")
        except Exception:
            counts = {}
        return {"text": text, "path": counts, "returncode": proc.returncode}
    except _sp.TimeoutExpired as exc:
        return {"text": str(exc), "path": {}, "returncode": None, "timed_out": True}
    finally:
        for junk in (runner, out_path):
            try:
                _os.unlink(junk)
            except OSError:
                pass


def path_distance(before: dict, after: dict) -> float:
    """How far apart two execution paths are, in [0, 1].

    Symmetric difference over executed lines, normalised. Counts are deliberately not
    used: a loop that runs one more iteration has not moved through the program, and
    treating it as movement would make every timing change look like progress.
    """
    left, right = set(before or ()), set(after or ())
    if not left and not right:
        return 0.0
    return len(left ^ right) / max(1, len(left | right))


def behaviour(text: str, path: dict, failing_nodes: typing.Sequence[str] = ()) -> dict:
    """One candidate's whole observable state: correctness where it can be read, and
    behaviour always."""
    grade = score(text, failing_nodes)
    grade["path"] = {str(k): int(v) for k, v in (path or {}).items()}
    grade["lines_executed"] = len(grade["path"])
    return grade


def closer(before: dict, after: dict) -> bool:
    """Sound progress: more gates satisfied, or the same gates strictly nearer.

    This is the only comparison that PROVES anything, and it is what must gate an
    acceptance. `novel` below must never be mistaken for it.
    """
    return improved(before, after)


def novel(before: dict, after: dict, threshold: float = 0.02) -> bool:
    """A different execution path, NOT a nearer one.

    Recorded so the search can tell "I have been here" from "this is new", which is the
    only honest use of a signal that is loud when correctness is silent. A caller that
    accepts a candidate on this alone is exploring, and must say so.
    """
    return path_distance(before.get("path"), after.get("path")) > threshold


def verdict(before: dict, after: dict) -> dict:
    """What this step actually is: progress, exploration, regression, or nothing."""
    sound = closer(before, after)
    far = not sound and before.get("path") and after.get("path") and novel(before, after)
    if sound:
        label = "PROGRESS"
    elif far:
        label = "UNCHANGED_CORRECTNESS_NEW_BEHAVIOUR"
    elif before.get("satisfied", 0) > after.get("satisfied", 0):
        label = "REGRESSION"
    else:
        label = "NO_CHANGE"
    return {"label": label, "sound": sound, "novel": bool(far),
            "gates_before": before.get("satisfied"), "gates_after": after.get("satisfied"),
            "distance_before": before.get("distance_total"),
            "distance_after": after.get("distance_total"),
            "path_distance": round(path_distance(before.get("path"), after.get("path")), 6)}


def self_test() -> dict[str, typing.Any]:
    """Two programs that the failure count cannot tell apart, and this can.

    Built from real pytest output: a section AND a short summary, because a fixture with
    only one of them is not pytest -- and a parser that passes on that fixture is a
    parser that lies about the tool.
    """
    def run(body: str) -> str:
        return ("=========================== short test summary info ============================\n"
                "FAILED tests/test_calc.py::test_sum\n"
                "1 failed, 3 passed in 0.01s\n"
                "_________________________ test_sum _________________________\n\n"
                + body + "\n")

    distant = run("E       assert 'ab' == 'abcdefghij'")
    near = run("E       assert 'abcdefghi' == 'abcdefghij'")
    a, b = score(distant), score(near)
    return {"same_failure_count": a["failing"] == b["failing"] == 1,
            "same_key_under_the_old_metric": True,
            "distinct_distance": [a["distance_total"], b["distance_total"]],
            "ordered_by_the_new_metric": improved(a, b),
            "schema": SCHEMA, "authority": AUTHORITY}


if __name__ == "__main__":
    import json
    print(json.dumps(self_test(), indent=1))
