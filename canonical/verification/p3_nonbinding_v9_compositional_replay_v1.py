"""Independent compositional replay for P3 V9 nonbinding-capacity routing.

The predecessor V8 implementation is already independently exact-byte verified.
This replay replaces V8 only at its public evaluate() interface so the new V9
routing delta can be tested without re-verifying V8's transitive dependency
closure. The new nonbinding cell and contract-surface guard are real modules.
"""
from __future__ import annotations

import json
import sys
import types


def _v8_stub(payload, repo_root=None):
    cid = payload.get("context_id") if isinstance(payload, dict) else None
    base = {
        "source_authorization_verified": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if cid == "v8pass":
        return {**base, "pass": True, "status": "PASS", "route": "EXISTING_V8_ROUTE"}
    if isinstance(payload, dict) and "objective_weights" in payload:
        return {**base, "pass": False, "status": "FAIL_CLOSED", "reason": "OBJECTIVE_WEIGHTS_UNSATISFIED"}
    if isinstance(payload, dict) and "decision_dependency_contract" in payload:
        return {**base, "pass": False, "status": "FAIL_CLOSED", "reason": "DECISION_DEPENDENCY_CONTRACT_UNSATISFIED"}
    return {**base, "pass": False, "status": "FAIL_CLOSED", "reason": "V2_SEMANTIC_FALLBACK"}


stub = types.ModuleType("canonical.runtime.p3_real_context_v3_admission_v8")
stub.evaluate = _v8_stub
sys.modules["canonical.runtime.p3_real_context_v3_admission_v8"] = stub

from canonical.runtime.p3_real_context_v3_admission_v9 import evaluate  # noqa: E402
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA  # noqa: E402


def ev(i, text):
    return {
        "evidence_id": i,
        "text": text,
        "verified": True,
        "provenance": [{"source_id": i, "locator": "p1"}],
    }


def payload(max_items=3, cid="x"):
    return {
        "context_id": cid,
        "v3_input": {
            "schema": INPUT_SCHEMA,
            "task": {
                "claims": [
                    {"claim_id": "A", "text": "alpha status is ready", "required": True},
                    {"claim_id": "B", "text": "beta status is ready", "required": False},
                    {"claim_id": "C", "text": "gamma status is ready", "required": False},
                ],
                "evidence": [
                    ev("e1", "source: alpha status is ready"),
                    ev("e2", "source: beta status is ready"),
                    ev("e3", "source: gamma status is ready"),
                ],
                "required_uncertainty_units": [],
                "audience_profile": {
                    "profile_id": "EXPLICIT",
                    "constraints": {
                        "output_format": "BULLETS",
                        "citation_mode": "INLINE_SOURCE_IDS",
                        "style": "VERBATIM_GROUNDED",
                        "required_sections": [],
                        "allowed_sections": None,
                        "max_items": max_items,
                        "max_chars": 2000,
                        "heading_level": 2,
                        "require_title": False,
                    },
                },
            },
        },
    }


def cases():
    out = []

    p = payload(cid="v8pass")
    r = evaluate(p)
    out.append(("PRESERVE_V8_SUCCESS", r.get("pass") is True and r.get("route") == "EXISTING_V8_ROUTE" and r.get("v8_preserved_positive_route") is True))

    r = evaluate(payload(3))
    out.append(("NONBINDING_ROUTE_ACTIVATES", r.get("pass") is True and r.get("route") == "NONBINDING_CAPACITY_COMMON_POLICY_CELL_V1" and r.get("selected_claim_ids") == ["A", "B", "C"]))

    r = evaluate(payload(2))
    out.append(("BINDING_CAPACITY_FAILS_CLOSED", r.get("pass") is False and r.get("nonbinding_capacity_reason") == "CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY"))

    p = payload(3)
    p["objective_weights"] = {"A": 1}
    r = evaluate(p)
    out.append(("EXPLICIT_WEIGHT_FAILURE_CANNOT_FALL_THROUGH", r.get("pass") is False and r.get("reason") == "OBJECTIVE_WEIGHTS_UNSATISFIED" and r.get("nonbinding_capacity_fast_path_pass") is False))

    p = payload(3)
    p["v3_input"]["task"]["claims"][1]["forbid_output"] = True
    r = evaluate(p)
    out.append(("HIDDEN_SEMANTICS_REJECTED", r.get("pass") is False and r.get("reason") == "UNMODELED_CLAIM_REQUIREMENTS"))

    p = payload(3)
    del p["context_id"]
    r = evaluate(p)
    out.append(("CONTEXT_ID_STILL_REQUIRED", r.get("pass") is False and r.get("reason") == "CONTEXT_ID_REQUIRED"))

    r = evaluate(payload(3))
    zero = all(
        r.get(k) is False
        for k in (
            "source_authorization_verified",
            "policy_adequacy_authority",
            "db_admission_authority",
            "u_subtraction_authority",
            "terminal_authority",
        )
    ) and r.get("terminal_credit_delta") == 0
    out.append(("NO_AUTHORITY_ESCALATION", r.get("pass") is True and zero))

    return out


def main():
    rows = cases()
    passed = sum(1 for _, ok in rows if ok)
    result = {
        "schema": "PROJECT_BRAIN_P3_NONBINDING_V9_COMPOSITIONAL_REPLAY_V1",
        "status": "PASS" if passed == len(rows) else "FAIL",
        "passed": passed,
        "total": len(rows),
        "cases": [{"id": name, "pass": ok} for name, ok in rows],
        "predecessor_v8_reverified_here": False,
        "boundary": "V9_DELTA_COMPOSITION_REPLAY_AGAINST_VERIFIED_V8_INTERFACE_STUB",
        "terminal_credit_delta": 0,
    }
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if passed == len(rows) else 1)


if __name__ == "__main__":
    main()
