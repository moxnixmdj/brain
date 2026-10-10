"""Professional-quality P1 Router V5: decision-relevant interpretation guard over V4.

V5 reuses the Brain-owned semantic ambiguity controller. It does not infer,
enumerate, or self-certify interpretations. The caller must provide a declared
complete finite interpretation model. V5 only permits V4 delegation when the
surviving interpretations are terminally equivalent. Otherwise it returns the
minimum policy-changing information action or fails closed.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v4 as base
from canonical.runtime import semantic_ambiguity_control_v1 as ambiguity

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V5"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _base(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "route": "ABSTAIN",
        "interpretation_model_bound": False,
        "root_subject_binding_authority": False,
        "semantic_truth_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def route(state: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        return _base("FAIL_CLOSED", reason="STATE_NOT_OBJECT")

    model = state.get("interpretation_model")
    if not isinstance(model, Mapping):
        return _base("FAIL_CLOSED", reason="INTERPRETATION_MODEL_REQUIRED")

    decision = ambiguity.decide(model)
    binding = {
        "interpretation_model_sha256": _digest(dict(model)),
        "ambiguity_decision_schema": decision.get("schema"),
        "ambiguity_decision_status": decision.get("status"),
        "ambiguity_owner": decision.get("ambiguity_owner"),
        "hypothesis_set_complete_declared": model.get("hypothesis_set_complete") is True,
        "does_not_self_certify_hypothesis_completeness": True,
    }

    if decision.get("pass") is not True:
        status = str(decision.get("status") or "")
        if status.startswith("OPEN__"):
            return _base(
                "ABSTAIN__R1_DECISION_RELEVANT_INTERPRETATION_AMBIGUITY",
                reason=decision.get("reason"),
                interpretation_model_bound=True,
                interpretation_binding=binding,
                ambiguity_action=decision.get("action"),
                next_observation_id=decision.get("next_observation_id"),
                ask_user_required=decision.get("ask_user_required") is True,
                clarification_required=decision.get("clarification_required") is True,
                additional_information_required=decision.get("additional_information_required") is True,
                unresolved_pairs=deepcopy(decision.get("unresolved_pairs") or []),
                ambiguity_decision=deepcopy(decision),
            )
        return _base(
            "FAIL_CLOSED",
            reason="INTERPRETATION_MODEL_INSUFFICIENT",
            interpretation_model_bound=True,
            interpretation_binding=binding,
            ambiguity_decision=deepcopy(decision),
        )

    if decision.get("action") != "CONTINUE_WITHOUT_DISAMBIGUATION":
        return _base(
            "FAIL_CLOSED",
            reason="AMBIGUITY_PASS_WITH_UNEXPECTED_ACTION",
            interpretation_model_bound=True,
            interpretation_binding=binding,
            ambiguity_decision=deepcopy(decision),
        )

    delegated = deepcopy(dict(state))
    delegated.pop("interpretation_model", None)
    out = base.route(delegated, repo_root=repo_root)
    if not isinstance(out, Mapping):
        return _base("FAIL_CLOSED", reason="V4_RESULT_NOT_OBJECT")

    result = deepcopy(dict(out))
    result["schema"] = SCHEMA
    result["interpretation_model_bound"] = True
    result["interpretation_binding"] = {
        **binding,
        "terminally_equivalent": decision.get("terminally_equivalent") is True,
        "does_not_require_full_interpretation_identity": decision.get(
            "does_not_require_full_interpretation_identity"
        ) is True,
    }
    result["ambiguity_decision"] = {
        "schema": decision.get("schema"),
        "status": decision.get("status"),
        "action": decision.get("action"),
        "terminally_equivalent": decision.get("terminally_equivalent") is True,
    }
    result["root_subject_binding_authority"] = False
    result["semantic_truth_authority"] = False
    result["quality_authority"] = False
    result["acceptance_authority"] = False
    result["promotion_authority"] = False
    result["terminal_authority"] = False
    result["terminal_credit_delta"] = 0
    result["incremental_spend_usd"] = 0
    return result


if __name__ == "__main__":
    print(json.dumps(_base("NOT_EXECUTED"), indent=2, sort_keys=True))
