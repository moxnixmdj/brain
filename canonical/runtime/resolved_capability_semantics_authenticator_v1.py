"""Authenticate one resolved value-bound capability instance.

A capability action template may contain trusted state references such as:
  {"$effect_result": {"effect": "DOC", "field": "candidate_sha256"}}

After those references are resolved from universal_solver_value_state_v1, the
resulting verifier/action instance is a different semantic object from the
template. This module therefore requires a content-addressed receipt plus a
separate independent-verification receipt for the exact resolved instance.

The receipt binds:
- full task contract identity;
- capability id and prerequisite effect names;
- current value-capsule head and exact prerequisite value hashes;
- action template digest;
- resolved action digest;
- built-in verifier id and resolved payload digest;
- exact verifier success condition;
- exact provided effects;
- declared result fields.

This module verifies receipt identity and binding only. The independent verifier
is the authority for the implication semantics.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes
from canonical.runtime.composition_state_capsule_v2 import project_context, verify_capsule
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime import universal_verified_adaptive_solver_v4 as v4

SCHEMA = "PROJECT_BRAIN_RESOLVED_CAPABILITY_SEMANTICS_AUTHENTICATOR_V1"
BINDING_SCHEMA = "PROJECT_BRAIN_RESOLVED_CAPABILITY_SEMANTICS_BINDING_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_RESOLVED_CAPABILITY_SEMANTICS_INDEPENDENT_VERIFICATION_V1"
CLAIM = "RESOLVED_VERIFIER_PASS_IMPLIES_EXACT_EFFECTS_AND_DECLARED_RESULT_FIELDS"


class ResolvedSemanticsError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _tokens(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ResolvedSemanticsError(label + "_INVALID")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ResolvedSemanticsError(label + "_ITEM_INVALID")
        token = item.strip()
        if token in out:
            raise ResolvedSemanticsError(label + "_DUPLICATE:" + token)
        out.append(token)
    return out


def expected_binding(
    problem: Mapping[str, Any],
    capability: Mapping[str, Any],
    resolved_action: Mapping[str, Any],
    value_capsule: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        raise ResolvedSemanticsError("PROBLEM_INVALID")
    if not isinstance(capability, Mapping):
        raise ResolvedSemanticsError("CAPABILITY_INVALID")
    if not isinstance(resolved_action, Mapping):
        raise ResolvedSemanticsError("RESOLVED_ACTION_INVALID")

    verdict = verify_capsule(value_capsule)
    if verdict.get("status") != "PASS":
        raise ResolvedSemanticsError("VALUE_CAPSULE_INVALID:" + str(verdict.get("reason")))

    cid = capability.get("id")
    if not isinstance(cid, str) or not cid:
        raise ResolvedSemanticsError("CAPABILITY_ID_INVALID")
    requires = sorted(_tokens(capability.get("requires", []), "REQUIRES"))
    provides = sorted(_tokens(capability.get("provides", []), "PROVIDES"))
    result_fields = sorted(_tokens(capability.get("result_fields", []), "RESULT_FIELDS"))
    if not provides:
        raise ResolvedSemanticsError("PROVIDES_EMPTY")

    template = capability.get("action")
    if not isinstance(template, Mapping):
        raise ResolvedSemanticsError("ACTION_TEMPLATE_INVALID")

    if resolved_action.get("type") == "verified_effect_tool":
        verifier_id = resolved_action.get("pre_verifier_id")
        verifier_payload = resolved_action.get("pre_verifier_payload")
    else:
        verifier_id = resolved_action.get("verifier_id")
        verifier_payload = resolved_action.get("verifier_payload")
    if verifier_id not in SUCCESS_CONDITIONS:
        raise ResolvedSemanticsError("VERIFIER_SUCCESS_CONDITION_UNKNOWN:" + str(verifier_id))
    if not isinstance(verifier_payload, Mapping):
        raise ResolvedSemanticsError("RESOLVED_VERIFIER_PAYLOAD_INVALID")

    contract = resolved_action.get("effect_contract")
    if not isinstance(contract, Mapping) or set(contract) != {"effects", "verifier_success_condition"}:
        raise ResolvedSemanticsError("EFFECT_CONTRACT_INVALID")
    effects = sorted(_tokens(contract.get("effects"), "EFFECTS"))
    if effects != provides:
        raise ResolvedSemanticsError("PROVIDES_EFFECT_CONTRACT_MISMATCH")
    success = SUCCESS_CONDITIONS[str(verifier_id)]
    if contract.get("verifier_success_condition") != success:
        raise ResolvedSemanticsError("VERIFIER_SUCCESS_CONDITION_MISMATCH")

    context = project_context(value_capsule, requires) if requires else {
        "capsule_head_hash": value_capsule.get("head_hash"),
        "bindings": {},
    }
    input_value_hashes = {
        effect: context["bindings"][effect]["value_hash"]
        for effect in requires
    }

    return {
        "capability_id": cid,
        "task_contract_sha256": v4.task_contract_sha256(problem),
        "requires": requires,
        "value_capsule_head_hash": value_capsule.get("head_hash"),
        "input_value_hashes": input_value_hashes,
        "action_template_sha256": _sha(template),
        "resolved_action_sha256": _sha(resolved_action),
        "verifier_id": verifier_id,
        "resolved_verifier_payload_sha256": _sha(verifier_payload),
        "verifier_success_condition": success,
        "provided_effects": provides,
        "result_fields": result_fields,
    }


def authenticate(
    problem: Mapping[str, Any],
    capability: Mapping[str, Any],
    resolved_action: Mapping[str, Any],
    value_capsule: Mapping[str, Any],
    binding_pair: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        expected = expected_binding(problem, capability, resolved_action, value_capsule)
        if not isinstance(binding_pair, Mapping):
            raise ResolvedSemanticsError("BINDING_PAIR_INVALID")
        rr = resolve_receipt_bytes(binding_pair.get("receipt"), repo_root=repo_root)
        vr = resolve_receipt_bytes(binding_pair.get("verification"), repo_root=repo_root)
        rd = rr["document"]
        vd = vr["document"]

        if rd.get("schema") != BINDING_SCHEMA:
            raise ResolvedSemanticsError("BINDING_SCHEMA_INVALID")
        if vd.get("schema") != VERIFY_SCHEMA:
            raise ResolvedSemanticsError("VERIFY_SCHEMA_INVALID")
        if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
            raise ResolvedSemanticsError("VERIFY_SUBJECT_BLOB_MISMATCH")

        for key, value in expected.items():
            if rd.get(key) != value:
                raise ResolvedSemanticsError("BINDING_MISMATCH:" + key)
            if vd.get(key) != value:
                raise ResolvedSemanticsError("VERIFY_MISMATCH:" + key)

        if rd.get("pass") is not True or rd.get("claim") != CLAIM:
            raise ResolvedSemanticsError("BINDING_CLAIM_INVALID")
        if (
            vd.get("pass") is not True
            or vd.get("independent_verified") is not True
            or vd.get("effect_semantics_verified") is not True
            or vd.get("result_field_semantics_verified") is not True
            or vd.get("trusted_substitution_semantics_verified") is not True
        ):
            raise ResolvedSemanticsError("INDEPENDENT_VERIFICATION_INSUFFICIENT")
        verifier = vd.get("independent_verifier_id")
        if not isinstance(verifier, str) or not verifier.strip():
            raise ResolvedSemanticsError("INDEPENDENT_VERIFIER_ID_INVALID")

        return {
            "schema": SCHEMA,
            "status": "PASS__RESOLVED_CAPABILITY_SEMANTICS_AUTHENTICATED",
            "pass": True,
            **expected,
            "receipt": {"path": rr["path"], "git_blob_sha": rr["git_blob_sha"]},
            "verification": {"path": vr["path"], "git_blob_sha": vr["git_blob_sha"]},
            "independent_verifier_id": verifier.strip(),
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }


def select_and_authenticate(
    problem: Mapping[str, Any],
    capability: Mapping[str, Any],
    resolved_action: Mapping[str, Any],
    value_capsule: Mapping[str, Any],
    binding_pairs: Sequence[Mapping[str, Any]],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(binding_pairs, Sequence) or isinstance(binding_pairs, (str, bytes, bytearray)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["BINDING_PAIRS_INVALID"],
            "terminal_authority": False,
        }
    failures: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    for pair in binding_pairs:
        out = authenticate(
            problem,
            capability,
            resolved_action,
            value_capsule,
            pair,
            repo_root=repo_root,
        )
        if out.get("pass") is True:
            matches.append(out)
        else:
            failures.append(out)
    if len(matches) != 1:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [
                "RESOLVED_SEMANTICS_BINDING_MATCH_COUNT:" + str(len(matches))
            ],
            "failed_candidate_count": len(failures),
            "terminal_authority": False,
        }
    return matches[0]
