#!/usr/bin/env python3
"""A lesson is admitted by what it does to programs it was never taught on. Not by its own demo.

THE HOLE THIS CLOSES, MEASURED FIRST
------------------------------------
`VerifiedSkillStore.crystallize_code_fix` already has the strongest option this tree offered:
`oracle=` plus `probes=`, which runs `rule_generalization_probe_v1.probe_rule`. But the learn path
calls it with `victim_snippet=before_snippet` -- the taught program itself. That probe's own
docstring says so: with the taught victim it checks "that the fix reproduces itself -- the weaker
question".

Measured on this tree, 2026-11-13, one boundary lesson (`x <= 100` -> `x < 100`) taught with
`oracle` and four probes:

    crystallized: True        state: ACTIVE        oracle_probe: {"verdict": "HOLDS", "probes_checked": 4}
    unseen programs executed before persistence: 0

    then, against two programs it was never taught on, each with its OWN spec:
        strict spec, defect present   -> REPAIRED
        inclusive spec, already right  -> BROKE CORRECT CODE

So the store granted permanence on four executions of the demonstration and zero executions of
anything else. `probe_skill_on_victim` can find that break afterwards and invalidate the row -- the
tree already knows how to detect the harm. It looks after the skill is live. This module moves the
same execution BEFORE the write.

WHAT IT IS, AND WHAT IT DELIBERATELY IS NOT
-------------------------------------------
It is the admission gate shape the newest work converged on: a candidate lesson is a hypothesis
tested in temporary state on target-transfer, falsification and archived-regression probes before
anything is committed (FGSE, arXiv:2611.14326, 10 Nov 2026); a candidate edit is admitted only
inside a hard regression budget (GRASP, arXiv:2605.29668); a revision must be non-regressive on
replay evidence (Skill-V, arXiv:2610.11781). It reuses this tree's own anti-unifier, applier and
executor, so there is one notion of "fires" and one notion of "breaks" here rather than two.

It is NOT a verifier, NOT a capability, and it exposes no persistence surface. `ADMIT` means: on
the victims and probe points supplied, the lesson repaired at least one unseen defective program,
left at least one already-correct program it touched behaving correctly, and broke nothing. It
says nothing about programs nobody supplied. `whole_task_correctness_proved` stays False.

THE TWO TRAPS IT REFUSES TO FALL INTO
-------------------------------------
1. A DECLARED family is not evidence. The caller does not say "this victim is a falsification
   case". The baseline is EXECUTED against that victim's own oracle: if it disagrees, the defect is
   present; if it agrees, the program was already right. `skill_scope_acquisition_v1` records why
   this matters -- a crude, declared fact produced a plausible wrong scope that looked identified.
2. A rule that never fires is not a safe rule. `NOT_APPLICABLE` yields no observation at all. If no
   already-correct victim was ever touched, the verdict is `REFINE`, never `ADMIT`: a check whose
   success case is "I didn't look" is the failure this whole seam exists to remove.

TWO FURTHER COUNTEREXAMPLES CLOSED, 2026-11-13
---------------------------------------------
The expected answers are fixed from the ORIGINAL source before either execution. Re-running
an oracle on the edited source let the candidate change its own exam. Also, every previously
passing probe is protected, even inside an already-defective program: a new failure yields
REGRESSED and rejection, including on archived programs. Equal aggregate failure counts are
not evidence of non-regression.

Authority: NONE. Sandbox measurement over caller-supplied victims; no receipt, no capability.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SCHEMA = "PROJECT_BRAIN_LESSON_ADMISSION_GATE_V1"

ADMIT = "ADMIT"
REFINE = "REFINE"
REJECT = "REJECT"
REFUSED = "REFUSED"

#: What one victim's execution said. Only REPAIRED and PRESERVED are evidence for admission.
REPAIRED = "REPAIRED"
PRESERVED = "PRESERVED"
BROKEN = "BROKEN"
REGRESSED = "REGRESSED"
STILL_WRONG = "STILL_WRONG"
NOT_APPLICABLE = "NOT_APPLICABLE"
NOT_HELD_OUT = "NOT_HELD_OUT"
NO_PROBES = "NO_PROBES"
ORACLE_ERROR = "ORACLE_ERROR"
BASELINE_EXECUTION_ERROR = "BASELINE_EXECUTION_ERROR"

#: Derived by executing the baseline, never declared by the caller.
DEFECT_PRESENT = "DEFECT_PRESENT"
ALREADY_CORRECT = "ALREADY_CORRECT"
UNCLASSIFIED = "UNCLASSIFIED"

HELD_OUT = "HELD_OUT"
ARCHIVE = "ARCHIVE"

_BROKEN_OUTCOMES = frozenset({BROKEN, REGRESSED})
_MALFORMED_OUTCOMES = frozenset({NO_PROBES, ORACLE_ERROR, BASELINE_EXECUTION_ERROR})

Oracle = Callable[[str, Any], Any]


@dataclasses.dataclass(frozen=True)
class Victim:
    """A program the lesson was not taught on, with its own spec and points to check it at.

    `oracle(source, point)` states the value the CORRECT program produces. It is called once
    per point with the ORIGINAL source, before execution; both arms use those expectations.
    It is the caller's specification, not the program's opinion of itself, and this module
    cannot repair a wrong one. Inputs, oracle and programs must be trusted: the executor runs
    in-process, without isolation or a timeout. Probe points must be JSON-serializable and
    distinct so the evidence can be audited and repeated observations cannot inflate coverage.
    One-shot probe iterables are materialized once before either execution.
    """

    victim_id: str
    source: str
    oracle: Oracle
    probes: Sequence[Any] = ()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _point_key(point: Any) -> str:
    """Stable audit identity for one input, not its Python object identity."""
    return json.dumps(point, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def _prepare_victims(victims: Sequence[Victim]) -> tuple[list[Victim], str | None]:
    """Validate and snapshot evidence inputs before any program or oracle runs.

    Snapshot once, and refuse duplicate/unreadable evidence instead of letting
    exhausted iterables or relabeled observations become safety evidence.
    """
    prepared: list[Victim] = []
    ids: set[str] = set()
    evidence: set[tuple[str, int, tuple[str, ...]]] = set()
    for victim in victims:
        if not isinstance(victim, Victim):
            return [], "VICTIM_IS_NOT_A_VICTIM_RECORD"
        if not isinstance(victim.victim_id, str) or not victim.victim_id.strip():
            return [], "INVALID_VICTIM_ID"
        if not isinstance(victim.source, str):
            return [], f"UNREADABLE_VICTIM_SOURCE:{victim.victim_id}"
        if victim.victim_id in ids:
            return [], f"DUPLICATE_VICTIM_ID:{victim.victim_id}"
        if not callable(victim.oracle):
            return [], f"VICTIM_HAS_NO_ORACLE:{victim.victim_id}"
        try:
            points = tuple(victim.probes)
            keys = tuple(_point_key(p) for p in points)
        except Exception:
            return [], f"UNREADABLE_PROBE_POINTS:{victim.victim_id}"
        if len(set(keys)) != len(keys):
            return [], f"DUPLICATE_PROBE_POINT:{victim.victim_id}"
        # The same source under a DIFFERENT spec is a different observation.
        # The same source/spec/points under a new label or role is not new evidence.
        key = (_norm(victim.source), id(victim.oracle), tuple(sorted(keys)))
        if key in evidence:
            return [], f"DUPLICATE_EVIDENCE:{victim.victim_id}"
        ids.add(victim.victim_id)
        evidence.add(key)
        prepared.append(dataclasses.replace(victim, probes=points))
    return prepared, None


def _run(source: str, point: Any) -> tuple[bool, Any, str | None]:
    """(ran, value, error). In-process single-call runner; NOT a security/time sandbox."""
    from canonical.tools.rule_generalization_probe_v1 import run_snippet

    try:
        return True, run_snippet(source, (point,)), None
    except Exception as exc:  # a program that raises is a fact about the program, not a crash here
        return False, None, f"{type(exc).__name__}:{exc}"


def _check(source: str, probes: Sequence[Any], expected_values: Sequence[Any]) -> dict[str, Any]:
    """Execute against the same pre-edit expectations in both arms, never a new spec."""
    rows: list[dict[str, Any]] = []
    for point, expected in zip(probes, expected_values, strict=True):
        ran, actual, error = _run(source, point)
        if not ran:
            rows.append({"probe": point, "agrees": False, "execution_error": error})
            continue
        rows.append({"probe": point, "agrees": actual == expected, "actual": actual, "expected": expected})
    return {"outcome": None, "points": rows,
            "disagreements": sum(1 for r in rows if not r["agrees"]),
            "execution_errors": sum(1 for r in rows if r.get("execution_error"))}


def _evaluate_victim(
    victim: Victim,
    rule: Mapping[str, Any],
    *,
    before_snippet: str,
    after_snippet: str,
    role: str,
) -> dict[str, Any]:
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import apply_crystallized_code_rule

    probes = tuple(victim.probes)
    row: dict[str, Any] = {
        "victim_id": victim.victim_id,
        "role": role,
        "source_sha256": _sha(victim.source),
        "probe_count": len(probes),
        "baseline_probes_executed": 0,
        "candidate_probes_executed": 0,
        "family": UNCLASSIFIED,
    }
    if not row["probe_count"]:
        return {**row, "outcome": NO_PROBES, "reason": "NOTHING_WOULD_BE_EXECUTED"}
    if _norm(victim.source) in {_norm(before_snippet), _norm(after_snippet)}:
        return {**row, "outcome": NOT_HELD_OUT,
                "reason": "VICTIM_IS_THE_DEMONSTRATION", "counted_as_evidence": False}

    # The oracle may inspect source metadata. Give it only the original program,
    # once per point, BEFORE either execution; an edit cannot move its own goalposts.
    try:
        expected_values = tuple(victim.oracle(victim.source, point) for point in probes)
    except Exception as exc:
        return {**row, "outcome": ORACLE_ERROR, "reason": f"{type(exc).__name__}:{exc}"}
    baseline = _check(victim.source, probes, expected_values)
    row["baseline_probes_executed"] = len(baseline["points"])
    if baseline.get("execution_errors"):
        return {**row, "outcome": BASELINE_EXECUTION_ERROR,
                "reason": "VICTIM_DOES_NOT_RUN_BEFORE_THE_LESSON",
                "points": baseline["points"]}

    defective = baseline["disagreements"] > 0
    row["family"] = DEFECT_PRESENT if defective else ALREADY_CORRECT
    row["baseline_disagreements"] = baseline["disagreements"]

    edited = apply_crystallized_code_rule(victim.source, rule)
    if edited is None:
        return {**row, "outcome": NOT_APPLICABLE, "counted_as_evidence": False,
                "reason": "RULE_DOES_NOT_FIRE_ON_THIS_PROGRAM"}
    row["edited_sha256"] = _sha(edited)

    after = _check(edited, probes, expected_values)
    row["candidate_probes_executed"] = len(after["points"])
    row["after_disagreements"] = after["disagreements"]
    row["after_execution_errors"] = after.get("execution_errors", 0)
    row["points"] = after["points"]
    # A program with one old defect can still lose working behavior. Compare
    # pointwise: equal or lower total failure counts can conceal a new failure.
    regressed = [old["probe"] for old, new in zip(baseline["points"], after["points"], strict=True)
                 if old["agrees"] and not new["agrees"]]
    row["regressed_probes"] = regressed
    row["regressed_probe_count"] = len(regressed)
    if defective and regressed:
        return {**row, "outcome": REGRESSED, "counted_as_evidence": True,
                "reason": "LOST_PREVIOUSLY_PASSING_BEHAVIOUR"}

    if after["disagreements"] == 0:
        return {**row, "outcome": REPAIRED if defective else PRESERVED, "counted_as_evidence": True}
    if defective:
        return {**row, "outcome": STILL_WRONG, "counted_as_evidence": True,
                "reason": "FIRED_AND_DID_NOT_REPAIR"}
    return {**row, "outcome": BROKEN, "counted_as_evidence": True,
            "reason": "CHANGED_BEHAVIOUR_OF_A_PROGRAM_THAT_WAS_ALREADY_RIGHT"}


def evaluate(
    before_snippet: str,
    after_snippet: str,
    *,
    victims: Iterable[Victim],
    archive: Iterable[Victim] = (),
    rule: Mapping[str, Any] | None = None,
    language: str = "python",
) -> dict[str, Any]:
    """Run the candidate lesson on held-out programs and decide whether it may be persisted.

    The gate does not persist lessons: edits are in-memory strings and the caller owns
    persistence. Executed programs/oracles are trusted, in-process code and may have side
    effects; there is no security sandbox. `ADMIT` concerns only the supplied probes.
    """
    offered = list(victims)
    archived = list(archive)
    if rule is None:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import anti_unify_code_rule

        rule = anti_unify_code_rule(before_snippet, after_snippet, language=language)
    if not rule:
        return {"schema": SCHEMA, "verdict": REFUSED, "reason": "SNIPPET_PAIR_DID_NOT_GENERALIZE",
                "rows": [], "authority": "NONE", "whole_task_correctness_proved": False}
    if not offered and not archived:
        return {"schema": SCHEMA, "verdict": REFUSED, "reason": "NO_VICTIMS_OFFERED",
                "rows": [], "authority": "NONE", "whole_task_correctness_proved": False}
    prepared, error = _prepare_victims([*offered, *archived])
    if error is not None:
        return {"schema": SCHEMA, "verdict": REFUSED, "reason": error,
                "rows": [], "authority": "NONE", "whole_task_correctness_proved": False}
    offered = prepared[:len(offered)]
    archived = prepared[len(offered):]

    rows = [_evaluate_victim(v, rule, before_snippet=before_snippet, after_snippet=after_snippet,
                             role=HELD_OUT) for v in offered]
    rows += [_evaluate_victim(v, rule, before_snippet=before_snippet, after_snippet=after_snippet,
                              role=ARCHIVE) for v in archived]

    # Gain is bought on NEW held-out programs. The archive is a damage guard, not a source of
    # gain: a lesson that only re-repairs what an older lesson already repaired has shown nothing.
    fresh = [r for r in rows if r["role"] == HELD_OUT]
    old = [r for r in rows if r["role"] == ARCHIVE]
    counts = {
        "victims_offered": len(rows),
        "held_out": len(fresh),
        "archive": len(old),
        "not_held_out": sum(1 for r in rows if r["outcome"] == NOT_HELD_OUT),
        "not_applicable": sum(1 for r in rows if r["outcome"] == NOT_APPLICABLE),
        "repaired": sum(1 for r in fresh if r["outcome"] == REPAIRED),
        "preserved": sum(1 for r in fresh if r["outcome"] == PRESERVED),
        "broken": sum(1 for r in fresh if r["outcome"] == BROKEN),
        "regressed": sum(1 for r in fresh if r["outcome"] == REGRESSED),
        "still_wrong": sum(1 for r in fresh if r["outcome"] == STILL_WRONG),
        "archive_repaired": sum(1 for r in old if r["outcome"] == REPAIRED),
        "archive_preserved": sum(1 for r in old if r["outcome"] == PRESERVED),
        "archive_broken": sum(1 for r in old if r["outcome"] == BROKEN),
        "archive_regressed": sum(1 for r in old if r["outcome"] == REGRESSED),
        # Program evaluations at probe points, including a baseline that ran
        # before the rule failed to match. Not a count of distinct programs.
        "programs_executed": sum(int(r.get("baseline_probes_executed") or 0)
                                 + int(r.get("candidate_probes_executed") or 0)
                                 for r in rows),
    }
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "counts": counts,
        "rows": rows,
        "authority": "NONE",
        "whole_task_correctness_proved": False,
        "probe_bounded": True,
    }

    malformed = [r["victim_id"] for r in rows if r["outcome"] in _MALFORMED_OUTCOMES]
    if malformed:
        return {**report, "verdict": REFUSED, "reason": "EVIDENCE_CANNOT_BE_READ:" + ",".join(malformed)}
    usable = [r for r in rows if r["outcome"] not in {NOT_HELD_OUT}]
    if not usable:
        return {**report, "verdict": REFUSED, "reason": "NO_HELD_OUT_VICTIM"}

    archived_broken = [r["victim_id"] for r in rows if r["role"] == ARCHIVE and r["outcome"] in _BROKEN_OUTCOMES]
    if archived_broken:
        return {**report, "verdict": REJECT, "reason": "ARCHIVE_REGRESSION:" + ",".join(archived_broken)}
    broken = [r["victim_id"] for r in rows if r["outcome"] == BROKEN]
    if broken:
        return {**report, "verdict": REJECT, "reason": "BROKE_CORRECT_PROGRAM:" + ",".join(broken)}
    regressed = [r["victim_id"] for r in rows if r["outcome"] == REGRESSED]
    if regressed:
        return {**report, "verdict": REJECT,
                "reason": "REGRESSED_PREVIOUSLY_PASSING_BEHAVIOUR:" + ",".join(regressed)}
    if counts["repaired"] == 0:
        return {**report, "verdict": REFINE, "reason": "NO_MEASURED_REPAIR_ON_AN_UNSEEN_PROGRAM"}
    if counts["preserved"] == 0:
        return {**report, "verdict": REFINE, "reason": "FALSIFICATION_UNEXERCISED"}
    return {**report, "verdict": ADMIT, "reason": None}


def record_for_store(report: Mapping[str, Any]) -> dict[str, Any]:
    """The audit row a caller may keep beside a persisted rule. Sources are hashed, not copied."""
    return {
        "schema": SCHEMA,
        "verdict": report.get("verdict"),
        "reason": report.get("reason"),
        "counts": dict(report.get("counts") or {}),
        "victims": [{"victim_id": r["victim_id"], "role": r["role"], "family": r["family"],
                     "outcome": r["outcome"], "source_sha256": r["source_sha256"],
                     "probe_count": r.get("probe_count", 0),
                     "baseline_probes_executed": r.get("baseline_probes_executed", 0),
                     "candidate_probes_executed": r.get("candidate_probes_executed", 0),
                     "regressed_probe_count": r.get("regressed_probe_count", 0)}
                    for r in report.get("rows") or []],
        "whole_task_correctness_proved": False,
        "authority": "NONE",
    }


UNGATED_RECORD = {
    "schema": SCHEMA,
    "verdict": "UNGATED",
    "reason": "NO_HELD_OUT_VICTIMS_SUPPLIED_AT_ADMISSION",
    "counts": {"repaired": 0, "preserved": 0, "broken": 0, "programs_executed": 0},
    "whole_task_correctness_proved": False,
    "authority": "NONE",
}


# ---------------------------------------------------------------------------
# the concrete measurement: the same lesson, with and without the gate
# ---------------------------------------------------------------------------
BEFORE = "def classify(x):\n    return x <= 100\n"
AFTER = "def classify(x):\n    return x < 100\n"
POINTS = (0, 99, 100, 101)


def strict_spec(_source: str, point: Any) -> bool:
    """This program's contract: 'under 100' excludes 100."""
    return point < 100


def inclusive_spec(_source: str, point: Any) -> bool:
    """A different program's contract: 'at most 100' includes 100. `<=` is right here."""
    return point <= 100


def demonstration() -> dict[str, Any]:
    """One lesson, three victims: the harm is real and the gate can see it before the write."""
    unseen_defect = Victim("strict_bucket", "def bucket(z):\n    return z <= 100\n", strict_spec, POINTS)
    already_right = Victim("inclusive_cap", "def cap(n):\n    return n <= 100\n", inclusive_spec, POINTS)
    untouched = Victim("no_boundary", "def twice(v):\n    return v * 2\n", lambda _s, p: p * 2, POINTS)

    harmful = evaluate(BEFORE, AFTER, victims=[unseen_defect, already_right])
    unexercised = evaluate(BEFORE, AFTER, victims=[unseen_defect, untouched])
    demo_only = evaluate(BEFORE, AFTER, victims=[Victim("the_demo", BEFORE, strict_spec, POINTS)])
    return {
        "schema": SCHEMA,
        "harmful_lesson": harmful,
        "falsification_never_touched": unexercised,
        "demonstration_is_not_a_victim": demo_only,
        "authority": "NONE",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the admission gate on one boundary lesson.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    out = demonstration()
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        for name in ("harmful_lesson", "falsification_never_touched", "demonstration_is_not_a_victim"):
            rep = out[name]
            print(f"{name}: {rep['verdict']} ({rep['reason']})")
            for row in rep["rows"]:
                print(f"    {row['victim_id']}: {row['family']} -> {row['outcome']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
