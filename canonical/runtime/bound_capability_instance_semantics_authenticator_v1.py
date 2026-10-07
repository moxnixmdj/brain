"""Authenticate one prepared promoted bound-capability instance for a task.

The bound registry proves a capability was independently verified for its promoted
registry contract. The universal solver may alias that capability into a task-
specific effect vocabulary, export selected result fields, and instantiate its
input template with trusted values.

Those task-specific semantics are NOT inherited automatically from the registry.
This authenticator therefore requires a separate content-addressed receipt plus
independent verification binding:

- task contract;
- universal capability instance id;
- prerequisite effects and current value hashes;
- source promoted registry capability id;
- exact registry file and entry digests;
- exact rendered action and input digests;
- exact task-level provided effects;
- exported result fields;
- the promoted action expectation;
- the claim that a verified promoted execution of this exact instance implies
  those task effects and result-field meanings.

It grants no execution or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes
from canonical.runtime.composition_state_capsule_v2 import project_context, verify_capsule
from canonical.runtime import universal_verified_adaptive_solver_v4 as v4

SCHEMA = "PROJECT_BRAIN_BOUND_CAPABILITY_INSTANCE_SEMANTICS_AUTHENTICATOR_V1"
BINDING_SCHEMA = "PROJECT_BRAIN_BOUND_CAPABILITY_INSTANCE_SEMANTICS_BINDING_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_BOUND_CAPABILITY_INSTANCE_SEMANTICS_INDEPENDENT_VERIFICATION_V1"
CLAIM = "VERIFIED_PROMOTED_BOUND_EXECUTION_IMPLIES_EXACT_TASK_EFFECTS_AND_RESULT_FIELDS"
SUCCESS_CONDITION = "PROMOTED_REGISTRY_EXPECTATION_AND_BOUND_EXECUTION_TRACE_VERIFIED"


class BoundInstanceSemanticsError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _tokens(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise BoundInstanceSemanticsError(label + "_INVALID")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise BoundInstanceSemanticsError(label + "_ITEM_INVALID")
        token = item.strip()
        if token in out:
            raise BoundInstanceSemanticsError(label + "_DUPLICATE:" + token)
        out.append(token)
    return out


def expected_binding(
    problem: Mapping[str, Any],
    capability: Mapping[str, Any],
    prepared: Mapping[str, Any],
    value_capsule: Mapping[str, Any],
) -> dict[str, Any]:
    verdict = verify_capsule(value_capsule)
    if verdict.get("status") != "PASS":
        raise BoundInstanceSemanticsError(
            "VALUE_CAPSULE_INVALID:" + str(verdict.get("reason"))
        )
    if not isinstance(capability, Mapping) or capability.get("action", {}).get("type") != "verified_bound_capability":
        raise BoundInstanceSemanticsError("UNIVERSAL_BOUND_CAPABILITY_ACTION_INVALID")
    if not isinstance(prepared, Mapping) or prepared.get("status") != "PREPARED__PROMOTED_BOUND_CAPABILITY":
        raise BoundInstanceSemanticsError("PREPARED_BOUND_CAPABILITY_INVALID")

    cid = capability.get("id")
    if not isinstance(cid, str) or not cid:
        raise BoundInstanceSemanticsError("CAPABILITY_ID_INVALID")
    action = capability["action"]
    source_id = action.get("registry_capability_id")
    if source_id != prepared.get("capability_id"):
        raise BoundInstanceSemanticsError("REGISTRY_CAPABILITY_ID_MISMATCH")

    requires = sorted(_tokens(capability.get("requires", []), "REQUIRES"))
    provides = sorted(_tokens(capability.get("provides", []), "PROVIDES"))
    result_fields = sorted(_tokens(capability.get("result_fields", []), "RESULT_FIELDS"))
    if prepared.get("instance_id") != cid:
        raise BoundInstanceSemanticsError("PREPARED_INSTANCE_ID_MISMATCH")
    if sorted(prepared.get("requires") or []) != requires:
        raise BoundInstanceSemanticsError("PREPARED_REQUIRES_MISMATCH")
    if sorted(prepared.get("provides") or []) != provides:
        raise BoundInstanceSemanticsError("PREPARED_PROVIDES_MISMATCH")
    if sorted(prepared.get("result_fields") or []) != result_fields:
        raise BoundInstanceSemanticsError("PREPARED_RESULT_FIELDS_MISMATCH")

    context = project_context(value_capsule, requires) if requires else {
        "capsule_head_hash": value_capsule.get("head_hash"),
        "bindings": {},
    }
    value_hashes = {
        effect: context["bindings"][effect]["value_hash"]
        for effect in requires
    }

    rendered = prepared.get("rendered_action")
    if not isinstance(rendered, Mapping):
        raise BoundInstanceSemanticsError("PREPARED_RENDERED_ACTION_INVALID")
    expect = rendered.get("expect")
    if not isinstance(expect, Mapping):
        raise BoundInstanceSemanticsError("PROMOTED_ACTION_EXPECTATION_MISSING")

    return {
        "capability_id": cid,
        "task_contract_sha256": v4.task_contract_sha256(problem),
        "requires": requires,
        "value_capsule_head_hash": value_capsule.get("head_hash"),
        "input_value_hashes": value_hashes,
        "registry_capability_id": source_id,
        "registry_file_sha256": prepared.get("registry_file_sha256"),
        "registry_entry_sha256": prepared.get("registry_entry_sha256"),
        "inputs_sha256": prepared.get("inputs_sha256"),
        "rendered_action_sha256": prepared.get("rendered_action_sha256"),
        "promoted_expectation_sha256": _sha(expect),
        "provided_effects": provides,
        "result_fields": result_fields,
        "execution_success_condition": SUCCESS_CONDITION,
    }


def authenticate(
    problem: Mapping[str, Any],
    capability: Mapping[str, Any],
    prepared: Mapping[str, Any],
    value_capsule: Mapping[str, Any],
    binding_pair: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        expected = expected_binding(problem, capability, prepared, value_capsule)
        if not isinstance(binding_pair, Mapping):
            raise BoundInstanceSemanticsError("BINDING_PAIR_INVALID")
        rr = resolve_receipt_bytes(binding_pair.get("receipt"), repo_root=repo_root)
        vr = resolve_receipt_bytes(binding_pair.get("verification"), repo_root=repo_root)
        rd = rr["document"]
        vd = vr["document"]
        if rd.get("schema") != BINDING_SCHEMA:
            raise BoundInstanceSemanticsError("BINDING_SCHEMA_INVALID")
        if vd.get("schema") != VERIFY_SCHEMA:
            raise BoundInstanceSemanticsError("VERIFY_SCHEMA_INVALID")
        if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
            raise BoundInstanceSemanticsError("VERIFY_SUBJECT_BLOB_MISMATCH")
        for key, value in expected.items():
            if rd.get(key) != value:
                raise BoundInstanceSemanticsError("BINDING_MISMATCH:" + key)
            if vd.get(key) != value:
                raise BoundInstanceSemanticsError("VERIFY_MISMATCH:" + key)
        if rd.get("pass") is not True or rd.get("claim") != CLAIM:
            raise BoundInstanceSemanticsError("BINDING_CLAIM_INVALID")
        if (
            vd.get("pass") is not True
            or vd.get("independent_verified") is not True
            or vd.get("registry_contract_semantics_verified") is not True
            or vd.get("task_effect_semantics_verified") is not True
            or vd.get("result_field_semantics_verified") is not True
            or vd.get("trusted_input_binding_semantics_verified") is not True
        ):
            raise BoundInstanceSemanticsError("INDEPENDENT_VERIFICATION_INSUFFICIENT")
        verifier = vd.get("independent_verifier_id")
        if not isinstance(verifier, str) or not verifier.strip():
            raise BoundInstanceSemanticsError("INDEPENDENT_VERIFIER_ID_INVALID")
        return {
            "schema": SCHEMA,
            "status": "PASS__BOUND_CAPABILITY_INSTANCE_SEMANTICS_AUTHENTICATED",
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
    prepared: Mapping[str, Any],
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
    matches = []
    for pair in binding_pairs:
        out = authenticate(
            problem, capability, prepared, value_capsule, pair, repo_root=repo_root
        )
        if out.get("pass") is True:
            matches.append(out)
    if len(matches) != 1:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["BOUND_INSTANCE_SEMANTICS_MATCH_COUNT:" + str(len(matches))],
            "terminal_authority": False,
        }
    return matches[0]
