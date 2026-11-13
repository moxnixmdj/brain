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

_BROKEN_OUTCOMES = frozenset({BROKEN})
_MALFORMED_OUTCOMES = frozenset({NO_PROBES, ORACLE_ERROR, BASELINE_EXECUTION_ERROR})

Oracle = Callable[[str, Any], Any]


@dataclasses.dataclass(frozen=True)
class Victim:
    """A program the lesson was not taught on, with its own spec and points to check it at.

    `oracle(source, point)` states the value the CORRECT program produces. It is the caller's
    specification, not the program's opinion of itself, and this module cannot repair a wrong one.
    """

    victim_id: str
    source: str
    oracle: Oracle
    probes: Sequence[Any] = ()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _run(source: str, point: Any) -> tuple[bool, Any, str | None]:
    """(ran, value, error). Executes the tree's own bounded single-call runner."""
    from canonical.tools.rule_generalization_probe_v1 import run_snippet

    try:
        return True, run_snippet(source, (point,)), None
    except Exception as exc:  # a program that raises is a fact about the program, not a crash here
        return False, None, f"{type(exc).__name__}:{exc}"


def _check(source: str, oracle: Oracle, probes: Sequence[Any]) -> dict[str, Any]:
    """Execute `source` at every point against the victim's own spec."""
    rows: list[dict[str, Any]] = []
    for point in probes:
        try:
            expected = oracle(source, point)
        except Exception as exc:
            return {"outcome": ORACLE_ERROR, "error": f"{type(exc).__name__}:{exc}", "points": rows}
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

    row: dict[str, Any] = {
        "victim_id": victim.victim_id,
        "role": role,
        "source_sha256": _sha(victim.source),
        "probe_count": len(tuple(victim.probes)),
        "family": UNCLASSIFIED,
    }
    if not row["probe_count"]:
        return {**row, "outcome": NO_PROBES, "reason": "NOTHING_WOULD_BE_EXECUTED"}
    if _norm(victim.source) in {_norm(before_snippet), _norm(after_snippet)}:
        return {**row, "outcome": NOT_HELD_OUT,
                "reason": "VICTIM_IS_THE_DEMONSTRATION", "counted_as_evidence": False}

    baseline = _check(victim.source, victim.oracle, victim.probes)
    if baseline["outcome"] == ORACLE_ERROR:
        return {**row, "outcome": ORACLE_ERROR, "reason": baseline["error"]}
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

    after = _check(edited, victim.oracle, victim.probes)
    if after["outcome"] == ORACLE_ERROR:
        return {**row, "outcome": ORACLE_ERROR, "reason": after["outcome"] + ":" + str(after["error"])}
    row["after_disagreements"] = after["disagreements"]
    row["after_execution_errors"] = after.get("execution_errors", 0)
    row["points"] = after["points"]

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

    Nothing is written anywhere: the lesson is applied to in-memory strings only. The caller owns
    persistence, and `ADMIT` is a statement about the supplied victims and probe points.
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
    for victim in [*offered, *archived]:
        if not isinstance(victim, Victim):
            return {"schema": SCHEMA, "verdict": REFUSED, "reason": "VICTIM_IS_NOT_A_VICTIM_RECORD",
                    "rows": [], "authority": "NONE", "whole_task_correctness_proved": False}
        if not callable(victim.oracle):
            return {"schema": SCHEMA, "verdict": REFUSED,
                    "reason": f"VICTIM_HAS_NO_ORACLE:{victim.victim_id}",
                    "rows": [], "authority": "NONE", "whole_task_correctness_proved": False}

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
        "still_wrong": sum(1 for r in fresh if r["outcome"] == STILL_WRONG),
        "archive_repaired": sum(1 for r in old if r["outcome"] == REPAIRED),
        "archive_preserved": sum(1 for r in old if r["outcome"] == PRESERVED),
        "archive_broken": sum(1 for r in old if r["outcome"] == BROKEN),
        "programs_executed": sum(int(r.get("probe_count") or 0) * 2 for r in rows
                                 if r["outcome"] not in _MALFORMED_OUTCOMES
                                 and r["outcome"] not in {NOT_HELD_OUT, NOT_APPLICABLE}),
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
    broken = [r["victim_id"] for r in rows if r["outcome"] in _BROKEN_OUTCOMES]
    if broken:
        return {**report, "verdict": REJECT, "reason": "BROKE_CORRECT_PROGRAM:" + ",".join(broken)}
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
                     "probe_count": r.get("probe_count", 0)}
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
