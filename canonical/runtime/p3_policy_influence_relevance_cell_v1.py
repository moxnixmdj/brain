"""P3 policy-influence relevance closure cell v1.

This cell does not infer free-form semantic relevance. It consumes an independently
verified, exact-byte-bound finite policy-world contract for the current P3 input.

For each exact discriminator bucket it requires at least one Brain-owned adequate
policy common to every source-compatible world in that bucket. Residual semantic
variation inside a bucket is therefore policy-noninterfering.

A discriminator is decision-relevant iff deleting it from the partition causes
at least one merged bucket to lose every common adequate policy. Otherwise the
discriminator is redundant/noninterfering over the verified world abstraction.

No source authorization, global policy-adequacy, D_B, U, or terminal authority is
minted by this cell.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import resolve_receipt_bytes
from canonical.runtime.p3_required_claim_grounded_realization_cell_v3 import (
    evaluate as realize,
)

SCHEMA = "PROJECT_BRAIN_P3_POLICY_INFLUENCE_RELEVANCE_CELL_V1"
CONTRACT_SCHEMA = "PROJECT_BRAIN_P3_POLICY_INFLUENCE_CONTRACT_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_P3_POLICY_INFLUENCE_INDEPENDENT_VERIFICATION_V1"

MAX_DISCRIMINATORS = 16
MAX_WORLDS = 4096
MAX_POLICIES = 256

_CONTRACT_FIELDS = {
    "schema", "environment_id", "goal_id", "discriminator_ids",
    "current_discriminator_values", "worlds", "policies", "verification_ref",
}
_WORLD_FIELDS = {"world_id", "discriminator_values", "adequate_policy_ids"}
_POLICY_FIELDS = {"policy_id", "selected_claim_ids"}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "p3_contract_cell_authorized": False,
        "policy_influence_noninterference_verified": False,
        "source_authorization_verified": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _digest(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return "sha256:" + sha256(raw).hexdigest()


def _contract_body(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {k: contract[k] for k in sorted(contract) if k != "verification_ref"}


def _validate_claims(public: Mapping[str, Any]) -> tuple[
    list[str], list[str], list[str], int
]:
    task = public.get("task")
    if not isinstance(task, Mapping):
        raise ValueError("TASK_REQUIRED")
    claims = task.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ValueError("CLAIMS_REQUIRED")
    if "claim_order" in task:
        raise ValueError("CALLER_CLAIM_ORDER_FORBIDDEN")
    ids: list[str] = []
    required: list[str] = []
    optional: list[str] = []
    for row in claims:
        if not isinstance(row, Mapping):
            raise ValueError("CLAIM_ROW_INVALID")
        cid = row.get("claim_id")
        req = row.get("required")
        if not isinstance(cid, str) or not cid or cid in ids:
            raise ValueError("CLAIM_ID_INVALID_OR_DUPLICATE")
        if req not in (True, False):
            raise ValueError("CLAIM_REQUIRED_FLAG_INVALID")
        if "include" in row:
            raise ValueError("CALLER_INCLUDE_FORBIDDEN")
        ids.append(cid)
        (required if req else optional).append(cid)

    profile = task.get("audience_profile")
    constraints = profile.get("constraints") if isinstance(profile, Mapping) else None
    max_items = constraints.get("max_items") if isinstance(constraints, Mapping) else None
    if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
        raise ValueError("MAX_ITEMS_INVALID")
    return ids, required, optional, max_items


def _common_policy(worlds: list[dict[str, Any]]) -> list[str]:
    common = set(worlds[0]["adequate_policy_ids"])
    for world in worlds[1:]:
        common.intersection_update(world["adequate_policy_ids"])
    return sorted(common)


def evaluate(payload: Mapping[str, Any], *, repo_root: str | Path) -> dict[str, Any]:
    try:
        if not isinstance(payload, Mapping):
            return _fail("PAYLOAD_MAPPING_REQUIRED")
        public = payload.get("v3_input")
        contract = payload.get("policy_influence_contract")
        if not isinstance(public, Mapping):
            return _fail("V3_INPUT_REQUIRED")
        if not isinstance(contract, Mapping):
            return _fail("POLICY_INFLUENCE_CONTRACT_REQUIRED")
        if set(contract) != _CONTRACT_FIELDS:
            return _fail(
                "POLICY_INFLUENCE_CONTRACT_FIELDS_INVALID",
                missing=sorted(_CONTRACT_FIELDS - set(contract)),
                extra=sorted(set(contract) - _CONTRACT_FIELDS),
            )
        if contract.get("schema") != CONTRACT_SCHEMA:
            return _fail("POLICY_INFLUENCE_CONTRACT_SCHEMA_INVALID")

        claim_ids, required_ids, optional_ids, max_items = _validate_claims(public)
        claim_set = set(claim_ids)
        required_set = set(required_ids)

        env = contract.get("environment_id")
        goal = contract.get("goal_id")
        if not isinstance(env, str) or not env or not isinstance(goal, str) or not goal:
            return _fail("ENVIRONMENT_OR_GOAL_ID_INVALID")

        discriminator_ids = contract.get("discriminator_ids")
        if (
            not isinstance(discriminator_ids, list)
            or not discriminator_ids
            or len(discriminator_ids) > MAX_DISCRIMINATORS
            or len(set(discriminator_ids)) != len(discriminator_ids)
            or any(not isinstance(x, str) or not x for x in discriminator_ids)
        ):
            return _fail("DISCRIMINATOR_IDS_INVALID")

        current_values = contract.get("current_discriminator_values")
        if not isinstance(current_values, Mapping) or set(current_values) != set(discriminator_ids):
            return _fail("CURRENT_DISCRIMINATOR_VALUES_INVALID")
        if any(not isinstance(current_values[d], str) or not current_values[d] for d in discriminator_ids):
            return _fail("CURRENT_DISCRIMINATOR_VALUE_INVALID")

        raw_policies = contract.get("policies")
        if (
            not isinstance(raw_policies, list)
            or not raw_policies
            or len(raw_policies) > MAX_POLICIES
        ):
            return _fail("POLICIES_INVALID_OR_TOO_MANY")

        policies: dict[str, list[str]] = {}
        for row in raw_policies:
            if not isinstance(row, Mapping) or set(row) != _POLICY_FIELDS:
                return _fail("POLICY_FIELDS_INVALID")
            pid = row.get("policy_id")
            selected = row.get("selected_claim_ids")
            if not isinstance(pid, str) or not pid or pid in policies:
                return _fail("POLICY_ID_INVALID_OR_DUPLICATE")
            if (
                not isinstance(selected, list)
                or not selected
                or len(set(selected)) != len(selected)
                or any(not isinstance(x, str) or x not in claim_set for x in selected)
            ):
                return _fail("POLICY_SELECTED_CLAIMS_INVALID", policy_id=pid)
            selected_set = set(selected)
            if not required_set.issubset(selected_set):
                return _fail("POLICY_OMITS_REQUIRED_CLAIM", policy_id=pid)
            if len(selected) > max_items:
                return _fail(
                    "POLICY_EXCEEDS_ITEM_BUDGET",
                    policy_id=pid,
                    selected_count=len(selected),
                    max_items=max_items,
                )
            expected_order = [cid for cid in claim_ids if cid in selected_set]
            if selected != expected_order:
                return _fail("POLICY_SELECTION_ORDER_MUST_PRESERVE_CLAIM_ORDER", policy_id=pid)
            policies[pid] = list(selected)

        raw_worlds = contract.get("worlds")
        if (
            not isinstance(raw_worlds, list)
            or not raw_worlds
            or len(raw_worlds) > MAX_WORLDS
        ):
            return _fail("WORLDS_INVALID_OR_TOO_MANY")

        worlds: list[dict[str, Any]] = []
        seen_worlds: set[str] = set()
        for row in raw_worlds:
            if not isinstance(row, Mapping) or set(row) != _WORLD_FIELDS:
                return _fail("WORLD_FIELDS_INVALID")
            wid = row.get("world_id")
            values = row.get("discriminator_values")
            adequate = row.get("adequate_policy_ids")
            if not isinstance(wid, str) or not wid or wid in seen_worlds:
                return _fail("WORLD_ID_INVALID_OR_DUPLICATE")
            if not isinstance(values, Mapping) or set(values) != set(discriminator_ids):
                return _fail("WORLD_DISCRIMINATOR_VALUES_INVALID", world_id=wid)
            if any(not isinstance(values[d], str) or not values[d] for d in discriminator_ids):
                return _fail("WORLD_DISCRIMINATOR_VALUE_INVALID", world_id=wid)
            if (
                not isinstance(adequate, list)
                or not adequate
                or len(set(adequate)) != len(adequate)
                or any(not isinstance(pid, str) or pid not in policies for pid in adequate)
            ):
                return _fail("WORLD_ADEQUATE_POLICIES_INVALID", world_id=wid)
            seen_worlds.add(wid)
            worlds.append({
                "world_id": wid,
                "discriminator_values": {d: values[d] for d in discriminator_ids},
                "adequate_policy_ids": sorted(adequate),
            })

        ref = contract.get("verification_ref")
        if not isinstance(ref, Mapping):
            return _fail("POLICY_INFLUENCE_VERIFICATION_REF_REQUIRED")
        path = ref.get("path")
        if not isinstance(path, str) or not path.startswith("canonical/verification/"):
            return _fail("POLICY_INFLUENCE_VERIFICATION_MUST_BE_CANONICAL")
        bound = resolve_receipt_bytes(ref, repo_root=Path(repo_root))
        receipt = bound["document"]
        if receipt.get("schema") != RECEIPT_SCHEMA:
            return _fail("POLICY_INFLUENCE_VERIFICATION_SCHEMA_INVALID")
        for field in (
            "independent_verified",
            "exact_byte_bound",
            "source_compatible_world_overapproximation_sound",
            "world_universe_complete_for_declared_scope",
            "policy_adequacy_authenticated",
            "discriminator_semantics_authenticated",
            "current_discriminator_values_authenticated",
            "selection_policy_bindings_authenticated",
        ):
            if receipt.get(field) is not True:
                return _fail("POLICY_INFLUENCE_VERIFICATION_PREMISE_UNPROVED:" + field)
        if receipt.get("conclusion") != "success":
            return _fail("POLICY_INFLUENCE_VERIFICATION_NOT_SUCCESS")
        if receipt.get("environment_id") != env or receipt.get("goal_id") != goal:
            return _fail("POLICY_INFLUENCE_VERIFICATION_SCOPE_MISMATCH")
        if receipt.get("contract_body_sha256") != _digest(_contract_body(contract)):
            return _fail("POLICY_INFLUENCE_CONTRACT_DIGEST_MISMATCH")
        if receipt.get("v3_input_sha256") != _digest(public):
            return _fail("POLICY_INFLUENCE_V3_INPUT_DIGEST_MISMATCH")

        buckets: dict[tuple[str, ...], list[dict[str, Any]]] = {}
        for world in worlds:
            key = tuple(world["discriminator_values"][d] for d in discriminator_ids)
            buckets.setdefault(key, []).append(world)

        bucket_common: dict[tuple[str, ...], list[str]] = {}
        for key, members in buckets.items():
            common = _common_policy(members)
            if not common:
                return _fail(
                    "DISCRIMINATOR_BUCKET_HAS_NO_COMMON_POLICY",
                    discriminator_values=dict(zip(discriminator_ids, key)),
                    world_ids=[w["world_id"] for w in members],
                    adequate_policy_ids={
                        w["world_id"]: w["adequate_policy_ids"] for w in members
                    },
                )
            bucket_common[key] = common

        current_key = tuple(current_values[d] for d in discriminator_ids)
        if current_key not in bucket_common:
            return _fail("CURRENT_DISCRIMINATOR_BUCKET_NOT_IN_VERIFIED_WORLD_UNIVERSE")
        selected_policy_id = bucket_common[current_key][0]
        selected_claim_ids = policies[selected_policy_id]

        relevance_bits: dict[str, str] = {}
        ablation_witnesses: dict[str, Any] = {}
        for drop_index, discriminator in enumerate(discriminator_ids):
            merged: dict[tuple[str, ...], list[dict[str, Any]]] = {}
            for world in worlds:
                full = tuple(world["discriminator_values"][d] for d in discriminator_ids)
                reduced = full[:drop_index] + full[drop_index + 1:]
                merged.setdefault(reduced, []).append(world)
            witness = None
            for reduced_key, members in merged.items():
                if not _common_policy(members):
                    witness = {
                        "remaining_discriminator_values": {
                            d: value
                            for d, value in zip(
                                discriminator_ids[:drop_index] + discriminator_ids[drop_index + 1:],
                                reduced_key,
                            )
                        },
                        "world_ids": [w["world_id"] for w in members],
                    }
                    break
            relevance_bits[discriminator] = "RELEVANT" if witness else "IRRELEVANT"
            if witness:
                ablation_witnesses[discriminator] = witness

        compiled = deepcopy(dict(public))
        ctask = compiled["task"]
        selected_set = set(selected_claim_ids)
        rows = []
        for row in ctask["claims"]:
            if row["claim_id"] not in selected_set:
                continue
            nr = dict(row)
            nr["required"] = True
            nr.pop("include", None)
            rows.append(nr)
        ctask["claims"] = rows
        ctask.pop("claim_order", None)
        realized = realize({"v3_input": compiled})
        if realized.get("pass") is not True:
            return _fail("SELECTED_POLICY_GROUNDED_REALIZATION_FAILED", realization=realized)
        if any(
            realized.get(field) is not False
            for field in (
                "source_authorization_verified",
                "policy_adequacy_authority",
                "db_admission_authority",
                "u_subtraction_authority",
                "terminal_authority",
            )
        ) or realized.get("terminal_credit_delta") != 0:
            return _fail("DOWNSTREAM_AUTHORITY_BOUNDARY_INVALID")

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__P3_POLICY_INFLUENCE_NONINTERFERENCE_RELEVANCE_CELL",
            "environment_id": env,
            "goal_id": goal,
            "verification_path": bound["path"],
            "verification_git_blob_sha": bound["git_blob_sha"],
            "source_compatible_world_overapproximation_sound": True,
            "world_universe_complete_for_declared_scope": True,
            "policy_influence_noninterference_verified": True,
            "discriminator_ids": list(discriminator_ids),
            "current_discriminator_values": dict(current_values),
            "relevance_bits": relevance_bits,
            "relevance_ablation_witnesses": ablation_witnesses,
            "common_policy_by_bucket": [
                {
                    "discriminator_values": dict(zip(discriminator_ids, key)),
                    "common_policy_ids": common,
                    "selected_policy_id": common[0],
                }
                for key, common in sorted(bucket_common.items())
            ],
            "selected_policy_id": selected_policy_id,
            "selected_claim_ids": list(selected_claim_ids),
            "required_claim_ids": required_ids,
            "optional_claim_ids": optional_ids,
            "rendered_text": realized.get("rendered_text"),
            "render_trace": realized.get("render_trace"),
            "realization_receipt": realized,
            "p3_contract_cell_authorized": True,
            "source_authorization_verified": False,
            "policy_adequacy_authority": False,
            "db_admission_authority": False,
            "u_subtraction_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "INDEPENDENT_EXACT_BYTE_BOUND_SOUND_SOURCE_COMPATIBLE_FINITE_WORLD_OVERAPPROXIMATION;"
                "AUTHENTICATED_POLICY_ADEQUACY_AND_DISCRIMINATOR_SEMANTICS;"
                "NO_GENERAL_FREE_FORM_SEMANTIC_RELEVANCE_OR_GLOBAL_P3_CLOSURE"
            ),
        }
    except Exception as exc:
        return _fail(
            "INVALID_INPUT",
            exception_type=type(exc).__name__,
            detail_text=str(exc)[:240],
        )


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(
        args or {},
        repo_root=root or Path(__file__).resolve().parents[2],
    )
