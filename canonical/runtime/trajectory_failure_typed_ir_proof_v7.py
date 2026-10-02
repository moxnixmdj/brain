"""V7 proof envelope for direct-causal-cutset trajectory diagnosis.

Reuses the independently verified V6 192-case forward intervention model, then
adds the two counterexample classes that invalidate V6 terminal-scope transport:
1) a derived-only visible failure must never be promoted to a direct root;
2) two serial DIRECT_CONTRACT faults require both repairs, even though one is an
   ancestor of the other.

No terminal case IDs, terminal seeds, or hidden terminal results are used.
"""
from __future__ import annotations
import copy
from typing import Any, Mapping

from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as v6

SCHEMA = "PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V7"
DOMAINS = v6.DOMAINS
KINDS = v6.KINDS
PATTERNS = v6.PATTERNS
suite_cases = v6.suite_cases
public_task = v6.public_task
execute_intervention = v6.execute_intervention
score_case = v6.score_case


def derived_only_case(domain: str = "CODE") -> dict[str, Any]:
    p = domain.lower() + ":"
    return {
        "schema": SCHEMA,
        "behavior_id": "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "task": {
            "domain": domain,
            "trajectory": [
                {
                    "step": 0, "action_id": "A0", "domain": domain,
                    "reads": [], "writes": [p+"upstream"], "depends_on": [],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [{
                        "kind": "INVARIANT", "id": "A0:INVARIANT", "pass": True,
                        "evidence": ["receipt:A0", "check:A0:INVARIANT"],
                        "failure_semantics": "DIRECT_CONTRACT",
                    }],
                },
                {
                    "step": 1, "action_id": "A1", "domain": domain,
                    "reads": [p+"upstream"], "writes": [p+"symptom"], "depends_on": ["A0"],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [
                        {
                            "kind": "INVARIANT", "id": "A1:INVARIANT:baseline", "pass": True,
                            "evidence": ["receipt:A1", "check:A1:INVARIANT:baseline"],
                            "failure_semantics": "DIRECT_CONTRACT",
                        },
                        {
                            "kind": "SCOPE", "id": "A1:SCOPE", "pass": False,
                            "evidence": ["receipt:A1", "check:A1:SCOPE"],
                            "failure_semantics": "DERIVED_UPSTREAM",
                        },
                    ],
                },
                {
                    "step": 2, "action_id": "A2", "domain": domain,
                    "reads": [p+"symptom"], "writes": [p+"terminal"], "depends_on": ["A1"],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [{
                        "kind": "INVARIANT", "id": "A2:INVARIANT", "pass": True,
                        "evidence": ["receipt:A2", "check:A2:INVARIANT"],
                        "failure_semantics": "DIRECT_CONTRACT",
                    }],
                },
            ],
            "terminal_failed_resources": [p+"terminal"],
            "goal": "LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITH_MACHINE_VERIFIED_TERMINAL_RESCUE",
        },
    }


def serial_direct_cofault_case(domain: str = "CODE") -> dict[str, Any]:
    p = domain.lower() + ":"
    return {
        "schema": SCHEMA,
        "behavior_id": "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "task": {
            "domain": domain,
            "trajectory": [
                {
                    "step": 0, "action_id": "A0", "domain": domain,
                    "reads": [], "writes": [p+"seed"], "depends_on": [],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [{
                        "kind": "INVARIANT", "id": "A0:INVARIANT", "pass": True,
                        "evidence": ["receipt:A0", "check:A0:INVARIANT"],
                        "failure_semantics": "DIRECT_CONTRACT",
                    }],
                },
                {
                    "step": 1, "action_id": "A1", "domain": domain,
                    "reads": [p+"seed"], "writes": [p+"first"], "depends_on": ["A0"],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [
                        {
                            "kind": "INVARIANT", "id": "A1:INVARIANT:baseline", "pass": True,
                            "evidence": ["receipt:A1", "check:A1:INVARIANT:baseline"],
                            "failure_semantics": "DIRECT_CONTRACT",
                        },
                        {
                            "kind": "AUTHORITY", "id": "A1:AUTHORITY", "pass": False,
                            "evidence": ["receipt:A1", "check:A1:AUTHORITY"],
                            "failure_semantics": "DIRECT_CONTRACT",
                        },
                    ],
                },
                {
                    "step": 2, "action_id": "A2", "domain": domain,
                    "reads": [p+"first"], "writes": [p+"second"], "depends_on": ["A1"],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [
                        {
                            "kind": "INVARIANT", "id": "A2:INVARIANT:baseline", "pass": True,
                            "evidence": ["receipt:A2", "check:A2:INVARIANT:baseline"],
                            "failure_semantics": "DIRECT_CONTRACT",
                        },
                        {
                            "kind": "SCOPE", "id": "A2:SCOPE", "pass": False,
                            "evidence": ["receipt:A2", "check:A2:SCOPE"],
                            "failure_semantics": "DIRECT_CONTRACT",
                        },
                    ],
                },
                {
                    "step": 3, "action_id": "A3", "domain": domain,
                    "reads": [p+"second"], "writes": [p+"symptom"], "depends_on": ["A2"],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [
                        {
                            "kind": "INVARIANT", "id": "A3:INVARIANT:baseline", "pass": True,
                            "evidence": ["receipt:A3", "check:A3:INVARIANT:baseline"],
                            "failure_semantics": "DIRECT_CONTRACT",
                        },
                        {
                            "kind": "INVARIANT", "id": "A3:INVARIANT:derived", "pass": False,
                            "evidence": ["receipt:A3", "check:A3:INVARIANT:derived"],
                            "failure_semantics": "DERIVED_UPSTREAM",
                        },
                    ],
                },
                {
                    "step": 4, "action_id": "A4", "domain": domain,
                    "reads": [p+"symptom"], "writes": [p+"terminal"], "depends_on": ["A3"],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [{
                        "kind": "INVARIANT", "id": "A4:INVARIANT", "pass": True,
                        "evidence": ["receipt:A4", "check:A4:INVARIANT"],
                        "failure_semantics": "DIRECT_CONTRACT",
                    }],
                },
            ],
            "terminal_failed_resources": [p+"terminal"],
            "goal": "LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITH_MACHINE_VERIFIED_TERMINAL_RESCUE",
        },
    }


def score_derived_only(candidate: Mapping[str, Any]) -> dict[str, Any]:
    good = (
        candidate.get("status") == "ESCALATE"
        and candidate.get("reason") == "ONLY_DERIVED_UPSTREAM_FAILURES_VISIBLE__NO_DIRECT_CAUSAL_ROOT_PROVED"
    )
    iv = execute_intervention(derived_only_case(), candidate)
    return {
        "pass": good and iv.get("terminal_rescued") is not True,
        "reason": "PASS" if good and iv.get("terminal_rescued") is not True else "DERIVED_ONLY_OVERCLAIM",
        "intervention": iv,
    }


def score_serial_direct_cofault(candidate: Mapping[str, Any], *, domain: str = "CODE") -> dict[str, Any]:
    public = serial_direct_cofault_case(domain)
    expected_repairs = ["restore:A1:AUTHORITY", "restore:A2:SCOPE"]
    iv = execute_intervention(public, candidate)
    good = (
        candidate.get("status") == "INTERACTION"
        and candidate.get("cause_action_ids") == ["A1", "A2"]
        and candidate.get("critical_action_id") == "A1"
        and candidate.get("mechanism_by_action") == {"A1": ["AUTHORITY"], "A2": ["SCOPE"]}
        and candidate.get("repair_targets") == expected_repairs
        and iv.get("terminal_rescued") is True
    )
    return {
        "pass": good,
        "reason": "PASS" if good else "SERIAL_DIRECT_CUTSET_WRONG",
        "intervention": iv,
        "expected_repair_targets": expected_repairs,
    }


def hardening_cases() -> list[dict[str, Any]]:
    out = []
    for domain in DOMAINS:
        out.append({"id": f"DERIVED_ONLY::{domain}", "kind": "DERIVED_ONLY", "public": derived_only_case(domain)})
        out.append({"id": f"SERIAL_DIRECT_COFAULT::{domain}", "kind": "SERIAL_DIRECT_COFAULT", "public": serial_direct_cofault_case(domain)})
    return out
