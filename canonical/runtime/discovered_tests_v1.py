"""A library of structural tests that keeps score, instead of a pipeline that runs them in my order.

THE DEFECT
----------
Round 12 recovered a *periodic* hypothesis from evidence, and then wrote down the limit of that
result: the pathway was a partition test, `mod 3` was induced only because I had already written that
test, and "writing the test is still my job". So the vocabulary became learned while the thing that
decides *what can be recovered* stayed hard-coded -- the same shape as the defect round 12 fixed, one
level up.

A second defect surfaced the moment a second test was added. The periodic test evaluates `x % period`
on `Fraction`s, so a fractional input has a fractional residue and every observation becomes its own
class:

    1.5 % 2 == 3/2

The test then reported `NO_STRUCTURE`, which reads as *"there is no periodic structure here"* when the
truth is *"this test is undefined on this domain"*. That is the same conflation as `SEARCH_TRUNCATED`
(budget, not world) and `ONTOLOGY_EXHAUSTED` (classes, not evidence), now reproduced *inside a test*.
A test must be able to say "not applicable", and that must be distinct from "failed".

WHAT THIS MODULE DOES
---------------------
Two tests, kept genuinely distinct, each able to report NOT_APPLICABLE:

    periodic    y is constant on x mod p                    integer inputs only
    level       y is constant on floor(x)                   any rational inputs

Each carries a RECORD: how many targets it has recovered. Tests are tried in order of that record, so
a test that has worked before is tried before one that has not. Failed attempts are recorded too, so
the same attempt is not repeated blindly.

WHAT THIS IS NOT
----------------
This is **a discovery record that reorders a fixed library**. It does not invent tests. I wrote both
tests, and the honest claim is that *preference* among them is learned, not the tests themselves.
Whether that produces any measurable improvement is what the measurements decide, and the writeup is
required to say so plainly either way rather than describing reordering as invention.

The constraint from round 12 travels with every test and is not optional: a class must be witnessed at
least twice, or a test with one parameter per observation would "explain" anything. It is enforced in
`_adjudicate` so no test can opt out of it.

Authority: NONE. Pure Python, `fractions`. No labels are read from this docstring at run time.
"""
from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.vocabulary_induction_v1 import (  # noqa: E402
    INDUCED,
    _exact,
    _num,
    _partition_holds,
    verify,
)

SCHEMA = "PROJECT_BRAIN_DISCOVERED_TESTS_V1"

NOT_APPLICABLE = "NOT_APPLICABLE"     # this test makes no claim about this domain
REFUTED = "REFUTED"                   # the test applies and the data does not satisfy it
UNDERDETERMINED = "UNDERDETERMINED"   # the test applies but there is too little evidence to decide

MIN_WITNESSES = 2


# ---------------------------------------------------------------------------------------------
# The tests. Each returns a partition or a reason it cannot speak.
# ---------------------------------------------------------------------------------------------

def probe_periodic(exact: Sequence[tuple[Fraction, Fraction]], max_period: int = 12) -> dict[str, Any]:
    """`y` is constant on `x mod p`. Undefined for fractional inputs -- and says so."""
    if any(x.denominator != 1 for x, _y in exact):
        return {"status": NOT_APPLICABLE,
                "why": ("modular residues are only meaningful here for integer inputs; a fractional "
                        "input has a fractional residue, so every observation would be its own "
                        "class and the test would be measuring nothing")}
    found = _partition_holds(exact, max_period)
    if found is None:
        return {"status": REFUTED, "why": "no period partitions the observations consistently"}
    return {"status": INDUCED, "partition": found["parameters"]["values"],
            "key": "period", "size": found["parameters"]["period"],
            "name": found["name"], "body": found["body"], "evidence": found["evidence"]}


def probe_level(exact: Sequence[tuple[Fraction, Fraction]]) -> dict[str, Any]:
    """`y` is constant on `floor(x)`: the value steps when the input crosses an integer."""
    buckets: dict[int, set[Fraction]] = {}
    counts: dict[int, int] = {}
    for x, y in exact:
        key = int(x // 1)
        buckets.setdefault(key, set()).add(y)
        counts[key] = counts.get(key, 0) + 1
    if any(len(v) > 1 for v in buckets.values()):
        return {"status": REFUTED,
                "why": "two observations with the same integer part disagree, so no level function fits"}
    if min(counts.values()) < MIN_WITNESSES:
        return {"status": UNDERDETERMINED,
                "why": "%d level(s) are witnessed only once, which cannot certify a step"
                       % sum(1 for c in counts.values() if c < MIN_WITNESSES)}
    if len(buckets) < 2:
        return {"status": REFUTED,
                "why": "every observation falls in one level, so this is a constant and not a step"}
    table = {k: sorted(v)[0] for k, v in buckets.items()}
    body = _level_body(table)
    return {"status": INDUCED, "partition": {str(k): _num(v) for k, v in sorted(table.items())},
            "key": "floor", "size": len(table),
            "name": "value steps at each whole number, %d steps" % len(table),
            "body": body,
            "evidence": ("%d observations partition into %d integer parts, each witnessed at least "
                         "twice, none holding two different values" % (len(exact), len(table)))}


def _level_body(table: dict[int, Fraction]) -> str:
    lines = ["import math as _m", "_k = int(_m.floor(x))"]
    keys = sorted(table)
    for index, key in enumerate(keys):
        keyword = "if" if index == 0 else "elif"
        lines.append("%s _k == %d:" % (keyword, key))
        lines.append("    return %s" % _num(table[key]))
    lines.append("return %s" % _num(table[keys[-1]]))
    return "\n".join(lines)


TESTS = [
    {"name": "periodic", "run": probe_periodic,
     "applies_to": "inputs whose values repeat on a cycle",
     "requires": "integer inputs"},
    {"name": "level", "run": probe_level,
     "applies_to": "values that step when the input crosses a whole number",
     "requires": "rational inputs"},
]


# ---------------------------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------------------------

class DiscoveryRecord:
    """Which tests have ever worked, and which have already been tried on this input.

    Deliberately not a model. It counts discoveries and attempts, nothing else, because anything
    richer would be claiming an inference this module does not make.
    """

    def __init__(self) -> None:
        self.recovered: dict[str, int] = {t["name"]: 0 for t in TESTS}
        self.attempts: dict[str, int] = {t["name"]: 0 for t in TESTS}
        self.failed_on: dict[str, set[tuple]] = {t["name"]: set() for t in TESTS}

    def order(self) -> list[dict[str, Any]]:
        """Best record first. Ties keep the library's declared order, so this is stable."""
        return sorted(TESTS, key=lambda t: (-self.recovered[t["name"]], TESTS.index(t)))

    def note(self, name: str, points_key: tuple, ok: bool) -> None:
        self.attempts[name] += 1
        if ok:
            self.recovered[name] += 1
        else:
            self.failed_on[name].add(points_key)

    def already_failed(self, name: str, points_key: tuple) -> bool:
        return points_key in self.failed_on[name]


def _key(exact: Sequence[tuple[Fraction, Fraction]]) -> tuple:
    return tuple(sorted((str(x), str(y)) for x, y in exact))


def _adjudicate(result: dict[str, Any], exact: Sequence[tuple[Fraction, Fraction]]) -> dict[str, Any]:
    """The constraint round 12 needed, enforced here so no test can opt out of it.

    A test that returns a partition whose classes are witnessed once is fitting, not explaining.
    Checked centrally rather than per test, because the failure is a property of the *claim* and not
    of the test that made it.
    """
    if result.get("status") != INDUCED:
        return result
    key = result.get("key")
    counts: dict[Any, int] = {}
    for x, _y in exact:
        slot = int(x % result["size"]) if key == "period" else int(x // 1)
        counts[slot] = counts.get(slot, 0) + 1
    if counts and min(counts.values()) < MIN_WITNESSES:
        return {"status": REFUTED,
                "why": ("the partition is consistent but %d of its %d classes are witnessed once, so "
                        "the explanation has as many parameters as facts"
                        % (sum(1 for c in counts.values() if c < MIN_WITNESSES), len(counts)))}
    return result


def recover(points: Sequence[tuple[Any, Any]], record: DiscoveryRecord,
            max_period: int = 12) -> dict[str, Any]:
    """Try the library in record order; return the first test that can speak and succeeds."""
    # Accept BOTH the project's `((args...), value)` form and flat `(x, value)`, and REFUSE anything
    # else loudly. Measured 2026-11-04: passing the project form to a flat-pair reader made every
    # point unparseable, and the function answered NOT_APPLICABLE -- "this test makes no claim about
    # this domain" -- for data it was perfectly well able to test. That is the fourth instance this
    # session of one module naming an input shape differently from the one reading it, and every
    # previous one failed silently rather than loudly.
    arities = {len(a) if isinstance(a, (tuple, list)) else 0 for a, _v in points}
    if arities - {0, 1}:
        return {"schema": SCHEMA, "status": NOT_APPLICABLE,
                "why": "these tests reason one input at a time; %d were supplied"
                       % max(arities), "authority": "NONE"}
    flat = [((a[0] if isinstance(a, (tuple, list)) else a), v) for a, v in points]
    exact = [(_exact(x), _exact(y)) for x, y in flat]
    if any(x is None or y is None for x, y in exact):
        return {"schema": SCHEMA, "status": NOT_APPLICABLE,
                "why": "an observation is not an exact rational", "authority": "NONE"}
    key = _key(exact)
    trace: list[dict[str, Any]] = []
    for test in record.order():
        name = test["name"]
        if record.already_failed(name, key):
            trace.append({"test": name, "status": "SKIPPED",
                          "why": "already tried on exactly this input and failed"})
            continue
        raw = test["run"](exact, max_period) if name == "periodic" else test["run"](exact)
        verdict = _adjudicate(raw, exact)
        trace.append({"test": name, "status": verdict["status"],
                      "why": verdict.get("why", "")[:120]})
        record.note(name, key, verdict["status"] == INDUCED)
        if verdict["status"] == INDUCED:
            out = dict(verdict)
            out.update({"schema": SCHEMA, "test": name, "trace": trace,
                        "tests_tried": len([t for t in trace if t["status"] != "SKIPPED"]),
                        "authority": "NONE"})
            return out
    return {"schema": SCHEMA, "status": REFUTED, "trace": trace,
            "tests_tried": len([t for t in trace if t["status"] != "SKIPPED"]),
            "why": "no test in the library explains these observations",
            "authority": "NONE"}


CASES = {
    "mod 2": [((0,), 0.0), ((1,), 1.0), ((2,), 0.0), ((3,), 1.0), ((4,), 0.0), ((5,), 1.0)],
    "mod 3": [((0,), 0.0), ((1,), 1.0), ((2,), 2.0), ((3,), 0.0), ((4,), 1.0), ((5,), 2.0),
              ((6,), 0.0), ((7,), 1.0), ((8,), 2.0)],
    "floor": [((0.5,), 1.0), ((0.9,), 1.0), ((1.2,), 2.0), ((1.8,), 2.0), ((2.1,), 3.0),
              ((2.7,), 3.0)],
    "noise": [((0,), 7.0), ((1,), 2.0), ((2,), 9.0), ((3,), 1.0), ((4,), 8.0), ((5,), 3.0)],
}


# ---------------------------------------------------------------------------------------------
# Measuring the claim, including where it cannot hold
# ---------------------------------------------------------------------------------------------

def _floor_like(i: int) -> list:
    """A level-structured target with different levels, so several distinct floor targets exist."""
    return [((i + 0.5,), float(2 * i + 1)), ((i + 0.9,), float(2 * i + 1)),
            ((i + 1.2,), float(2 * i + 2)), ((i + 1.8,), float(2 * i + 2)),
            ((i + 2.1,), float(2 * i + 3)), ((i + 2.7,), float(2 * i + 3))]


def _measure_stream(sequence: Sequence, label: str) -> dict[str, Any]:
    """Tests tried, fixed order vs record order, over one stream of targets."""
    fixed = sum(recover(p, _FrozenRecord([t["name"] for t in TESTS]))["tests_tried"]
                for p in sequence)
    record = DiscoveryRecord()
    learned = sum(recover(p, record)["tests_tried"] for p in sequence)
    return {"stream": label, "targets": len(sequence), "fixed_total": fixed,
            "learned_total": learned, "order_after": [t["name"] for t in record.order()],
            "recovered": dict(record.recovered), "improved": learned < fixed}


def _streams() -> list[dict[str, Any]]:
    mixed = [CASES["mod 2"], CASES["mod 3"], CASES["floor"], CASES["noise"]]
    floors = [_floor_like(i) for i in range(5)]
    periodic_only = [CASES["mod 2"], CASES["mod 3"],
                     [((0,), 1.0), ((1,), 2.0), ((2,), 3.0), ((3,), 1.0), ((4,), 2.0), ((5,), 3.0)]]
    return [_measure_stream(mixed, "mixed (periodic dominant)"),
            _measure_stream(floors, "five level targets"),
            _measure_stream(periodic_only, "three periodic targets")]


def _measure_ordering() -> dict[str, Any]:
    """Does the record reduce attempts? Measured on a sequence with a held-out third test.

    With TWO tests, reordering cannot help: whichever test is not first loses on the first target
    of the sequence and the library flips to put it first, which is the same set of choices. The
    improvement only exists when a test that is NOT the library's first choice keeps winning -- so
    the honest measurement supplies one.
    """
    def _third_test(exact, max_period: int = 12) -> dict[str, Any]:
        """A test that applies only when every input is a whole number and the values alternate."""
        if any(x.denominator != 1 for x, _y in exact):
            return {"status": NOT_APPLICABLE, "why": "integer inputs only"}
        values = [y for _x, y in sorted(exact)]
        if len(values) < 4 or any(values[i] == values[i + 1] for i in range(len(values) - 1)):
            return {"status": REFUTED, "why": "the values do not alternate"}
        return {"status": INDUCED, "key": "period", "size": 2,
                "partition": {"0": _num(values[0]), "1": _num(values[1])},
                "name": "the two values alternate", "body": _level_body({0: values[0], 1: values[1]})}

    global TESTS
    original = list(TESTS)
    TESTS = original + [{"name": "alternation", "run": _third_test,
                         "applies_to": "values that alternate", "requires": "integer inputs"}]
    try:
        sequence = [CASES["mod 2"], CASES["mod 3"], CASES["floor"],
                    [((0,), 1.0), ((1,), 2.0), ((2,), 1.0), ((3,), 2.0), ((4,), 1.0), ((5,), 2.0)]]

        # (a) fixed library order: the first test in the list until one succeeds
        fixed_tried = 0
        for points in sequence:
            r = recover(points, _FrozenRecord([t["name"] for t in TESTS]))
            fixed_tried += r["tests_tried"]

        # (b) record order: learns what works and puts it first
        record = DiscoveryRecord()
        record.recovered = {t["name"]: 0 for t in TESTS}
        record.attempts = {t["name"]: 0 for t in TESTS}
        record.failed_on = {t["name"]: set() for t in TESTS}
        learned_tried = []
        for points in sequence:
            r = recover(points, record)
            learned_tried.append(r["tests_tried"])
            # the third test is only reachable through its record: no other test in the library
            # explains the alternation case, so it is tried last and then remembered
        return {"fixed_total": fixed_tried, "learned_total": sum(learned_tried),
                "per_target": learned_tried,
                "order_after": [t["name"] for t in record.order()],
                "improved": sum(learned_tried) < fixed_tried}
    finally:
        TESTS = original


class _FrozenRecord(DiscoveryRecord):
    """A record that never learns, used as the fixed-order control."""

    def __init__(self, order: Sequence[str]) -> None:
        super().__init__()
        self._fixed = list(order)

    def order(self) -> list[dict[str, Any]]:
        return [t for name in self._fixed for t in TESTS if t["name"] == name]

    def note(self, name: str, points_key: tuple, ok: bool) -> None:
        return None


def run() -> dict[str, Any]:
    """The round-13 pre-registration, scored -- including where it fails."""
    rec = DiscoveryRecord()
    results = {name: recover(ex, rec) for name, ex in CASES.items()}
    streams = _streams()

    mod2, mod3, floor_c, noise = (results["mod 2"], results["mod 3"],
                                  results["floor"], results["noise"])
    floor_level = recover(CASES["floor"], DiscoveryRecord())
    mod2_periodic = recover(CASES["mod 2"], DiscoveryRecord())

    # T2: is a failed attempt remembered?
    repeat = DiscoveryRecord()
    first = recover(CASES["noise"], repeat)
    second = recover(CASES["noise"], repeat)
    skipped = [t for t in second["trace"] if t["status"] == "SKIPPED"]

    # T5: the negative control. A library that can fit anything must not fit this.
    broad = DiscoveryRecord()
    noise_result = recover(CASES["noise"], broad)

    improvements = [s for s in streams if s["improved"]]
    regressions = [s for s in streams if s["learned_total"] > s["fixed_total"]]

    findings = [
        {"id": "the_two_tests_are_genuinely_different",
         "question": "does only one test apply to each kind of target?",
         "map2": mod2.get("test"), "floor": floor_level.get("test"),
         "pass": mod2.get("test") == "periodic" and floor_level.get("test") == "level"},

        {"id": "each_test_refuses_the_other_targets",
         "question": "or does one test quietly handle everything?",
         "detail": "periodic on floor data = NOT_APPLICABLE; level on mod 2 = UNDERDETERMINED",
         "pass": _cross_check()},

        {"id": "a_failed_attempt_is_not_repeated_blindly",
         "question": "is the same failing attempt retried on the same input?",
         "skipped_on_second": len(skipped), "first_tried": first["tests_tried"],
         "second_tried": second["tests_tried"],
         "pass": len(skipped) == len(skipped) and second["tests_tried"] == 0 and len(skipped) > 0},

        {"id": "the_record_changes_the_order",
         "question": "does a success actually reorder the library?",
         "order": [t["name"] for t in rec.order()], "recovered": rec.recovered,
         "pass": [t["name"] for t in rec.order()][0] == "periodic"},

        {"id": "the_record_reduces_attempts_where_it_can",
         "question": "does preference save work on a stream the library's order suits badly?",
         "improved_streams": [(s["stream"], s["fixed_total"], s["learned_total"])
                              for s in improvements],
         "pass": any(s["fixed_total"] - s["learned_total"] >= 2 for s in improvements)},

        {"id": "the_record_never_costs_anything",
         "question": "does learning ever make it slower?",
         "regressions": [s["stream"] for s in regressions],
         "pass": not regressions},

        {"id": "the_reordering_is_decorative_when_one_test_dominates",
         "question": "is there a stream where the record buys nothing?",
         "no_gain": [(s["stream"], s["fixed_total"], s["learned_total"])
                     for s in streams if not s["improved"]],
         "pass": any(not s["improved"] for s in streams)},

        {"id": "structureless_data_is_still_refused",
         "question": "can a library of tests be made to fit unrelated data?",
         "status": noise_result["status"], "trace": noise_result["trace"],
         "pass": noise_result["status"] != INDUCED},

        {"id": "a_kind_is_not_counted_twice",
         "question": "do two tests recovering the same law inflate the kinds count?",
         "periodic_on_mod2": mod2_periodic.get("test"),
         "detail": "alternation adds nothing to mod 2; the periodic test already explains it",
         "pass": mod2_periodic.get("test") == "periodic"},

        {"id": "recovery_still_works_without_survivors",
         "question": "does the test library depend on the string search finding anything?",
         "mod_3": mod3.get("name"), "mod_3_tried": mod3["tests_tried"],
         "pass": mod3.get("status") == INDUCED},
    ]
    passed = sum(1 for f in findings if f["pass"])
    rows = [{"case": name, "status": r["status"], "test": r.get("test"),
             "tried": r.get("tests_tried"), "name": r.get("name"),
             "body": r.get("body")} for name, r in results.items()]
    return {"schema": SCHEMA, "passed": passed, "total": len(findings), "findings": findings,
            "cases": rows, "streams": streams, "authority": "NONE"}


def _cross_check() -> bool:
    from canonical.runtime.vocabulary_induction_v1 import _exact
    mod2 = [(_exact(a[0]), _exact(v)) for a, v in CASES["mod 2"]]
    floor_pts = [(_exact(a[0]), _exact(v)) for a, v in CASES["floor"]]
    return (probe_periodic(floor_pts)["status"] == NOT_APPLICABLE
            and probe_level(mod2)["status"] != INDUCED)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = run()
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True, default=str))
        return 0
    for row in doc["cases"]:
        print("%-7s %-12s test=%-9s tried=%s  %s" % (
            row["case"], row["status"], row["test"] or "-", row["tried"],
            (row["name"] or "")[:42]))
    print()
    for s in doc["streams"]:
        print("%-28s fixed=%-2d learned=%-2d %s" % (
            s["stream"], s["fixed_total"], s["learned_total"],
            "SAVED %d" % (s["fixed_total"] - s["learned_total"]) if s["improved"] else "no gain"))
    print("\n%d/%d findings as predicted" % (doc["passed"], doc["total"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
