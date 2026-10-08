"""Abstract policy-cover -> concrete-scope totality lift v1.

This module proves one generic implication only:

  sound over-approximation of the concrete target scope
  + positive finite abstract policy-cover totality
  + sound concrete lifts for every used policy and discriminator
  => concrete-scope adaptive policy totality.

It does NOT prove the supplied receipts, U-empty, DB admission, acceptance,
ownership finality, or terminal success. Unknown/missing bindings fail closed.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ABSTRACT_POLICY_COVER_CONCRETE_LIFT_V1"


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "concrete_scope_adaptive_policy_totality_proved": False,
        "selected_cover_complete_authorized": False,
        "u_empty_authorized": False,
        "db_admission_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _receipt_ok(value: Any, required: Mapping[str, Any]) -> tuple[bool, str | None]:
    if not isinstance(value, Mapping):
        return False, "RECEIPT_REQUIRED"
    common = {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
    }
    for key, expected in {**common, **dict(required)}.items():
        if value.get(key) != expected:
            return False, "RECEIPT_BINDING_MISMATCH:" + key
    return True, None


def _walk_tree(node: Any, *, policies: set[str], discriminators: set[str], depth: int = 0) -> str | None:
    if depth > 256:
        return "DECISION_TREE_DEPTH_BOUND_EXCEEDED"
    if not isinstance(node, Mapping):
        return "DECISION_TREE_NODE_MAPPING_REQUIRED"
    terminal = node.get("terminal_policy_id")
    discriminator = node.get("discriminator_id")

    if isinstance(terminal, str) and terminal:
        if discriminator is not None or "outcome_partitions" in node:
            return "TERMINAL_NODE_HAS_DISCRIMINATOR_FIELDS"
        policies.add(terminal)
        return None

    if not isinstance(discriminator, str) or not discriminator:
        return "NONTERMINAL_DISCRIMINATOR_REQUIRED"
    parts = node.get("outcome_partitions")
    if not isinstance(parts, Sequence) or isinstance(parts, (str, bytes)) or not parts:
        return "NONTERMINAL_PARTITIONS_REQUIRED"
    discriminators.add(discriminator)

    seen_parts: set[str] = set()
    for i, row in enumerate(parts):
        if not isinstance(row, Mapping):
            return f"PARTITION_MAPPING_REQUIRED:{i}"
        world_ids = row.get("world_ids")
        if (
            not isinstance(world_ids, Sequence)
            or isinstance(world_ids, (str, bytes))
            or not world_ids
            or any(not isinstance(x, str) or not x for x in world_ids)
        ):
            return f"PARTITION_WORLD_IDS_INVALID:{i}"
        key = _canon(sorted(set(world_ids)))
        if key in seen_parts:
            return f"DUPLICATE_PARTITION:{i}"
        seen_parts.add(key)
        err = _walk_tree(row.get("next"), policies=policies, discriminators=discriminators, depth=depth + 1)
        if err:
            return err
    return None


def _normalize_receipts(
    rows: Any,
    *,
    id_field: str,
    expected_ids: set[str],
    common_required: Mapping[str, Any],
    kind_required: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]] | None, str | None]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return None, "RECEIPT_SEQUENCE_REQUIRED"
    out: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return None, f"RECEIPT_ROW_INVALID:{i}"
        rid = row.get(id_field)
        if not isinstance(rid, str) or not rid or rid in out:
            return None, f"RECEIPT_ID_INVALID_OR_DUPLICATE:{i}"
        out[rid] = row
    if set(out) != expected_ids:
        return None, "RECEIPT_ID_SET_MISMATCH"
    for rid, row in out.items():
        ok, reason = _receipt_ok(row, {**dict(common_required), id_field: rid, **dict(kind_required)})
        if not ok:
            return None, f"{rid}:{reason}"
    return out, None


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    scope_id = payload.get("scope_id")
    state_id = payload.get("state_id")
    if not isinstance(scope_id, str) or not scope_id:
        return _fail("SCOPE_ID_REQUIRED")
    if not isinstance(state_id, str) or not state_id:
        return _fail("STATE_ID_REQUIRED")

    totality = payload.get("abstract_totality_result")
    if not isinstance(totality, Mapping):
        return _fail("ABSTRACT_TOTALITY_RESULT_REQUIRED")
    if (
        totality.get("pass") is not True
        or totality.get("bound_state_totality_proved") is not True
        or totality.get("state_id") != state_id
        or totality.get("unresolved_observational_classes") not in ([], ())
    ):
        return _fail("ABSTRACT_TOTALITY_NOT_POSITIVELY_PROVED")

    tree = totality.get("decision_tree")
    policies: set[str] = set()
    discriminators: set[str] = set()
    err = _walk_tree(tree, policies=policies, discriminators=discriminators)
    if err:
        return _fail("ABSTRACT_DECISION_TREE_INVALID", tree_error=err)
    if not policies:
        return _fail("ABSTRACT_DECISION_TREE_HAS_NO_TERMINAL_POLICY")

    totality_sha = _digest(totality)
    tree_sha = _digest(tree)

    abstraction_required = {
        "scope_id": scope_id,
        "state_id": state_id,
        "abstract_totality_result_sha256": totality_sha,
        "decision_tree_sha256": tree_sha,
        "concrete_scope_frozen": True,
        "every_concrete_context_represented": True,
        "abstraction_is_sound_overapproximation": True,
        "uncertainty_only_widens_abstract_state": True,
        "unproved_refinement_can_never_remove_concrete_possibilities": True,
    }
    ok, reason = _receipt_ok(payload.get("abstraction_soundness_receipt"), abstraction_required)
    if not ok:
        return _fail("ABSTRACTION_SOUNDNESS_RECEIPT_INVALID", receipt_error=reason)

    common_required = {
        "scope_id": scope_id,
        "state_id": state_id,
        "abstract_totality_result_sha256": totality_sha,
        "decision_tree_sha256": tree_sha,
    }

    _, reason = _normalize_receipts(
        payload.get("policy_lift_receipts"),
        id_field="policy_id",
        expected_ids=policies,
        common_required=common_required,
        kind_required={
            "abstract_policy_region_implies_concrete_adequacy": True,
            "brain_owned": True,
            "deployed_exact": True,
            "resource_bound_proved": True,
        },
    )
    if reason:
        return _fail("POLICY_LIFT_RECEIPTS_INVALID", receipt_error=reason)

    _, reason = _normalize_receipts(
        payload.get("discriminator_lift_receipts", []),
        id_field="discriminator_id",
        expected_ids=discriminators,
        common_required=common_required,
        kind_required={
            "concrete_observation_refines_to_declared_abstract_outcome": True,
            "truth_preserving_on_scope": True,
            "safe_on_scope": True,
            "resource_bound_proved": True,
        },
    )
    if reason:
        return _fail("DISCRIMINATOR_LIFT_RECEIPTS_INVALID", receipt_error=reason)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__ABSTRACT_TOTALITY_SOUNDLY_LIFTS_TO_CONCRETE_SCOPE_POLICY_TOTALITY",
        "scope_id": scope_id,
        "state_id": state_id,
        "abstract_totality_result_sha256": totality_sha,
        "decision_tree_sha256": tree_sha,
        "used_policy_ids": sorted(policies),
        "used_discriminator_ids": sorted(discriminators),
        "concrete_scope_adaptive_policy_totality_proved": True,
        "proof_rule": (
            "EVERY_CONCRETE_CONTEXT_IS_REPRESENTED_BY_THE_SOUND_OVERAPPROXIMATION__"
            "EVERY_USED_DISCRIMINATOR_PRESERVES_THE_CONCRETE_TO_ABSTRACT_BRANCH_RELATION__"
            "ABSTRACT_TOTALITY_REACHES_A_TERMINAL_POLICY_ON_EVERY_ABSTRACT_PATH__"
            "EVERY_USED_ABSTRACT_POLICY_REGION_SOUNDLY_IMPLIES_CONCRETE_POLICY_ADEQUACY__"
            "THEREFORE_EVERY_CONCRETE_CONTEXT_REACHES_AN_ADEQUATE_BRAIN_OWNED_POLICY"
        ),
        "basis_completeness_required_for_positive_proof": False,
        "complete_raw_semantic_world_model_required": False,
        "selected_cover_complete_authorized": False,
        "u_empty_authorized": False,
        "db_admission_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "GENERIC_SOUNDNESS_LIFT_ONLY__THIS_RUNTIME_AUTHENTICATES_DECLARED_RECEIPTS_BUT_DOES_NOT_PROVE_"
            "THEIR_EXTERNAL_TRUTH__NO_U_EMPTY_DB_ADMISSION_ACCEPTANCE_OR_TERMINAL_AUTHORITY"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {})
