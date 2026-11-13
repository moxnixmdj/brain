#!/usr/bin/env python3
"""Is the experience we have accumulated a legal training set for weight-space learning?

Why this question comes before buying an optimizer
-------------------------------------------------
The owner's proposal is to convert token-space experience into permanent weight updates by
fine-tuning on our own execution traces. Three 2026 papers are the strongest public evidence
that this direction is real, and each of them states what its learning signal must be:

* ASCENT (arXiv:2610.05303, 2026-10-04) learns from "the executed trajectory with its
  verification result" and *skips the update when verification fails*. Its validity filter
  removes turns whose actions the environment did not execute. It therefore needs a
  per-episode verification bit, both outcome classes, and executed actions rather than a
  prose summary of what the agent meant to do.
* Experience Distillation (arXiv:2607.21051, 2026-07-23) queries an experience-conditioned
  teacher at every *recorded history prefix*. It therefore needs the recorded states, not
  just the final plan. The same paper reports that direct supervised fine-tuning on the
  collected experience recovers only 3.8% of the in-context gain, against at least 64.8%
  for the distillation objective: "fine-tune on the traces" is not one operation but many,
  and the naive one is measured to be nearly worthless.
* Agentic Test-Time Training (arXiv:2607.03441, 2026-07-03) shows that an update stream which
  replays the same text reinforces behaviour that already failed, and downweights tokens by
  their prior n-gram exposure. A store holding silent duplicates bakes that repetition into
  the training distribution before the optimizer ever sees it.

None of those requirements is about the optimizer. All of them are about the record. The
record is what this repository already owns, so it is the cheapest place to look first, and
the same five properties are what token-space reuse needs too. A row that cannot be trusted
as a training target cannot be trusted as a recalled plan either.

What this tool is and is not
----------------------------
It is a *necessary-not-sufficient* readiness screen over the durable, tracked experience
stores. Passing it does not show that weight training would work; failing it shows that the
corpus cannot yet be the learning signal those methods specify. It runs no model, spends
nothing, and writes no authority: ``AUTHORITY`` is NONE and ``truth.achieved`` stays false.

The screen has failure power by construction
-------------------------------------------
This repository has already been bitten by "a gate that rejects everything passes every
failure test". So the screen ships with one positive control that must satisfy all five
row requirements, and five ablations that each break exactly one requirement and must fail
exactly that one. `control_report()` recomputes them; the test suite pins them. A census
whose positive control fails is reported as INVALID, never as a finding about the corpus.

Frozen expectations are in `EXPECTED`, written before the corpus was audited.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_EXPERIENCE_CORPUS_TRAINING_READINESS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

#: Row-level requirements. Each is traceable to a published learning signal, not to taste.
REQUIREMENTS = (
    "verified_outcome",       # ASCENT: verification result gates the update
    "executed_trajectory",    # ASCENT validity filter / EPD recorded history prefixes
    "world_identity",         # rows from incompatible worlds teach contradictory dynamics
    "evidence_provenance",    # a wrong lesson must be findable and withdrawable
    "distinct_payload",       # aTTT: repeated update text reinforces what already failed
)

#: Written before the audit ran. The corpus is expected to fail; the controls must not.
EXPECTED = {
    "positive_control_satisfies_all_five": True,
    "each_ablation_fails_exactly_its_own_requirement": True,
    "no_live_store_is_fully_ready": True,
    "generalization_experiences_record_zero_failures": True,
}

_OUTCOMES = {
    "success": True, "failure": False, "failed": False, "reached": True,
    "pass": True, "fail": False, True: True, False: False,
}
_OBSERVATION_KEYS = ("observation", "state", "after", "obs", "result")
_PROVENANCE_KEYS = ("provenance", "ownership_receipt", "receipt", "taught_sources", "evidence_path")
_WORLD_KEYS = ("environment", "world", "env_id", "fingerprint")


def _is_executable_action(action: Any) -> bool:
    """An executed action, not a description of one.

    The repo's real action vocabularies are identifiers (``run_gzip``, ``copy_to_out``,
    ``+0``, ``inc``) or typed call objects (``{"type": "click", "index": 4}``). Prose such as
    ``"parse file with ast.parse()"`` is a narration: it names no callable and records no
    arguments, so a teacher cannot be queried at that prefix and a validity filter cannot
    ask whether the environment executed it.
    """
    if isinstance(action, Mapping):
        return bool(action.get("type") or action.get("op") or action.get("action"))
    return isinstance(action, str) and bool(action.strip()) and not any(c.isspace() for c in action.strip())


def _trajectory_is_executed(steps: Any) -> bool:
    if not isinstance(steps, (list, tuple)) or not steps:
        return False
    for step in steps:
        if not isinstance(step, Mapping):
            return False
        action = step.get("action", step.get("act"))
        if not _is_executable_action(action):
            return False
        if not any(k in step for k in _OBSERVATION_KEYS):
            return False
    return True


def _has_world_identity(row: Mapping[str, Any]) -> bool:
    if not any(row.get(k) for k in _WORLD_KEYS):
        return False
    # A carried transition model is only comparable under the identity that wrote it.
    if row.get("model") and not row.get("model_schema"):
        return False
    return True


def _has_provenance(row: Mapping[str, Any]) -> bool:
    for key in _PROVENANCE_KEYS:
        value = row.get(key)
        if value:
            return True
    prov = row.get("provenance")
    return bool(isinstance(prov, Mapping) and prov)


def _payload_key(store: str, row: Mapping[str, Any]) -> str:
    """The part of a row that would become a training target, canonicalised."""
    for fields in (
        ("task_description", "trajectory"),
        ("content",),
        ("sentence", "examples"),
        ("goal_skeleton", "abstract_steps"),
        ("fp_key", "goal_key", "plan"),
    ):
        if all(f in row for f in fields):
            return json.dumps({f: row[f] for f in fields}, sort_keys=True, default=str)
    return json.dumps(row, sort_keys=True, default=str)


def audit_rows(store: str, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Screen rows. `distinct_payload` is decided across the whole store, not per row."""
    seen: dict[str, int] = {}
    for row in rows:
        key = _payload_key(store, row)
        seen[key] = seen.get(key, 0) + 1

    per_requirement = {name: 0 for name in REQUIREMENTS}
    outcome_classes: set[bool] = set()
    ready = 0
    failures: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        raw_outcome = None
        for field in ("outcome", "reached", "verified", "status"):
            if field in row:
                raw_outcome = row[field]
                break
        has_outcome = raw_outcome in _OUTCOMES if isinstance(raw_outcome, (str, bool)) else False
        if has_outcome:
            outcome_classes.add(_OUTCOMES[raw_outcome])
        checks = {
            "verified_outcome": has_outcome,
            "executed_trajectory": _trajectory_is_executed(row.get("trajectory", row.get("steps"))),
            "world_identity": _has_world_identity(row),
            "evidence_provenance": _has_provenance(row),
            "distinct_payload": seen[_payload_key(store, row)] == 1,
        }
        for name, ok in checks.items():
            per_requirement[name] += int(ok)
        if all(checks.values()):
            ready += 1
        else:
            failures.append({"row": index, "missing": [n for n, ok in checks.items() if not ok]})

    return {
        "store": store,
        "rows": len(rows),
        "rows_meeting_each_requirement": per_requirement,
        "fully_ready_rows": ready,
        "outcome_classes_present": sorted(outcome_classes),
        "records_both_success_and_failure": outcome_classes == {True, False},
        "duplicate_payload_rows": sum(n - 1 for n in seen.values() if n > 1),
        "failures": failures,
    }


# --------------------------------------------------------------------------- controls

def admissible_reference_row() -> dict[str, Any]:
    """A row that satisfies all five requirements. The census is INVALID if this fails."""
    return {
        "outcome": "success",
        "trajectory": [
            {"action": "inc", "observation": 0},
            {"action": "inc", "observation": 1},
        ],
        "environment": "counter-v1",
        "model_schema": "PROJECT_BRAIN_ENVIRONMENT_STATE_KEY_V2",
        "provenance": {"receipt": "canonical/verification/example.json", "git_blob_sha": "0" * 40},
    }


def ablations() -> dict[str, dict[str, Any]]:
    """One row per requirement, broken exactly there."""
    out: dict[str, dict[str, Any]] = {}
    row = admissible_reference_row(); row.pop("outcome"); out["verified_outcome"] = row
    row = admissible_reference_row(); row["trajectory"] = [{"action": "parse file with ast.parse()"}]
    out["executed_trajectory"] = row
    row = admissible_reference_row(); row.pop("environment"); out["world_identity"] = row
    row = admissible_reference_row(); row.pop("provenance"); out["evidence_provenance"] = row
    # Duplication is a property of the store, so its ablation is audited as a pair.
    out["distinct_payload"] = admissible_reference_row()
    return out


def control_report() -> dict[str, Any]:
    positive = audit_rows("control", [admissible_reference_row()])
    positive_ok = positive["fully_ready_rows"] == 1
    results: dict[str, Any] = {}
    for name, row in ablations().items():
        rows = [row, dict(row)] if name == "distinct_payload" else [row]
        report = audit_rows("control", rows)
        missing: set[str] = set()
        for failure in report["failures"]:
            missing.update(failure["missing"])
        results[name] = {"failed_exactly_own_requirement": missing == {name}, "missing": sorted(missing)}
    return {
        "positive_control_satisfies_all_five": positive_ok,
        "positive_control": positive["rows_meeting_each_requirement"],
        "ablations": results,
        "each_ablation_fails_exactly_its_own_requirement": all(
            r["failed_exactly_own_requirement"] for r in results.values()
        ),
        "valid": positive_ok and all(r["failed_exactly_own_requirement"] for r in results.values()),
    }


# --------------------------------------------------------------------------- the live stores

#: Durable stores the runtime reads or writes. Frozen verification receipts are NOT training
#: data and are deliberately excluded: they are measurements of a run, not experience rows.
LIVE_STORES: tuple[tuple[str, str], ...] = (
    ("canonical/astra_runtime/generalization/GENERALIZATION_EXPERIENCES_V1.json", "experiences"),
    ("canonical/astra_runtime/skills/COMPILED_WORKFLOWS_BUNDLE_V1.json", "skills"),
    ("canonical/astra_runtime/state/ASSOCIATIVE_MEMORY_V1.json", "entries"),
    ("canonical/astra_runtime/state/TRANSFER_LEARNING_EPISODES_V1.json", ""),
    ("canonical/runtime/TAUGHT_WORD_LESSONS_V1.json", "lessons"),
)


def _rows(document: Any, key: str) -> list[Mapping[str, Any]]:
    rows = document.get(key) if key and isinstance(document, dict) else document
    if isinstance(rows, dict):
        rows = list(rows.values())
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, Mapping)]


def measure(root: pathlib.Path | None = None) -> dict[str, Any]:
    root = root or ROOT
    controls = control_report()
    stores: list[dict[str, Any]] = []
    for rel, key in LIVE_STORES:
        path = root / rel
        if not path.is_file():
            stores.append({"store": rel, "absent": True, "rows": 0})
            continue
        try:
            rows = _rows(json.loads(path.read_text(encoding="utf-8")), key)
        except (OSError, ValueError) as exc:
            stores.append({"store": rel, "unreadable": type(exc).__name__, "rows": 0})
            continue
        report = audit_rows(rel, rows)
        report["failures"] = report["failures"][:5]
        stores.append(report)

    present = [s for s in stores if s.get("rows")]
    total_rows = sum(s["rows"] for s in present)
    ready_rows = sum(s.get("fully_ready_rows", 0) for s in present)
    observed = {
        "positive_control_satisfies_all_five": controls["positive_control_satisfies_all_five"],
        "each_ablation_fails_exactly_its_own_requirement": controls["each_ablation_fails_exactly_its_own_requirement"],
        "no_live_store_is_fully_ready": all(s.get("fully_ready_rows", 0) == 0 for s in present),
        "generalization_experiences_record_zero_failures": next(
            (not s.get("records_both_success_and_failure", True)
             and s.get("outcome_classes_present") == [True]
             for s in present if "GENERALIZATION_EXPERIENCES" in s["store"]), False
        ),
    }
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "census_valid": controls["valid"],
        "requirements": list(REQUIREMENTS),
        "controls": controls,
        "stores": stores,
        "totals": {
            "live_stores_present": len(present),
            "rows": total_rows,
            "fully_ready_rows": ready_rows,
            "stores_recording_both_outcome_classes": sum(
                int(s.get("records_both_success_and_failure", False)) for s in present
            ),
        },
        "expected": EXPECTED,
        "observed": observed,
        "expectations_met": observed == EXPECTED,
        "scope": (
            "NECESSARY_NOT_SUFFICIENT__A_PASS_DOES_NOT_SHOW_WEIGHT_TRAINING_WORKS__"
            "A_FAIL_SHOWS_THE_CORPUS_IS_NOT_THE_LEARNING_SIGNAL_THOSE_METHODS_SPECIFY"
        ),
        "producer_cognition_model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    ns = parser.parse_args(list(argv) if argv is not None else None)
    report = measure(ns.root)
    text = json.dumps(report, indent=2, default=str) + "\n"
    if ns.json:
        ns.json.write_text(text, encoding="utf-8")
    print(f"census_valid {report['census_valid']}")
    for store in report["stores"]:
        if not store.get("rows"):
            print(f"  {store['store']}: absent/unreadable")
            continue
        print(f"  {store['store']}: rows={store['rows']} ready={store['fully_ready_rows']} "
              f"outcomes={store['outcome_classes_present']} dupes={store['duplicate_payload_rows']}")
        print(f"    {store['rows_meeting_each_requirement']}")
    print("totals", json.dumps(report["totals"]))
    print("expectations_met", report["expectations_met"])
    print("AUTHORITY NONE -- producer-run sandbox measurement")
    return 0 if report["census_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
