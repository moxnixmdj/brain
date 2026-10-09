"""Strict CursorBench externality attempt.

This module exists to prevent the invalid classifier:
    private / blocked / hard -> external.

It reuses the canonical information-theoretic externality standard.  For the
whole CursorBench predicate, current state has a public-score
non-identifiability witness, but it also has an explicitly open stronger
scope-complete policy-adequacy route.  Therefore the required ALTERNATIVE_ROUTE
bypass is not falsified and whole-predicate externality cannot be proved.

No externality certificate is manufactured here.  The correct current result
is INTERNAL_UNSOLVED.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.information_theoretic_externality_gate_v1 import (
    REQUIRED_BYPASS_CLASSES,
    verify_certificate,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_CURSORBENCH_STRICT_EXTERNALITY_ATTEMPT_V1"

EXPECTED = {
    "canonical/runtime/information_theoretic_externality_gate_v1.py":
        "008e3b8e43ba26336eee71092a67a13c02b19e1c",
    "canonical/governance/CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json":
        "d58c41a8e93fc95df6667e955e291b3f36c8942f",
    "canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V1.json":
        "7401589da3b30954104145dc4959e534ab8cd641",
    "canonical/governance/CURSORBENCH_4_0_PUBLIC_SCORE_ROUTE_NONIDENTIFIABILITY_20261009_V1.json":
        "9812efaa5098eaab3c758563a5825d5e43f6696b",
    "canonical/verification/CURSORBENCH_PUBLIC_SCORE_NONIDENTIFIABILITY_INDEPENDENT_VERIFICATION_20261009_V1.json":
        "9a97cd858170dd274f1313e565cf546501bb97ee",
    "canonical/governance/CODING_PRIVATE_BENCHMARK_PROOF_CARRYING_SCOPE_COVER_RECONCILIATION_20261009_V4.json":
        "79a7f6652d40b8749d250e344c3e32c2e8d8e996",
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json":
        "5a63cc6b57f649b6b8b60a181086beefb546837c",
}

def _blob(path: Path) -> str:
    data=path.read_bytes()
    h=hashlib.sha1()
    h.update(b"blob "+str(len(data)).encode("ascii")+b"\0"+data)
    return h.hexdigest()

def _load(path: str) -> dict[str, Any]:
    obj=json.loads((ROOT/path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(path+":NOT_OBJECT")
    return obj

def classify_attempt(
    *,
    public_score_nonidentifiable: bool,
    scope_complete: bool,
    stronger_policy_adequacy_route_state: str,
    exact_protocol_admissible_world_pair_proved: bool,
    all_internal_bypass_classes_falsified: bool,
    proof_carrying_externality_certificate_present: bool,
) -> dict[str, Any]:
    blockers: list[str]=[]

    if not public_score_nonidentifiable:
        blockers.append("PUBLIC_SCORE_NONIDENTIFIABILITY_NOT_PROVED")
    if not scope_complete:
        blockers.append("CURSORBENCH_SCOPE_NOT_COMPLETE")

    # Whole-predicate externality requires exhausting every internal route.
    # An explicitly open stronger theorem route alone is sufficient to block
    # external classification.
    if stronger_policy_adequacy_route_state != "PROVED_IMPOSSIBLE":
        blockers.append("ALTERNATIVE_ROUTE_NOT_FALSIFIED")

    if not exact_protocol_admissible_world_pair_proved:
        blockers.append("EXACT_CURSORBENCH_PROTOCOL_ADMISSIBLE_WORLD_PAIR_NOT_PROVED")

    if not all_internal_bypass_classes_falsified:
        blockers.append("INTERNAL_BYPASS_EXHAUSTION_NOT_PROVED")

    if not proof_carrying_externality_certificate_present:
        blockers.append("STRICT_EXTERNALITY_CERTIFICATE_ABSENT")

    external = not blockers
    return {
        "schema": SCHEMA+"_CLASSIFICATION",
        "status": (
            "PROVED_INFORMATION_THEORETICALLY_EXTERNAL"
            if external
            else "INTERNAL_UNSOLVED__STRICT_EXTERNALITY_NOT_PROVED"
        ),
        "externality_proved": external,
        "classification": (
            "PROVEN_INFORMATION_THEORETICALLY_EXTERNAL"
            if external else "INTERNAL_UNSOLVED"
        ),
        "blockers": blockers,
        "terminal_credit_delta": 0,
    }

def verify_current() -> dict[str, Any]:
    errors: list[str]=[]
    for rel,expected in EXPECTED.items():
        path=ROOT/rel
        if not path.is_file():
            errors.append("SOURCE_MISSING:"+rel)
        elif _blob(path)!=expected:
            errors.append("SOURCE_DRIFT:"+rel)

    owner=_load("canonical/governance/CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json")
    scope=_load("canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V1.json")
    nonid=_load("canonical/governance/CURSORBENCH_4_0_PUBLIC_SCORE_ROUTE_NONIDENTIFIABILITY_20261009_V1.json")
    nonid_v=_load("canonical/verification/CURSORBENCH_PUBLIC_SCORE_NONIDENTIFIABILITY_INDEPENDENT_VERIFICATION_20261009_V1.json")
    reconciliation=_load("canonical/governance/CODING_PRIVATE_BENCHMARK_PROOF_CARRYING_SCOPE_COVER_RECONCILIATION_20261009_V4.json")
    terminal=_load("canonical/governance/CURRENT_TERMINAL_AUTHORITY.json")

    if owner.get("target_predicate")!="CODING_CURSORBENCH_GE_57_8":
        errors.append("OWNER_PREDICATE_DRIFT")
    if scope.get("scope_complete") is not True:
        errors.append("SCOPE_NOT_CLOSED")
    if nonid.get("critical_scope_boundary",{}).get("whole_cursorbench_acceptance_predicate")!="NOT_CLASSIFIED_EXTERNAL":
        errors.append("NONIDENTIFIABILITY_BOUNDARY_DRIFT")
    if nonid_v.get("result",{}).get("whole_cursorbench_predicate_classified_external") is not False:
        errors.append("NONIDENTIFIABILITY_VERIFICATION_BOUNDARY_DRIFT")

    cb=reconciliation.get("cursorbench_4_0") or {}
    if cb.get("whole_predicate_external") is not False:
        errors.append("RECONCILIATION_EXTERNALITY_DRIFT")
    if cb.get("active_internal_missing_object") != (
        "SCOPE_COMPLETE_AUTHENTICATED_BRAIN_OWNED_POSITIVE_POLICY_ADEQUACY_CERTIFICATE"
    ):
        errors.append("ACTIVE_INTERNAL_ROUTE_DRIFT")
    if cb.get("acceptance")!="OPEN":
        errors.append("CURSORBENCH_ACCEPTANCE_MUST_REMAIN_OPEN")

    live=terminal.get("live_truth") or {}
    if live.get("cursorbench_scope_completeness_proved") is not True:
        errors.append("TERMINAL_SCOPE_RECONCILIATION_MISSING")
    if live.get("cursorbench_positive_adequacy_cover_closed") is not False:
        errors.append("TERMINAL_ADEQUACY_STATE_DRIFT")
    if live.get("cursorbench_acceptance_predicate_closed") is not False:
        errors.append("TERMINAL_ACCEPTANCE_STATE_DRIFT")

    # The strict gate itself rejects absent proof-carrying externality evidence.
    gate_result=verify_certificate(
        None,
        pending=[{"work_id":"CODING_CURSORBENCH_GE_57_8"}],
    )
    if gate_result.get("pass") is not False:
        errors.append("STRICT_GATE_UNEXPECTEDLY_PASSED_WITHOUT_CERTIFICATE")
    if gate_result.get("reason")!="PROOF_CARRYING_EXTERNALITY_CERTIFICATE_REQUIRED":
        errors.append("STRICT_GATE_REASON_DRIFT")

    attempt=classify_attempt(
        public_score_nonidentifiable=True,
        scope_complete=True,
        stronger_policy_adequacy_route_state="INTERNAL_UNSOLVED",
        exact_protocol_admissible_world_pair_proved=False,
        all_internal_bypass_classes_falsified=False,
        proof_carrying_externality_certificate_present=False,
    )
    if attempt["classification"]!="INTERNAL_UNSOLVED":
        errors.append("WHOLE_PREDICATE_MISCLASSIFIED")
    if "ALTERNATIVE_ROUTE_NOT_FALSIFIED" not in attempt["blockers"]:
        errors.append("OPEN_STRONGER_ROUTE_NOT_PRESERVED")

    passed=not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__STRICT_EXTERNALITY_ATTEMPT_FAILS_CLOSED__"
            "CURSORBENCH_WHOLE_PREDICATE_INTERNAL_UNSOLVED__ZERO_CREDIT"
            if passed else "FAIL_CLOSED"
        ),
        "pass": passed,
        "errors": errors,
        "predicate_id":"CODING_CURSORBENCH_GE_57_8",
        "required_bypass_classes": list(REQUIRED_BYPASS_CLASSES),
        "strict_gate_result": gate_result,
        "attempt": attempt,
        "public_score_route_nonidentifiable": True,
        "whole_predicate_externality_proved": False,
        "current_classification":"INTERNAL_UNSOLVED",
        "active_internal_route":
            "SCOPE_COMPLETE_AUTHENTICATED_BRAIN_OWNED_POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
        "exact_protocol_admissible_world_pair_proved": False,
        "reason_world_pair_not_promoted": (
            "CURRENT_OWNER_EVIDENCE_DOES_NOT_BIND_A_COMPLETE_CURSORBENCH_4_0_"
            "HIDDEN_TASK_SELECTION_AND_EXACT_GRADING_CONTRACT_SUFFICIENT_TO_PROVE_"
            "BOTH_COUNTERWORLDS_ARE_ADMISSIBLE_TARGET_WORLDS"
        ),
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

if __name__=="__main__":
    print(json.dumps(verify_current(),indent=2,sort_keys=True))
