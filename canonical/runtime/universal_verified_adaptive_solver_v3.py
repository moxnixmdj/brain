from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.solver_candidate_measurement_gate_v1 import audit_problem
from canonical.runtime.universal_verified_adaptive_solver_v2 import run as run_v2

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V3"


def run(
    problem: Mapping[str, Any],
    *,
    proposal_packets: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    verified_facts: Sequence[str] = (),
) -> dict[str, Any]:
    """V3 = V2 proof-to-effect binding + fail-closed observation binding preflight.

    V2 remains the execution engine. V3 refuses to promote target effects through
    verifier classes whose acceptance depends on abstract candidate values supplied
    by the proposal itself without an independent artifact/world measurement route.
    """
    measurement = audit_problem(problem)
    if measurement.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": measurement.get("status") or "FAIL_CLOSED",
            "pass": False,
            "reason": measurement.get("reason"),
            "candidate_measurement_gate": measurement,
            "terminal_authority": False,
            "capability_ownership_credit_delta": 0,
        }

    out = run_v2(
        problem,
        proposal_packets=proposal_packets,
        verified_facts=verified_facts,
    )
    if not isinstance(out, Mapping):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "V2_RESULT_NOT_MAPPING",
            "candidate_measurement_gate": measurement,
            "terminal_authority": False,
        }
    return {
        **dict(out),
        "schema": SCHEMA,
        "candidate_measurement_gate": measurement,
        "solver_base": "UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V2",
        "observation_binding": "FAIL_CLOSED_PRECHECK_FOR_UNMEASURED_PROPOSAL_VALUE_VERIFIERS",
    }
