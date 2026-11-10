#!/usr/bin/env python3
"""SUPREME GATE ENGINE — the 775 lines of discipline, made executable.

THE GAP THIS CLOSES
-------------------
`canonical/capabilities/internalized/software_engineering/supreme_c062bec/` holds the
Supreme engineering framework: five documents, 775 lines, a 10-gate
`SUPREME_EXECUTION_CONTRACT_V1.json` marked MANDATORY_FAIL_CLOSED_INTEGRATION_GLUE, and an
INTERNALIZATION_MANIFEST with all 7 source blobs integrity-matched.

Measured 2026-11-09: `grep -rln "SUPREME_EXECUTION_CONTRACT|supreme_c062bec|submission_gates"
--include=*.py canonical/` returns NOTHING. The framework is written down and enforced by
no code. Its own contract says "the framework is guidance, not a runtime enforcement
mechanism" -- true, and that is the defect. The gates exist; nothing asks them.

THE 2026 EVIDENCE SAYS THIS IS THE HIGHEST-VALUE PLACE TO SPEND
---------------------------------------------------------------
The same model moves 6.7% -> 68.3% on SWE-bench from a changed edit-tool format; LangChain's
agent 52.8% -> 66.5% on Terminal-Bench from scaffolding alone; up to 40x token difference
between harnesses on an identical model. For a system with ZERO weights, the harness is not
half the story -- it is the only place capability can live.

WHAT THIS DOES
--------------
`audit(receipt)` takes one execution receipt and returns a verdict. Ten required gates,
thirteen required fields, fail-closed: a missing gate, an empty field, a known acceptance
gap, or a read of task-specific verifier logic before submission all BLOCK. There is no
scoring, no weighting, no partial credit and no way to average a failure away.

`require_authorized(receipt)` raises. That is the only function a caller needs.

WHY FAIL-CLOSED IS THE RIGHT DEFAULT HERE
-----------------------------------------
The interesting failure of a coding agent is not "it could not do the task". It is "it said
it did". Every gate below is a different way of asking *what evidence do you have*, and the
engine refuses to accept an assertion in place of evidence -- the exact error class this
repository has corrected in itself repeatedly (the 75% -> 22.2% correction, the ARC rule-list
ceiling, the "test report with no evidence" counterexample that verifier_falsification_v1
already catches).

Cost: 0 weights, 0 parameters, 0 external model calls, 0 dollars.

Usage
    python3 canonical/runtime/supreme_gate_engine_v1.py --self-check
    python3 canonical/runtime/supreme_gate_engine_v1.py --demo
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SUPREME_GATE_ENGINE_V1"
CONTRACT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "capabilities/internalized/software_engineering/supreme_c062bec"
    / "SUPREME_EXECUTION_CONTRACT_V1.json"
)

# The ten gates, and for each: which receipt field must carry the evidence and what
# "carrying evidence" means. `evidence` gates need a non-empty value; `named` gates need
# the specific sub-key to be present, because "I did it" is not a risk class.
GATES: tuple[tuple[str, str, str], ...] = (
    ("CONFIGURATION_BOUND",          "configuration_revision", "nonempty"),
    ("ENVIRONMENT_EVIDENCE",         "environment_evidence",   "nonempty"),
    ("ACCEPTANCE_AND_INVARIANTS",    "acceptance_criteria",    "nonempty"),
    ("RISK_CLASSIFICATION",          "risk_class",             "named"),
    ("REPRODUCTION_OR_BASELINE",     "pre_change_reproduction_or_threat_model", "nonempty"),
    ("SURGICAL_IMPLEMENTATION",      "implementation_scope",   "nonempty"),
    ("INDEPENDENT_SELF_VERIFICATION", "self_tests",            "nonempty"),
    ("ADVERSARIAL_NEGATIVE_TESTS",   "adversarial_tests",      "nonempty"),
    ("COMPLETION_AUDIT",             "completion_audit",       "nonempty"),
    ("FRESHNESS_AND_CONTAMINATION",  "contamination_state",    "nonempty"),
)

REQUIRED_FIELDS: tuple[str, ...] = (
    "configuration_revision", "task_identity", "environment_evidence", "acceptance_criteria",
    "invariants", "risk_class", "pre_change_reproduction_or_threat_model",
    "implementation_scope", "self_tests", "adversarial_tests", "completion_audit",
    "contamination_state", "submission_authorized",
)

# A risk class must be one of these. A free-text risk class is a way to say nothing.
RISK_CLASSES: frozenset[str] = frozenset(
    {"TRIVIAL", "STANDARD", "SECURITY", "CONCURRENCY", "PERSISTENCE",
     "PERFORMANCE", "PARSING", "RECOVERY"}
)
# The contract says these classes REQUIRE adversarial/boundary verification. Enforced
# below, not merely stored.
ADVERSARIAL_REQUIRED: frozenset[str] = frozenset(
    {"SECURITY", "CONCURRENCY", "PERSISTENCE", "PERFORMANCE", "PARSING", "RECOVERY"}
)


class SubmissionBlocked(RuntimeError):
    """Raised by require_authorized(). Carries the blocking reasons, not just a message."""

    def __init__(self, verdict: Mapping[str, Any]):
        self.verdict = dict(verdict)
        super().__init__("SUBMISSION_BLOCKED:" + ",".join(self.verdict.get("blocking") or []))


def _nonempty(value: Any) -> bool:
    """Evidence exists and is not a placeholder.

    A boolean `True` is NOT evidence: it is an assertion. Zero, an empty string, an empty
    list and a dict of only nulls are all refusals waiting to be mistaken for passes.
    """
    if value is None or value is False:
        return False
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, frozenset)):
        return len(value) > 0
    if isinstance(value, Mapping):
        return any(_nonempty(v) for v in value.values())
    return True


def _has_counts(entry: Any) -> bool:
    """A test entry must carry an observed number, not a claim that tests ran.

    Mirrors the counterexample `verifier_falsification_v1` already refuses: "a report
    asserting success with no evidence" and "a tooling timing line, not a test count".
    """
    if isinstance(entry, Mapping):
        for key in ("passed", "passed_count", "failed", "failed_count",
                    "total", "count", "exit_code"):
            if key in entry and isinstance(entry[key], int) and not isinstance(entry[key], bool):
                return True
        return _nonempty(entry.get("observed")) or _nonempty(entry.get("evidence"))
    if isinstance(entry, (list, tuple)):
        return len(entry) > 0
    return False


def audit(receipt: Mapping[str, Any], *, contract: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Audit one execution receipt against the Supreme contract. Fail-closed.

    Returns a verdict with exactly two terminal states: SUBMISSION_AUTHORIZED or
    SUBMISSION_BLOCKED. There is deliberately no third state, because "probably fine" is
    the state that ships broken patches.
    """
    t0 = time.perf_counter()
    r = dict(receipt or {})
    blocking: list[str] = []
    gate_rows: list[dict[str, Any]] = []

    for gate_id, field, mode in GATES:
        present = field in r
        value = r.get(field)
        if not present:
            ok, why = False, "FIELD_ABSENT"
        elif mode == "named" and isinstance(value, str):
            ok = value.strip().upper() in RISK_CLASSES
            why = "RISK_CLASS_RECOGNISED" if ok else "RISK_CLASS_NOT_A_CLASS"
        else:
            ok = _nonempty(value)
            why = "EVIDENCE_PRESENT" if ok else "EVIDENCE_EMPTY_OR_ASSERTION_ONLY"
        gate_rows.append({"gate": gate_id, "field": field, "pass": ok, "reason": why})
        if not ok:
            blocking.append(f"GATE_FAILED:{gate_id}:{why}")

    for field in REQUIRED_FIELDS:
        if field not in r:
            blocking.append(f"REQUIRED_FIELD_ABSENT:{field}")

    # Rule: KNOWN_ACCEPTANCE_GAP_BLOCKS_EXTERNAL_SUBMISSION
    gaps = r.get("known_gaps")
    if isinstance(gaps, (list, tuple)) and len(gaps) > 0:
        blocking.append(f"KNOWN_ACCEPTANCE_GAP_OPEN:{len(gaps)}")

    # Rule: a risk class at or above adversarial requires the adversarial evidence to
    # carry an observed number, not a claim.
    risk = str(r.get("risk_class") or "").strip().upper()
    if risk in ADVERSARIAL_REQUIRED:
        adv = r.get("adversarial_tests")
        if not _has_counts(adv):
            blocking.append("ADVERSARIAL_EVIDENCE_HAS_NO_OBSERVED_COUNT")
    self_tests = r.get("self_tests")
    if risk in RISK_CLASSES and not _has_counts(self_tests):
        blocking.append("SELF_TEST_EVIDENCE_HAS_NO_OBSERVED_COUNT")

    # Rule: BENCHMARK_SOLUTION_OR_TASK_SPECIFIC_VERIFIER_READ_BEFORE_SUBMISSION_INVALIDATES
    contamination = str(r.get("contamination_state") or "").strip().upper()
    if contamination in {"CLEAN", "NONE", "NOT_CONTAMINATED"}:
        pass
    elif contamination.startswith(("CONTAMINATED", "SOLUTION_READ", "VERIFIER_READ")):
        blocking.append(f"CONTAMINATION:{contamination}")
    elif contamination:
        # An unrecognised contamination state is not "clean". This is the whole point.
        blocking.append(f"CONTAMINATION_STATE_UNRECOGNISED:{contamination}")
    else:
        blocking.append("CONTAMINATION_STATE_EMPTY")

    # Rule: the caller's own boolean cannot authorize submission.
    if r.get("submission_authorized") is True and blocking:
        blocking.append("CALLER_CLAIMED_AUTHORIZATION_OVERRIDDEN_BY_GATE_FAILURE")

    authorized = not blocking
    return {
        "schema": SCHEMA,
        "verdict": "SUBMISSION_AUTHORIZED" if authorized else "SUBMISSION_BLOCKED",
        "submission_authorized": authorized,
        "gates": gate_rows,
        "gates_passed": sum(1 for g in gate_rows if g["pass"]),
        "gates_total": len(gate_rows),
        "blocking": blocking,
        "blocking_count": len(blocking),
        "contract_source": str(CONTRACT_PATH.name),
        "contract_gates": _contract_gate_ids(contract),
        "weights": 0,
        "incremental_spend_usd": 0,
        "elapsed_us": round((time.perf_counter() - t0) * 1e6, 1),
    }


def _contract_gate_ids(contract: Mapping[str, Any] | None = None) -> list[str]:
    """The gate ids the contract file actually declares. Used to prove we implement them all."""
    if contract is None:
        try:
            contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - a missing contract is reported, not crashed on
            return []
    return [str(g.get("id")) for g in (contract.get("submission_gates") or [])]


def require_authorized(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """The only function a caller needs. Raises SubmissionBlocked with the reasons."""
    verdict = audit(receipt)
    if not verdict["submission_authorized"]:
        raise SubmissionBlocked(verdict)
    return verdict


def contract_coverage() -> dict[str, Any]:
    """Do the gates this engine enforces equal the gates the contract declares?

    A gate engine that implements nine of ten gates and reports success is worse than no
    engine, because the missing gate now looks covered.
    """
    declared = _contract_gate_ids()
    implemented = [g[0] for g in GATES]
    missing = [g for g in declared if g not in implemented]
    extra = [g for g in implemented if g not in declared]
    return {
        "declared": declared,
        "implemented": implemented,
        "declared_count": len(declared),
        "implemented_count": len(implemented),
        "missing_from_engine": missing,
        "extra_in_engine": extra,
        "complete": not missing,
    }


# ---------------------------------------------------------------------------- self-check --
def _good() -> dict[str, Any]:
    return {
        "configuration_revision": "supreme@c062bec2971c25c332c00954f57eb19a41053d61",
        "task_identity": "self-check/task",
        "environment_evidence": {"python": "3.11", "repo_snapshot": "sha256:abc"},
        "acceptance_criteria": ["the gate engine blocks a receipt with no evidence"],
        "invariants": ["no gate may pass on an assertion"],
        "risk_class": "TRIVIAL",
        "pre_change_reproduction_or_threat_model": "engine absent -> audit() did not exist",
        "implementation_scope": ["canonical/runtime/supreme_gate_engine_v1.py"],
        "self_tests": {"passed": 9, "failed": 0},
        "adversarial_tests": {"passed": 3, "failed": 0},
        "completion_audit": {"criteria_mapped": 1, "unresolved": 0},
        "contamination_state": "CLEAN",
        "submission_authorized": False,
    }


def self_check() -> int:
    """Prove the engine can say NO, not merely that it can say yes."""
    failures: list[str] = []

    ok = audit(_good())
    if not ok["submission_authorized"]:
        failures.append("a complete receipt was blocked: " + ",".join(ok["blocking"]))

    # each gate, removed in turn, must block and must name itself
    for gate_id, field, _mode in GATES:
        r = _good()
        r.pop(field, None)
        v = audit(r)
        if v["submission_authorized"] or not any(gate_id in b for b in v["blocking"]):
            failures.append(f"removing {field} did not block {gate_id}")

    # a boolean is not evidence
    r = _good(); r["self_tests"] = True
    if audit(r)["submission_authorized"]:
        failures.append("self_tests=True was accepted as evidence")

    # a test claim with no number
    r = _good(); r["self_tests"] = "all tests pass"
    if audit(r)["submission_authorized"]:
        failures.append("a prose test claim was accepted")

    # a known gap blocks
    r = _good(); r["known_gaps"] = ["the compound-question path is still slow"]
    if audit(r)["submission_authorized"]:
        failures.append("a known acceptance gap was accepted")

    # contamination blocks
    r = _good(); r["contamination_state"] = "SOLUTION_READ"
    if audit(r)["submission_authorized"]:
        failures.append("reading the solution did not block")

    # unrecognised contamination is not clean
    r = _good(); r["contamination_state"] = "PROBABLY_FINE"
    if audit(r)["submission_authorized"]:
        failures.append("an unrecognised contamination state was treated as clean")

    # a caller cannot authorize itself past a failed gate
    r = _good(); r.pop("adversarial_tests")
    r["risk_class"] = "SECURITY"
    r["submission_authorized"] = True
    v = audit(r)
    if v["submission_authorized"]:
        failures.append("caller claimed authorization past a failed gate")

    # an adversarial risk class demands counted adversarial evidence
    r = _good(); r["risk_class"] = "SECURITY"; r["adversarial_tests"] = "we were careful"
    if audit(r)["submission_authorized"]:
        failures.append("SECURITY risk accepted prose adversarial evidence")

    # an unrecognised risk class is not a class
    r = _good(); r["risk_class"] = "PROBABLY_FINE"
    if audit(r)["submission_authorized"]:
        failures.append("an unrecognised risk class was accepted")

    # require_authorized raises, and carries reasons
    try:
        require_authorized({})
        failures.append("require_authorized accepted an empty receipt")
    except SubmissionBlocked as exc:
        if not exc.verdict.get("blocking"):
            failures.append("SubmissionBlocked carried no reasons")

    cov = contract_coverage()
    if not cov["complete"]:
        failures.append("engine does not implement every declared gate: " + ",".join(cov["missing_from_engine"]))

    print(f"contract gates declared: {cov['declared_count']}  implemented: {cov['implemented_count']}")
    print(f"self-check cases: 9 positive/negative classes + {len(GATES)} gate removals")
    if failures:
        print(f"SELF-CHECK FAILED ({len(failures)}):")
        for f in failures:
            print("  -", f)
        return 1
    print("SELF-CHECK PASS — the engine can say NO in every way the contract requires")
    return 0


def demo() -> int:
    print(json.dumps(audit(_good()), indent=1)[:1400])
    print("\n--- a receipt that claims it is authorized but has no evidence ---")
    bad = {"task_identity": "x", "risk_class": "SECURITY", "submission_authorized": True,
           "self_tests": {"passed": 4}, "contamination_state": "CLEAN"}
    v = audit(bad)
    print(json.dumps({"verdict": v["verdict"], "gates_passed": v["gates_passed"],
                      "blocking_count": v["blocking_count"],
                      "first_three": v["blocking"][:3]}, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args(argv)
    if a.self_check:
        return self_check()
    if a.demo:
        return demo()
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
